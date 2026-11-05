import pytest
from services.api import core,creative,media,worker

@pytest.fixture(autouse=True)
def no_live_async_providers(monkeypatch):
    import asyncio
    async def forbidden(*args,**kwargs):
        raise AssertionError('Ordinary pytest cannot launch a live CLI provider; mock the async subprocess or use the explicit verification script')
    monkeypatch.setattr(asyncio,'create_subprocess_exec',forbidden)

@pytest.fixture
def store(tmp_path,monkeypatch):
    monkeypatch.setenv('ODD_AI_PROVIDER','manual')
    monkeypatch.setenv('ODD_DATA_ROOT',str(tmp_path))
    for module in [core,creative,media,worker]:
        monkeypatch.setattr(module,'STORE',tmp_path)
    core.init_db()
    return tmp_path
