from pathlib import Path
import hashlib
import json
import os
import sqlite3
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if os.getenv('ODD_EPISODE_WORKER')!='1':load_dotenv(ROOT / '.env')
STORE = Path(os.getenv('ODD_DATA_ROOT', str(ROOT))).resolve()

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(value):
    return hashlib.sha256(value.encode('utf-8') if isinstance(value, str) else value).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    path = Path(path)
    writer=_episode_writer(path)
    if writer:
        return writer.json(path.absolute().relative_to(writer.root).as_posix(),value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)

def textfile(path, text):
    path = Path(path)
    writer=_episode_writer(path)
    if writer:return writer.text(path.absolute().relative_to(writer.root).as_posix(),text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))

@contextmanager
def db():
    if os.getenv('ODD_EPISODE_WORKER')=='1':raise PermissionError('Episode workers cannot open the shared application database')
    (STORE/'data').mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(STORE/'data/odd_frame.sqlite', timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

def init_db():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS episodes (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, path TEXT UNIQUE, title TEXT, status TEXT, data TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, episode_id INTEGER, at TEXT, stage TEXT, message TEXT);
        CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, episode_id INTEGER, task TEXT, status TEXT, request TEXT, provenance TEXT, result TEXT, error TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, episode_id INTEGER, kind TEXT, status TEXT, progress REAL DEFAULT 0, stage TEXT, error TEXT, created TEXT, updated TEXT);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY, episode_id INTEGER, payload TEXT, created TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS active_job ON jobs(episode_id,kind) WHERE status IN ('QUEUED','RUNNING');
        ''')
        columns={r['name'] for r in c.execute('PRAGMA table_info(runs)')}
        for name,definition in [('workspace','TEXT'),('stage','TEXT'),('progress','REAL DEFAULT 0'),('provider','TEXT')]:
            if name not in columns:c.execute(f'ALTER TABLE runs ADD COLUMN {name} {definition}')
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_active_creative ON runs(episode_id) WHERE episode_id IS NOT NULL AND status IN ('QUEUED','RUNNING')")
    # This controller capability is outside all worker-readable paths. Never send it to workers.
    token_path=STORE/'data/controller-access.json'
    if not token_path.exists():
        write_json(token_path,dict(token=secrets.token_urlsafe(48)))

def controller_token():
    if os.getenv('ODD_EPISODE_WORKER')=='1':raise PermissionError('Controller capability is unavailable to episode workers')
    return read_json(STORE/'data/controller-access.json')['token']

def _episode_writer(path):
    from .file_writer import EpisodeWriter,UnsafePath
    path=Path(path).absolute()
    if os.getenv('ODD_EPISODE_WORKER')=='1':
        root=Path(os.environ['EPISODE_WRITE_ROOT']).absolute()
        if not path.is_relative_to(root):raise UnsafePath('Worker write would escape EPISODE_WRITE_ROOT')
        return EpisodeWriter(root)
    episodes_root=(STORE/'episodes').absolute()
    if path.is_relative_to(episodes_root):
        for parent in path.parents:
            if (parent/'.production').is_dir():return EpisodeWriter(parent)
    return None

def episode(eid):
    if os.getenv('ODD_EPISODE_WORKER')=='1':
        root=Path(os.environ['EPISODE_WRITE_ROOT']);value=read_json(root/'episode.json')
        if value['id']!=eid:raise PermissionError('Worker attempted to access a different episode')
        state_path=root/'production_status.json'
        if state_path.exists():
            state=read_json(state_path)
            if 'data' in state:value.update(status=state['status'],data=state['data'],updated=state['updated'])
        return value
    with db() as c:
        row = c.execute('SELECT * FROM episodes WHERE id=?', (eid,)).fetchone()
    if not row:
        raise ValueError('Episode not found')
    result = dict(row)
    result['data'] = json.loads(result['data'])
    local=epdir(result)/'episode.json'
    if local.exists():
        authoritative=read_json(local)
        if any(authoritative.get(k)!=result[k] for k in ('id','code','path')):raise ValueError('Episode identity differs from trusted controller registration')
        result=authoritative
        state=read_json(epdir(result)/'production_status.json') if (epdir(result)/'production_status.json').exists() else {}
        if 'data' in state:
            if state.get('episode_id')!=result['code']:raise ValueError('Production state identity mismatch')
            result.update(status=state['status'],data=state['data'],updated=state['updated'])
    return result

def epdir(ep):
    path = (STORE / ep['path']).resolve()
    if not path.is_relative_to((STORE/'episodes').resolve()):
        raise ValueError('Invalid episode path')
    if os.getenv('ODD_EPISODE_WORKER')=='1' and path!=Path(os.environ['EPISODE_WRITE_ROOT']).resolve():raise PermissionError('Cross-episode access rejected')
    return path

def update_episode(eid, status=None, **changes):
    from .file_writer import episode_lock
    initial=episode(eid)
    with episode_lock(epdir(initial)):
        ep=episode(eid);ep['data'].update(changes);ep['status']=status or ep['status'];ep['updated']=now()
        history_path=epdir(ep)/'.production/history.json'
        history=read_json(history_path) if history_path.exists() else []
        if status:history.append(dict(id=len(history)+1,episode_id=eid,at=ep['updated'],stage=status,message=changes.get('message',status)))
        write_json(history_path,history)
        write_json(epdir(ep)/'production_status.json',dict(episode_id=ep['code'],status=ep['status'],updated=ep['updated'],data=ep['data'],history=history,error=ep['data'].get('error')))
        write_json(epdir(ep)/'episode.json',ep)
    if os.getenv('ODD_EPISODE_WORKER')!='1':index_episode(ep)
    return ep

def index_episode(ep):
    """Trusted controller's read-derived dashboard index; never called by a worker."""
    with db() as c:
        c.execute('UPDATE episodes SET status=?,data=?,updated=? WHERE id=?',(ep['status'],json.dumps(ep['data']),ep['updated'],ep['id']))

def sync_index():
    with db() as c:ids=[r['id'] for r in c.execute('SELECT id FROM episodes')]
    for eid in ids:
        try:index_episode(episode(eid))
        except (OSError,ValueError):pass

def settings():
    with db() as c:
        saved = {r['key']:json.loads(r['value']) for r in c.execute('SELECT * FROM settings')}
    return dict(provider=saved.get('provider', os.getenv('ODD_AI_PROVIDER','manual')),
                base_url=saved.get('base_url',os.getenv('ODD_AI_BASE_URL','https://api.openai.com/v1')),
                model=saved.get('model',os.getenv('ODD_AI_MODEL','')),
                context_tokens=int(saved.get('context_tokens',os.getenv('ODD_AI_CONTEXT_TOKENS','200000'))),
                output_tokens=int(saved.get('output_tokens',os.getenv('ODD_AI_OUTPUT_TOKENS','12000'))),
                timeout_seconds=int(saved.get('timeout_seconds',os.getenv('ODD_AI_TIMEOUT_SECONDS','300'))),
                max_concurrent_jobs=int(saved.get('max_concurrent_jobs',os.getenv('ODD_AI_MAX_CONCURRENT_JOBS','1'))),
                api_key_configured=bool(os.getenv('ODD_AI_API_KEY')),claude_api_key_configured=bool(os.getenv('ANTHROPIC_API_KEY')),root=str(STORE),
                caption_defaults='Barlow Condensed 800 · white/black · centered · quick pop',
                output='1080×1920 · 30 FPS · H.264/AAC', music_preferences=saved.get('music_preferences','Genre-specific instrumental; no vocals'))
