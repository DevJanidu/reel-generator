"""Trusted controller for native Windows MXC episode process boundaries.

No elevation, fallback sandbox or permission bypass. A failed probe disables execution.
The controller owns SQLite; the child receives only episode-local request files.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_verified: dict[str,dict] = {}
_guard = threading.Lock()
_running: dict[str,subprocess.Popen] = {}

class IsolationError(ValueError):
    pass

def codex_command():
    configured=os.getenv('ODD_CODEX_COMMAND','codex')
    path=shutil.which(configured)
    if not path or Path(path).suffix.lower()!='.exe':
        raise IsolationError('Native codex.exe is required for the verified Windows MXC boundary')
    return str(Path(path).resolve())

def environment(root:Path, job_id:str, extra_env=None):
    temp=root/'.production/temp'/job_id
    temp.mkdir(parents=True,exist_ok=True)
    # Do not inherit agent IPC/approval authority or provider credentials not needed by this worker.
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(('CODEX_','CLAUDE_CODE_','ODD_EPISODE_','ODD_CONTROLLER_'))}
    env.update(EPISODE_WRITE_ROOT=str(root),ODD_EPISODE_WORKER='1',ODD_JOB_ID=job_id,
               ODD_EXECUTION_MODE='episode',
               ODD_APP_ROOT=str(ROOT),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',
               TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp),
               XDG_CACHE_HOME=str(temp/'cache'),npm_config_cache=str(temp/'npm'),
               CODEX_HOME=str(root/'.production/runtime/sandbox-host'/job_id))
    Path(env['CODEX_HOME']).mkdir(parents=True,exist_ok=True)
    if extra_env:env.update(extra_env)
    return env

def sandbox_argv(root:Path, argv:list[str], *, network=False):
    root=root.absolute()
    # Exact paths only, no global temp write grants. Narrow readonly entries override episode write.
    entries={':root':'read',root.as_posix():'write',
             (root/'.production/input_snapshot').as_posix():'read',
             (root/'.production/provenance.json').as_posix():'read'}
    from .core import STORE
    entries.update({(STORE/'data').as_posix():'deny',(ROOT/'data').as_posix():'deny',(ROOT/'.env').as_posix():'deny'})
    auth_parent=root/'.production/runtime/codex-auth'
    if auth_parent.exists():
        for auth in auth_parent.glob('*/auth.json'):entries[auth.as_posix()]='read'
    if (root/'01_script/SCRIPT_APPROVAL.json').exists():
        entries[(root/'01_script').as_posix()]='read'
    filesystem='{'+', '.join(json.dumps(k)+' = '+json.dumps(v) for k,v in entries.items())+'}'
    return [codex_command(),'-c','windows.sandbox="mxc"','-c','features.prefer_mxc=true',
            '-c','permissions.odd_frame.filesystem='+filesystem,
            '-c',f'permissions.odd_frame.network.enabled={str(network).lower()}',
            'sandbox','--permission-profile','odd_frame','-C',str(root),'--',*map(str,argv)]

def launch(root:Path, argv:list[str], job_id:str, *, network=False, timeout=300, cancel=None, stdin=None, verify=True, extra_env=None):
    """Run approved fixed code, never AI-generated commands. Capture all output under root."""
    from .file_writer import EpisodeWriter,assert_clean_tree
    writer=EpisodeWriter(root)
    assert_clean_tree(root)
    if verify:
        require_verified(root)
    env=environment(root,job_id,extra_env)
    logs=root/'.production/logs';logs.mkdir(parents=True,exist_ok=True)
    outpath=writer.path(f'.production/logs/{job_id}.stdout.log')
    errpath=writer.path(f'.production/logs/{job_id}.stderr.log')
    command=sandbox_argv(root,argv,network=network)
    writer.json(f'.production/logs/{job_id}.execution.json',dict(argv=command,write_root=str(root),network=network,started=time.time(),mechanism='Windows MXC'))
    with outpath.open('wb') as out,errpath.open('wb') as err:
        proc=subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                              stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        from .windows_job import ProcessJob
        try:process_job=ProcessJob(proc)
        except OSError as exc:
            proc.kill();proc.wait();raise IsolationError('Cannot enforce controller/child lifetime boundary: '+str(exc)) from exc
        with _guard:_running[job_id]=proc
        if stdin is not None:
            def feed():
                try:
                    proc.stdin.write(stdin.encode('utf-8'));proc.stdin.close()
                except (BrokenPipeError,OSError):pass
            threading.Thread(target=feed,daemon=True).start()
        deadline=time.monotonic()+timeout
        try:
            while proc.poll() is None:
                if (cancel and cancel.is_set()) or time.monotonic()>deadline:
                    # MXC terminates descendant processes when its foreground command exits.
                    subprocess.run(['taskkill.exe','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    raise IsolationError('Generation cancelled' if cancel and cancel.is_set() else f'Worker timeout after {timeout}s')
                time.sleep(.15)
        finally:
            with _guard:_running.pop(job_id,None)
            process_job.close()
    stdout=outpath.read_text(encoding='utf-8',errors='replace')
    stderr=errpath.read_text(encoding='utf-8',errors='replace')
    return dict(returncode=proc.returncode,stdout=stdout,stderr=stderr,stdout_path=str(outpath),stderr_path=str(errpath))

def verify_boundary(root:Path):
    from .file_writer import EpisodeWriter
    writer=EpisodeWriter(root)
    nonce=str(uuid.uuid4())
    result_path=f'.production/logs/boundary-{nonce}.json'
    result=launch(root,[sys.executable,'-B',str(ROOT/'scripts/episode_boundary_probe.py'),str(root),str(ROOT),result_path],
                  'boundary-'+nonce,verify=False,timeout=60)
    try:
        report=json.loads(writer.path(result_path).read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        raise IsolationError('Native isolation probe failed: '+(result['stderr'] or result['stdout'])[-1200:]) from exc
    if result['returncode'] or not report.get('verified'):
        raise IsolationError('Episode OS boundary was not verified: '+json.dumps(report))
    report['checked_at']=time.time(); report['mechanism']='Windows MXC';report['root']=str(root)
    with _guard:_verified[str(root)]=report
    writer.json('.production/isolation_status.json',report)
    return report

def require_verified(root:Path):
    if os.name!='nt':
        raise IsolationError('Strict episode execution requires Windows MXC. Use structured manual import; no unrestricted worker will be launched.')
    with _guard:report=_verified.get(str(root))
    if not report or time.time()-report['checked_at']>600:
        return verify_boundary(root)
    return report

def status(root=None):
    if root:
        from .file_writer import assert_clean_tree
        try:assert_clean_tree(root)
        except (OSError,ValueError) as exc:return dict(verified=False,available=True,message=str(exc))
        with _guard:result=_verified.get(str(root))
        if result and time.time()-result['checked_at']<=600:return result
    try:command=codex_command()
    except IsolationError as exc:return dict(verified=False,available=False,message=str(exc))
    return dict(verified=False,available=os.name=='nt',mechanism='Windows MXC',command=command,
                message='A real per-workspace permission probe must pass before automatic execution')
