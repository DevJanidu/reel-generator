"""Explicit DEVELOPMENT operation: prepare read-only shared native media dependencies."""
from pathlib import Path
import hashlib,json,shutil,subprocess,os
ROOT=Path(__file__).resolve().parents[1]
if os.getenv('ODD_EPISODE_WORKER')=='1':raise SystemExit('Runtime setup is forbidden during episode production')
target=ROOT/'video/remotion/runtime-binaries';target.mkdir(parents=True,exist_ok=True)
source=ROOT/'node_modules/@remotion/compositor-win32-x64-msvc'
for path in source.iterdir():
    if path.suffix.lower() in ('.exe','.dll') and path.name not in ('ffmpeg.exe','ffprobe.exe'):shutil.copyfile(path,target/path.name)
for name in ('ffmpeg','ffprobe'):
    executable=shutil.which(name+'.exe')
    if not executable:raise SystemExit(name+' is required on PATH')
    shutil.copyfile(executable,target/('ffmpeg-native.exe' if name=='ffmpeg' else name+'.exe'))
compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if not compiler.exists():raise SystemExit('Windows .NET Framework C# compiler is required to prepare the FFmpeg 9 compatibility runtime')
subprocess.run([str(compiler),'/nologo','/target:exe','/platform:x64','/out:'+str(target/'ffmpeg.exe'),str(ROOT/'scripts/ffmpeg_compat.cs')],check=True,capture_output=True)
files=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),byte_length=p.stat().st_size) for p in target.iterdir() if p.suffix.lower() in ('.exe','.dll')]
(target/'manifest.json').write_text(json.dumps(dict(version='1',source='Installed FFmpeg tools plus unchanged Remotion compositor/runtime libraries',files=files),indent=2),encoding='utf-8')
print('Prepared shared read-only media runtime: '+str(target))
