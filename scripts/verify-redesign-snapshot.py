"""Read-only proof that the owner worktree and backend baseline remain intact."""
import ast
import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parents[1]
original = pathlib.Path('E:/facebook')
manifest = json.loads((root / 'reports/SOURCE_SNAPSHOT.json').read_text(encoding='utf-8'))
def git(where, *args):
    return subprocess.check_output(['git', '-C', str(where), *args], text=True, encoding='utf-8')
assert git(original, 'rev-parse', 'HEAD').strip() == manifest['head']
assert git(original, 'branch', '--show-current').strip() == 'main'
assert git(original, 'status', '--porcelain=v1') == manifest['status']
for row in manifest['files']:
    path = original / row['path']
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    assert digest == row['sha256'], row['path']
changed=set(git(root,'diff','--name-only','d445704','--','services','brand','prompts','video').splitlines())
assert changed <= {'services/api/main.py','services/api/file_catalog.py'},changed
baseline=ast.parse(git(root,'show','d445704:services/api/main.py'))
current=ast.parse((root/'services/api/main.py').read_text(encoding='utf-8'))
for tree in [baseline,current]:
    tree.body=[node for node in tree.body if not (isinstance(node,ast.FunctionDef) and node.name=='detail')]
assert ast.dump(baseline)==ast.dump(current),'Changes outside read-only episode detail metadata'
for path in git(root, 'ls-files').splitlines():
    assert not (path.startswith(('data/', 'episodes/', 'artifacts/')) and not path.endswith('.gitkeep')), path
    assert not (path.startswith('.env') and path != '.env.example'), path
print('PASS: main HEAD/status and all original dirty-source hashes unchanged; only the reviewed read-only file catalog differs in backend; creative/Remotion source unchanged; no runtime data or private env files tracked.')
