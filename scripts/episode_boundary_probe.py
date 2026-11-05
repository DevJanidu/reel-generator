"""Non-model executable adversarial probe, invoked only inside native isolation."""
import json,os,subprocess,sys,uuid,ctypes
from pathlib import Path
root=Path(sys.argv[1]);app=Path(sys.argv[2]);result=root/sys.argv[3]
checks=[]
def deny(name,fn):
    try:fn();checks.append(dict(name=name,blocked=False))
    except OSError as e:checks.append(dict(name=name,blocked=True,error=e.winerror if hasattr(e,'winerror') else e.errno))
def writable_open(path):
    with path.open('r+b'):pass # no real shared source is modified even if isolation fails
for relative in ['prompts/00_MASTER_PROMPT.md','brand/skills/ODD_FRAME_2D_STILL_DESIGN_SKILL.md','video/remotion/src/index.tsx']:
    deny('shared:'+relative,lambda p=app/relative:writable_open(p))
deny('repository root',lambda:(app/('forbidden-'+uuid.uuid4().hex)).write_text('denied'))
deny('parent traversal',lambda:(root/'..'/('forbidden-'+uuid.uuid4().hex)).write_text('denied'))
deny('global cache',lambda:(app/'data'/('forbidden-'+uuid.uuid4().hex)).write_text('denied'))
snap=root/'.production/input_snapshot/prompts/00_MASTER_PROMPT.md'
if snap.exists():deny('immutable snapshot',lambda:writable_open(snap))
child=subprocess.run([sys.executable,'-B','-c',"from pathlib import Path; import sys; Path(sys.argv[1]).write_text('denied')",str(app/('forbidden-child-'+uuid.uuid4().hex))],capture_output=True)
checks.append(dict(name='inherited subprocess',blocked=child.returncode!=0))
own=root/'.production/temp'/('probe-'+uuid.uuid4().hex+'.txt');own.parent.mkdir(parents=True,exist_ok=True)
own.write_text('authorized');allowed=own.read_text()=='authorized';own.unlink()
result.parent.mkdir(parents=True,exist_ok=True)
from ctypes import wintypes as w
kernel=ctypes.WinDLL('kernel32',use_last_error=True);adv=ctypes.WinDLL('advapi32',use_last_error=True)
kernel.GetCurrentProcess.restype=w.HANDLE
adv.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]
adv.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD,ctypes.POINTER(w.DWORD)]
token=w.HANDLE();appcontainer=w.DWORD();elevation=w.DWORD();size=w.DWORD()
token_checked=bool(adv.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)))
if token_checked:
    token_checked=bool(adv.GetTokenInformation(token,29,ctypes.byref(appcontainer),4,ctypes.byref(size))) and bool(adv.GetTokenInformation(token,20,ctypes.byref(elevation),4,ctypes.byref(size)))
    kernel.CloseHandle(token)
report=dict(verified=allowed and all(c['blocked'] for c in checks) and token_checked and bool(appcontainer.value) and not bool(elevation.value),own_write=allowed,checks=checks,
            token_verified=token_checked,appcontainer=bool(appcontainer.value),elevated=bool(elevation.value))
result.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
sys.exit(0 if report['verified'] else 4)
