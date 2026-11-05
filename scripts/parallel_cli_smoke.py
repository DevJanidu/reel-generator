"""Two REAL simultaneous short creative requests; disposable, no approval/export claims."""
import json,os,sys,time,uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
STORE=ROOT/'artifacts/parallel-cli'/time.strftime('%Y%m%d-%H%M%S')
os.environ['ODD_DATA_ROOT']=str(STORE);os.environ['ODD_AI_PROVIDER']='codex_cli'
from services.api import core,creative,skills,snapshots,providers,isolation
from services.api.file_writer import EpisodeWriter
from tests.fixtures import IDEA
from pydantic import BaseModel,ConfigDict,Field

class Response(BaseModel):
    model_config=ConfigDict(extra='forbid')
    episode_id:str
    character:str
    opening_line:str=Field(min_length=15,max_length=220)

def main():
    core.init_db()
    eps=[creative.create_episode({**IDEA,'title':'Parallel CLI diagnostic '+name}) for name in ['A','B']]
    protected=list((ROOT/'brand').rglob('*.md'))+list((ROOT/'prompts').glob('*.md'))+[ROOT/'video/remotion/src/index.tsx']
    before={str(p):core.sha(p.read_bytes()) for p in protected}
    def run(ep):
        start=time.monotonic();root=creative.epdir(ep);runid='parallel-'+uuid.uuid4().hex
        config={**core.settings(),'provider':'codex_cli','max_concurrent_jobs':2}
        animal='otter' if ep['id']==eps[0]['id'] else 'fox'
        messages,provenance=skills.model_request('01_IDEA_GENERATION.md',dict(task='PARALLEL CREATIVE ISOLATION DIAGNOSTIC: not a ten-idea menu. Return only episode_id, character and one original concrete fictional opening_line using ONLY the required character. Name that species in the opening line. Do not use the other diagnostic cast. No complete story, files or tools.',episode_id=ep['code'],required_character=animal,output_json_schema=Response.model_json_schema()),config,root=snapshots.source_root(root))
        data=Response.model_validate(providers.generate(config,messages,Response.model_json_schema(),root,runid)).model_dump()
        assert data['episode_id']==ep['code']
        assert data['character'].lower()==animal and animal in data['opening_line'].lower()
        EpisodeWriter(root).json('reports/PARALLEL_CREATIVE_DIAGNOSTIC.json',dict(response=data,provenance=provenance,request_id=runid))
        assert not list(root.glob('.production/runtime/codex-auth/*/auth.json'))
        return dict(episode_id=ep['code'],request_id=runid,root=str(root),start=start,end=time.monotonic(),isolation=isolation.status(root),response=data)
    with ThreadPoolExecutor(max_workers=2) as executor:reports=list(executor.map(run,eps))
    overlap=min(r['end'] for r in reports)-max(r['start'] for r in reports)
    assert overlap>0
    assert all(core.sha(p.read_bytes())==before[str(p)] for p in protected)
    result=dict(result='PASS',real_cli_requests=2,concurrent_overlap_seconds=overlap,shared_hashes_unchanged=True,reports=reports,
                scope='Two short opening-line creative probes in separate real episode workspaces; not two full Reels or renders')
    core.write_json(STORE/'RESULT.json',result);core.write_json(ROOT/'artifacts/parallel-cli/latest.json',result)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
