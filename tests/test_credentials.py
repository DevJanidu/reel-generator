import os
import pytest
from services.api import providers, main

TOKEN = 'sk-ant-oat01-' + 'A' * 40


@pytest.fixture
def env(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    path.write_text('KEEP=1\nCLAUDE_CODE_OAUTH_TOKEN=old\n', encoding='utf-8')
    monkeypatch.setattr(providers, 'ENV_PATH', path)
    for name in providers.CREDENTIALS:
        monkeypatch.delenv(name, raising=False)
    yield path
    for name in providers.CREDENTIALS:
        os.environ.pop(name, None)


def test_token_is_saved_applied_and_never_returned(env):
    out = main.provider_credential_set('CLAUDE_CODE_OAUTH_TOKEN', dict(value=TOKEN))
    row = next(c for c in out['credentials'] if c['name'] == 'CLAUDE_CODE_OAUTH_TOKEN')
    assert row['configured'] and row['stored_in_env_file'] and row['hint'] == '…' + TOKEN[-4:]
    assert TOKEN not in str(out)
    text = env.read_text(encoding='utf-8')
    assert 'KEEP=1' in text and text.count('CLAUDE_CODE_OAUTH_TOKEN=') == 1 and TOKEN in text
    assert os.environ['CLAUDE_CODE_OAUTH_TOKEN'] == TOKEN and providers.claude_auth_mode() == 'subscription_token'
    assert TOKEN not in providers.redact('failed with ' + TOKEN)
    cleared = main.provider_credential_clear('CLAUDE_CODE_OAUTH_TOKEN')
    assert not next(c for c in cleared['credentials'] if c['name'] == 'CLAUDE_CODE_OAUTH_TOKEN')['configured']
    assert 'CLAUDE_CODE_OAUTH_TOKEN' not in env.read_text(encoding='utf-8') and 'KEEP=1' in env.read_text(encoding='utf-8')


@pytest.mark.parametrize('name,value', [
    ('CLAUDE_CODE_OAUTH_TOKEN', 'short'), ('CLAUDE_CODE_OAUTH_TOKEN', 'sk-ant-oat01-has space ' + 'x' * 30),
    ('CLAUDE_CODE_OAUTH_TOKEN', 'wrong-prefix-' + 'x' * 30), ('PATH', TOKEN), ('SOMETHING_ELSE', TOKEN)])
def test_invalid_or_foreign_credentials_are_rejected(env, name, value):
    with pytest.raises(ValueError):
        main.provider_credential_set(name, dict(value=value))
    assert env.read_text(encoding='utf-8') == 'KEEP=1\nCLAUDE_CODE_OAUTH_TOKEN=old\n'


def test_writes_require_the_controller_capability(store):
    from fastapi.testclient import TestClient
    client = TestClient(main.app, base_url='http://127.0.0.1:8123')
    assert client.put('/api/providers/credentials/ODD_AI_API_KEY', json=dict(value='x' * 30)).status_code == 401
    assert client.delete('/api/providers/credentials/ODD_AI_API_KEY').status_code == 401
    assert client.get('/api/providers/credentials').status_code == 200


def test_controller_status_reports_authorization_without_revealing_the_key(store):
    from fastapi.testclient import TestClient
    from services.api import core
    client = TestClient(main.app, base_url='http://127.0.0.1:8123')
    assert client.get('/api/controller/status').json() == dict(authorized=False)
    assert client.get('/api/controller/status', headers={'x-odd-controller': 'wrong'}).json() == dict(authorized=False)
    ok = client.get('/api/controller/status', headers={'x-odd-controller': core.controller_token()})
    assert ok.json() == dict(authorized=True) and core.controller_token() not in ok.text


def test_saved_token_survives_a_restart_and_is_read_by_any_browser(env, monkeypatch):
    from dotenv import dotenv_values
    main.provider_credential_set('ODD_AI_API_KEY', dict(value='key-' + 'B' * 30))
    assert dotenv_values(env)['ODD_AI_API_KEY'] == 'key-' + 'B' * 30          # what the next process start loads
    monkeypatch.delenv('ODD_AI_API_KEY')                                      # simulate a fresh process before dotenv load
    from dotenv import load_dotenv
    load_dotenv(env)
    row = next(c for c in main.provider_credentials()['credentials'] if c['name'] == 'ODD_AI_API_KEY')
    assert row['configured'] and row['stored_in_env_file']                    # status is server-side, not per-browser
    assert not env.with_name('.env.tmp').exists()
