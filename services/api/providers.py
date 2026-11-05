"""Four explicit providers. Never switch billing/authentication/provider on failure."""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from pathlib import Path
import httpx
from .core import ROOT,STORE,settings,now
from .file_writer import EpisodeWriter
from . import isolation

PROVIDERS=('codex_cli','claude_cli','manual','openai-compatible')

class ProviderError(ValueError):
    def __init__(self,message,code='PROVIDER_FAILED'):
        self.code=code
        super().__init__(message)

def classify(message):
    lowered=message.lower()
    if any(x in lowered for x in ['usage limit','rate limit','quota','insufficient_quota','429','credit balance','out of credits']):return 'USAGE_LIMIT'
    if any(x in lowered for x in ['unauthorized','authentication','not logged in','401','invalid api key','login required','credentials','claude_auth_unsupported']):return 'AUTHENTICATION'
    if 'timeout' in lowered or 'timed out' in lowered:return 'TIMEOUT'
    if 'cancel' in lowered:return 'CANCELLED'
    if any(x in lowered for x in ['sandbox','isolation','mxc']):return 'ISOLATION_UNAVAILABLE'
    if any(x in lowered for x in ['schema','structured','json']):return 'INVALID_OUTPUT'
    return 'PROVIDER_FAILED'

def redact(message):
    message=re.sub(r'(?:sk-[A-Za-z0-9_-]+|Bearer\s+\S+)','[redacted]',message)
    for name in ('ODD_AI_API_KEY','ANTHROPIC_API_KEY','CLAUDE_CODE_OAUTH_TOKEN'):
        if os.getenv(name):message=message.replace(os.environ[name],'[redacted]')
    message=re.sub(r'[A-Za-z]:[^\r\n\"<>]*[\\/]\.production[\\/]runtime[^\r\n\"<>]*','[private job runtime]',message)
    return message[-3500:]

def claude_auth_mode():
    """Credentials the owner explicitly configured; the CLI's documented precedence puts the API key first."""
    if os.getenv('ANTHROPIC_API_KEY'):return 'api_key'
    if os.getenv('CLAUDE_CODE_OAUTH_TOKEN'):return 'subscription_token'
    return None

def cli_info(provider):
    envname='ODD_CODEX_COMMAND' if provider=='codex_cli' else 'ODD_CLAUDE_COMMAND'
    configured=os.getenv(envname,'codex' if provider=='codex_cli' else 'claude')
    path=shutil.which(configured)
    if not path:return dict(installed=False,provider=provider,eligible=False,error='Command not found: '+configured)
    if Path(path).suffix.lower()!='.exe':return dict(installed=False,provider=provider,eligible=False,error='A native .exe is required; shell wrappers are not executed')
    try:
        version=subprocess.run([path,'--version'],capture_output=True,text=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        text=version.stdout.strip()
        if version.returncode or not ('codex-cli' in text if provider=='codex_cli' else 'Claude Code' in text):raise ValueError('Unexpected command version signature')
        args=[path,'login','status'] if provider=='codex_cli' else [path,'auth','status']
        auth=subprocess.run(args,capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if provider=='codex_cli':
            authenticated=auth.returncode==0 and 'logged in' in (auth.stdout+auth.stderr).lower()
            method=('ChatGPT login (installed Codex CLI)' if 'chatgpt' in (auth.stdout+auth.stderr).lower() else 'Existing API-key login (installed Codex CLI)') if authenticated else 'Not authenticated'
            eligible=authenticated
            reason='' if eligible else 'Run codex login in your own terminal'
        else:
            payload=json.loads(auth.stdout) if auth.returncode==0 else {}
            authenticated=bool(payload.get('loggedIn'))
            mode=claude_auth_mode()
            method={'api_key':'ANTHROPIC_API_KEY (billed to the key owner)','subscription_token':'Your Claude subscription (claude setup-token)'}.get(mode,payload.get('authMethod','unknown'))
            eligible=bool(mode)
            reason='' if eligible else 'Dashboard automation needs its own credential. Run claude setup-token in your terminal, add CLAUDE_CODE_OAUTH_TOKEN=<token> to .env and restart the station. ANTHROPIC_API_KEY also works and is billed separately.'
        return dict(provider=provider,installed=True,command=path,version=text,authenticated=authenticated,
                    auth_method=method,eligible=eligible,eligibility_message=reason,live_generation_tested=False)
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        return dict(provider=provider,installed=True,command=path,eligible=False,error=redact(str(exc)))

def inventory():
    return [cli_info('codex_cli'),cli_info('claude_cli'),
            dict(provider='manual',installed=True,eligible=True,auth_method='External user workflow',live_generation_tested=False),
            dict(provider='openai-compatible',installed=True,eligible=bool(os.getenv('ODD_AI_API_KEY')),auth_method='Environment API key',live_generation_tested=False)]

def cleanup_private_job_homes(root):
    """Controller startup recovery after its Job Object has terminated orphaned children."""
    from .file_writer import no_links
    parent=Path(root)/'.production/runtime/codex-auth'
    if not parent.exists():return
    no_links(parent)
    for candidate in parent.iterdir():
        if candidate.is_dir():
            no_links(candidate)
            if not candidate.resolve().is_relative_to(Path(root).resolve()):raise ValueError('Private job home escapes its assigned episode')
            shutil.rmtree(candidate)

def strict_schema(schema):
    """Codex structured outputs require every object property in required, with no extras."""
    schema=json.loads(json.dumps(schema))
    def walk(node):
        if isinstance(node,dict):
            node.pop('default',None)
            if node.get('type')=='object':node['required']=list(node.get('properties',{}));node['additionalProperties']=False
            for value in list(node.values()):walk(value)
        elif isinstance(node,list):
            for item in node:walk(item)
    walk(schema)
    return schema

def generate(config,messages,schema,root,runid,cancel=None):
    provider=config['provider'];writer=EpisodeWriter(root)
    if provider=='manual':raise ProviderError('Manual mode requires explicit import','MANUAL_REQUIRED')
    if provider=='openai-compatible':
        if not config['model'] or not os.getenv('ODD_AI_API_KEY'):raise ProviderError('AI provider not configured: model and ODD_AI_API_KEY are required, or choose Codex CLI/manual','AUTHENTICATION')
        try:
            with httpx.Client(timeout=config.get('timeout_seconds',300)) as client:
                response=client.post(config['base_url'].rstrip('/')+'/chat/completions',json=dict(model=config['model'],messages=messages,max_tokens=config['output_tokens'],response_format={'type':'json_object'}),headers={'Authorization':'Bearer '+os.environ['ODD_AI_API_KEY']})
                response.raise_for_status();completion=response.json()['choices'][0]
                if completion.get('finish_reason') not in (None,'stop'):raise ProviderError('Model response incomplete: '+str(completion.get('finish_reason')),'INVALID_OUTPUT')
                data=json.loads(completion['message']['content'])
            writer.json(f'.production/runs/{runid}/response.json',data)
            return data
        except Exception as exc:
            if isinstance(exc,ProviderError):raise
            raise ProviderError(redact(str(exc)),classify(str(exc))) from exc
    info=cli_info(provider)
    if not info.get('installed'):raise ProviderError(info.get('error','CLI missing'),'NOT_INSTALLED')
    if not info.get('eligible'):raise ProviderError(info.get('eligibility_message') or info.get('error','Provider authentication unavailable'),'AUTHENTICATION')
    try:isolation.require_verified(Path(root))
    except (OSError,ValueError) as exc:raise ProviderError(str(exc),'ISOLATION_UNAVAILABLE') from exc
    auth_home=None
    if provider=='codex_cli':
        # Official documented cache provisioning for a private job CODEX_HOME. Do not parse,
        # translate or log credentials; do not use this mechanism for Claude subscription OAuth.
        original_home=Path(os.getenv('CODEX_HOME',str(Path.home()/'.codex')))
        source=original_home/'auth.json'
        if not source.is_file():raise ProviderError('Codex uses an OS credential store unavailable to this private job home. Sign in with codex login using a private supported file-cache home; no authentication bypass will be attempted.','AUTHENTICATION')
        auth_home=Path(root)/'.production/runtime/codex-auth'/runid
        auth_home.mkdir(parents=True,exist_ok=False)
        # Keep the short-lived cache private to the signed-in Windows owner; no credential
        # contents are inspected. MXC separately enforces read-only access for the worker.
        import csv,io
        identity=subprocess.run(['whoami.exe','/user','/fo','csv','/nh'],capture_output=True,text=True,check=True)
        sid=next(csv.reader(io.StringIO(identity.stdout)))[1]
        acl=subprocess.run(['icacls.exe',str(auth_home),'/inheritance:r','/grant:r','*'+sid+':(OI)(CI)F'],capture_output=True,text=True)
        if acl.returncode:raise ProviderError('Could not secure the private Codex authentication cache','AUTHENTICATION')
        writer.bytes(str((auth_home/'auth.json').relative_to(root)).replace('\\','/'),source.read_bytes(),replace=False)
    spec=dict(provider=provider,command=info['command'],model=config.get('model',''),messages=messages,
              schema=strict_schema(schema),job_id=runid,auth_home=str(auth_home) if auth_home else None,
              claude_auth=claude_auth_mode() if provider=='claude_cli' else None)
    from .core import db
    with db() as c: activity_run=c.execute('SELECT episode_id,task FROM runs WHERE id=?',(runid,)).fetchone()
    spec['activity']=dict(episode_id=activity_run['episode_id'] if activity_run else None,stage=activity_run['task'] if activity_run else 'connection test')
    relative=f'.production/runs/{runid}/cli_request.json'
    writer.json(relative,spec)
    # Only this provider's job receives the owner-supplied token; it is never written to the request.
    extra_env={'CLAUDE_CODE_OAUTH_TOKEN':os.environ['CLAUDE_CODE_OAUTH_TOKEN']} if spec['claude_auth']=='subscription_token' else None
    try:
        result=isolation.launch(Path(root),[sys.executable,'-B',str(ROOT/'scripts/cli_worker.py'),relative],runid,
                                network=True,timeout=config.get('timeout_seconds',300),cancel=cancel,extra_env=extra_env)
        if result['returncode']:
            provider_log=writer.path(f'.production/runs/{runid}/provider.stderr.log')
            detail=result['stderr']+'\n'+result['stdout']
            if provider_log.exists():detail+='\n'+provider_log.read_text(encoding='utf-8')[-1500:]
            raise ProviderError(redact(detail) or 'CLI exited without a valid response',classify(detail))
        return json.loads(writer.path(f'.production/runs/{runid}/response.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        if isinstance(exc,ProviderError):raise
        raise ProviderError(redact(str(exc)),classify(str(exc))) from exc
    finally:
        if auth_home:
            # Only runtime files created in this exact job home; never copy a refreshed cache back
            # into the user's global auth store or retain credentials as episode deliverables.
            from .file_writer import no_links
            no_links(auth_home)
            shutil.rmtree(auth_home)

def test_connection(provider):
    from .skills import model_request
    from .snapshots import bootstrap,source_root
    config={**settings(),'provider':provider}
    runid='connection-'+uuid.uuid4().hex
    directory=STORE/'episodes'/'_provider_tests'/runid
    directory.mkdir(parents=True,exist_ok=False);bootstrap(directory)
    schema=dict(type='object',properties={'ok':{'type':'boolean'},'nonce':{'type':'string'},'message':{'type':'string'}},required=['ok','nonce','message'],additionalProperties=False)
    nonce=uuid.uuid4().hex
    messages,evidence=model_request('01_IDEA_GENERATION.md',dict(task='CONNECTION_TEST: do not generate story ideas. Return only the short object below; this is a diagnostic, not an episode.',required_response={'ok':True,'nonce':nonce,'message':'ODD FRAME connection ready'},output_json_schema=schema),config,root=source_root(directory))
    writer=EpisodeWriter(directory);writer.json('.production/connection_request.json',dict(messages=messages,provenance=evidence))
    if provider=='manual':return dict(provider=provider,success=True,live_generation_tested=False,code='MANUAL_READY',message='Full validated request export/import is available; manual mode does not call a model',workspace=str(directory))
    from .core import db
    from .creative import run_event
    with db() as c:
        c.execute('INSERT INTO runs(id,episode_id,task,status,request,provenance,created,workspace,stage,progress,provider) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (runid,None,'connection_test','RUNNING',json.dumps(dict(messages=messages)),json.dumps(evidence),now(),str(directory),'Testing provider connection',0,provider))
    run_event(runid,'skills.validated','All four complete pinned skills and master prompt validated')
    run_event(runid,'job.started','Starting a real short structured provider diagnostic')
    try:
        data=generate(config,messages,schema,directory,runid)
        if data!={'ok':True,'nonce':nonce,'message':'ODD FRAME connection ready'}:raise ProviderError('Connection response did not match the exact diagnostic contract','INVALID_OUTPUT')
        report=dict(provider=provider,success=True,live_generation_tested=True,code='CONNECTED',message='Real short structured generation passed with all four full skills and master prompt',workspace=str(directory),isolation=isolation.status(directory),at=now())
    except ProviderError as exc:
        report=dict(provider=provider,success=False,live_generation_tested=False,code=exc.code,message=str(exc),workspace=str(directory),at=now())
    with db() as c:c.execute('UPDATE runs SET status=?,error=?,stage=? WHERE id=?',('SUCCEEDED' if report['success'] else 'FAILED',None if report['success'] else report['code'],'Connection verified' if report['success'] else 'Connection unavailable',runid))
    run_event(runid,'job.completed' if report['success'] else 'ai.failed','Real provider diagnostic passed' if report['success'] else 'Provider diagnostic unavailable: '+report['code'],status='SUCCEEDED' if report['success'] else 'FAILED')
    writer.json('.production/connection_result.json',report)
    return report
