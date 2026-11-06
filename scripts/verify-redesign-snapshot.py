"""Read-only proof that the owner worktree and backend baseline remain intact."""
import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[1]
original = pathlib.Path('E:/facebook')
manifest = json.loads((root / 'reports/SOURCE_SNAPSHOT.json').read_text(encoding='utf-8'))
def git(where, *args):
    return subprocess.check_output(['git', '-C', str(where), *args], text=True)
assert git(original, 'rev-parse', 'HEAD').strip() == manifest['head']
assert git(original, 'branch', '--show-current').strip() == 'main'
assert git(original, 'status', '--porcelain=v1') == manifest['status']
for row in manifest['files']:
    path = original / row['path']
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    assert digest == row['sha256'], row['path']
assert not git(root, 'diff', '--name-only', 'd445704', '--', 'services', 'brand', 'prompts', 'video').strip()
for path in git(root, 'ls-files').splitlines():
    assert not (path.startswith(('data/', 'episodes/', 'artifacts/')) and not path.endswith('.gitkeep')), path
    assert not (path.startswith('.env') and path != '.env.example'), path
print('PASS: main HEAD/status and all original dirty-source hashes unchanged; backend/creative/Remotion source unchanged after snapshot; no runtime data or private env files tracked.')
