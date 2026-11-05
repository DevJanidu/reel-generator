"""Fixed structured-output provider process. Must be launched through verified MXC."""
import asyncio,json,os,subprocess,sys
from pathlib import Path

root=Path(os.environ['EPISODE_WRITE_ROOT']).absolute()
temporary=root/'.production/temp'/os.environ['ODD_JOB_ID'];temporary.mkdir(parents=True,exist_ok=True)
for name in ('TMP','TEMP','TMPDIR'):os.environ[name]=str(temporary)
sys.path.insert(0,os.environ['ODD_APP_ROOT'])
from services.api.file_writer import EpisodeWriter
writer=EpisodeWriter(root)
request_path=writer.path(sys.argv[1]);spec=json.loads(request_path.read_text(encoding='utf-8'))
job=spec['job_id'];folder=f'.production/runs/{job}'
schema=writer.json(folder+'/schema.json',spec['schema'])
response=writer.path(folder+'/response.json')
provider=spec['provider'];env=os.environ.copy()
prompt='\n\n'.join('=== '+m['role'].upper()+' ===\n'+m['content'] for m in spec['messages'])
prompt+='\n\nReturn ONLY the complete JSON object matching the supplied output schema. All mandatory reference text above was supplied in full. Do not use tools, edit files or execute commands.'
if provider=='codex_cli':
    # Auth stays in the installed CLI's own store, which the outer OS boundary makes read-only.
    env['CODEX_HOME']=spec['auth_home']
    args=[spec['command'],'--no-daemon','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check',
          '--sandbox','read-only','--output-schema',str(schema),'--output-last-message',str(response),'--json','--color','never',
          '-c','approval_policy="never"','-c','web_search="disabled"',
          '-c','log_dir='+json.dumps(str(root/'.production/logs'/job)),
          '-c','sqlite_home='+json.dumps(str(root/'.production/runtime/codex-state'/job)),
          '-c','project_doc_max_bytes=0','-c','skills.bundled.enabled=false']
    for feature in ['shell_tool','unified_exec','multi_agent','apps','plugins','hooks','shell_snapshot','in_app_browser']:
        args+=['--disable',feature]
    if spec.get('model'):args+=['--model',spec['model']]
    args+=['-']
elif provider=='claude_cli':
    mode=spec.get('claude_auth')
    if mode=='api_key' and env.get('ANTHROPIC_API_KEY'):
        isolation_args=['--bare']
    elif mode=='subscription_token' and env.get('CLAUDE_CODE_OAUTH_TOKEN'):
        # Bare mode ignores this token. Without it, keep the host's settings, hooks, plugins and memory out
        # using an empty private config directory; no login files are read or copied.
        isolation_args=['--setting-sources','']
        env['CLAUDE_CONFIG_DIR']=str(root/'.production/runtime/claude-config'/job)
        env['CLAUDE_CODE_DISABLE_CLAUDE_MDS']='1';env['CLAUDE_CODE_DISABLE_AUTO_MEMORY']='1'
        env.pop('ANTHROPIC_AUTH_TOKEN',None)
    else:
        raise SystemExit('CLAUDE_AUTH_UNSUPPORTED: Run claude setup-token and set CLAUDE_CODE_OAUTH_TOKEN, or set ANTHROPIC_API_KEY, then restart the station.')
    args=[spec['command'],*isolation_args,'-p','--tools','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
          '--no-session-persistence','--output-format','stream-json','--verbose','--json-schema',json.dumps(spec['schema'],separators=(',',':')),
          '--permission-mode','dontAsk','--permission-prompts','none','--disable-slash-commands']
    if spec.get('model'):args+=['--model',spec['model']]
else:raise SystemExit('Unsupported CLI provider')
writer.json(folder+'/invocation.json',dict(provider=provider,argv=args,tools='disabled; Codex model commands also read-only',auth=spec.get('claude_auth') or 'Installed CLI authentication'))
from services.api.activity import emit,provider_activity
meta=spec.get('activity',dict(episode_id=None,stage='generation'))
def activity(kind,message):
    emit(root,job,meta['episode_id'],provider,meta['stage'],kind,message)

async def execute():
    # Drain stdout asynchronously; stderr goes directly to an episode-private file.
    # Bound each machine event and total captured bytes; never accumulate a transcript in RAM.
    with writer.path(folder+'/provider.stderr.log').open('wb') as err, writer.path(folder+'/events.jsonl').open('wb') as log:
        proc=await asyncio.create_subprocess_exec(*args,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,
                    stderr=err,env=env,cwd=root,limit=4*1024*1024,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        activity('ai.started','Provider process started; waiting for structured activity')
        async def feed():
            try:
                proc.stdin.write(prompt.encode('utf-8'));await proc.stdin.drain();proc.stdin.close()
            except (BrokenPipeError,ConnectionResetError):pass
        feeder=asyncio.create_task(feed())
        size=0;envelope=None
        try:
            while line:=await proc.stdout.readline():
                size+=len(line)
                if size>64*1024*1024:raise ValueError('Provider event output exceeded the safety limit')
                log.write(line);log.flush()
                try:event=json.loads(line)
                except ValueError:continue
                if not isinstance(event,dict):continue
                item=event.get('item') or {}
                if item.get('type') in ('command_execution','file_change','mcp_tool_call','web_search'):
                    raise ValueError('Unexpected tool use during structured generation; response rejected')
                if event.get('type') in ('error','turn.failed'):
                    raise ValueError('Provider reported a generation failure; retry after checking provider status')
                message=provider_activity(provider,event)
                if message:activity('ai.activity',message)
                if provider=='claude_cli':
                    blocks=(event.get('message') or {}).get('content') or []
                    if any(x.get('type')=='tool_use' and x.get('name')!='StructuredOutput' for x in blocks if isinstance(x,dict)):
                        raise ValueError('Unexpected Claude tool use; response rejected')
                    if event.get('type')=='result':envelope=event
            await feeder
            code=await proc.wait()
            if code:raise ValueError('Provider process exited unsuccessfully; check authentication and usage limits')
            if provider=='claude_cli':
                if not envelope or envelope.get('is_error'):raise ValueError('Claude generation did not complete successfully')
                data=envelope.get('structured_output')
                if not isinstance(data,dict):raise ValueError('Claude did not return structured_output')
                writer.json(folder+'/response.json',data)
            activity('ai.completed','Provider exited successfully; schema and coverage validation are still required')
        finally:
            if proc.returncode is None:proc.kill();await proc.wait()
            if not feeder.done():feeder.cancel()
asyncio.run(execute())
if not response.exists():raise SystemExit('Provider returned no final structured response')
data=json.loads(response.read_text(encoding='utf-8'))
if not isinstance(data,dict):raise SystemExit('Structured response must be an object')
print(json.dumps(dict(status='GENERATED',provider=provider,response=str(response.relative_to(root)))))
