import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from services.api import continuity, core, creative, main
from services.api.models import Flow, Package
from .fixtures import package, NARRATION, IDEA, SCRIPT


def compile(p=None,root=None,narration=NARRATION):
    return continuity.compile_plan(p or package(),narration,'OF_QA',root or core.ROOT/'artifacts')


def test_standalone_three_scene_contract(tmp_path):
    p=package();result=compile(p,tmp_path)
    assert result['report']['status']=='PASS'
    flow=Flow.model_validate(result['flow']).model_dump()
    assert set(flow)=={'schema_version','episode_id','jobs'}
    assert len(flow['jobs'])==3
    for job in flow['jobs']:
        assert set(job)=={'job_id','scene_id','type','prompt','source_image','output_name'}
        assert job['source_image'] is None
        assert p['characters'][0]['description'] in job['prompt']
        assert continuity.RESTRICTIONS in job['prompt']
        assert not continuity.lint(job['prompt'].split(continuity.STYLE)[0])
    assert result['report']['visual_inspection']=='NOT_PERFORMED'
    assert [s['state']['door'] for s in result['report']['scenes']]==['closed','open','open']


@pytest.mark.parametrize('text',[
    'Telephoto cross-section from south', 'Technical elevation showing roof',
    'Engineering survey drawing', 'Measurement annotation', 'Labeled marker A/B/C',
    'Scene S001', 'Same instant as previous scene', 'Scale drawing', 'Measurement arrows',
    'Stake A is 0.80 m above roof', 'River water +0.40 m', 'Face at .33,.35',
    '| x | y | elevation |', 'TODO show this', '{{character}}', 'same house as before',
    'Draw an arrow toward the roof',
])
def test_leaks_block_export(text,tmp_path):
    p=package();p['visual_continuity']['ledger']['shots'][0]['composition']='Wide shot. '+text
    result=compile(p,tmp_path)
    assert result['flow'] is None
    assert result['report']['status']=='BLOCKED'


def test_numbers_in_legitimate_art_direction_are_allowed(tmp_path):
    p=package();p['visual_continuity']['ledger']['shots'][0]['moment']='The rabbit holds 2 matching bags with 3 stitched leaf motifs on each bag.'
    assert compile(p,tmp_path)['flow']


@pytest.mark.parametrize('fault', ['character_text','absent','unknown','duplicate','state','fixed','evidence','giant','planes','changed_scale','missing_scale','missing_shot','sequence','hash','narration','placeholder'])
def test_continuity_contradictions_block(fault,tmp_path):
    p=package();plan=p['visual_continuity'];shots=plan['ledger']['shots'];first=shots[0]
    if fault=='character_text':plan['bible']['assets'][0]['description']+=' Different fur.'
    elif fault=='absent':first['character_map']={}
    elif fault=='unknown':first['asset_ids'].append('CHAR_INTRUDER')
    elif fault=='duplicate':first['asset_ids'].append('CHAR_MIRA')
    elif fault=='state':shots[1]['changes'][0]['before']='already open'
    elif fault=='fixed':plan['ledger']['fixed_properties']['door']='closed'
    elif fault=='evidence':shots[1]['changes'][0]['narration_evidence']='A nonexistent flood arrived'
    elif fault=='giant':first['scale_checks'][0]['character_height']=9
    elif fault=='planes':first['scale_checks'][0]['character_plane']='foreground'
    elif fault=='changed_scale':shots[1]['scale_checks'][0]['door_height']=1.8
    elif fault=='missing_scale':first['scale_checks']=[]
    elif fault=='missing_shot':first['composition']='The subject is beside the cottage doorway.'
    elif fault=='sequence':shots.reverse()
    elif fault=='hash':plan['bible']['narration_sha256']='0'*64
    elif fault=='narration':p['scenes'][0]['narration_text']='A new story.'
    elif fault=='placeholder':plan['bible']['assets'][1]['description']+=' [BUILDING_DESCRIPTION]'
    result=compile(p,tmp_path)
    assert result['flow'] is None, fault
    assert result['report']['status']=='BLOCKED'


def test_reference_real_bytes_and_no_attachment_claim(tmp_path):
    import io
    from PIL import Image
    buffer=io.BytesIO();Image.new('RGB',(20,20),'gray').save(buffer,format='PNG');raw=buffer.getvalue()
    p=package();b=p['visual_continuity']['bible']
    b['assets'][0]['reference_ids']=['REF_MIRA']
    b['references']=[dict(id='REF_MIRA',category='character',path='refs/mira.png',sha256=hashlib.sha256(raw).hexdigest(),approved=True,essential=True)]
    assert compile(p,tmp_path)['flow'] is None
    (tmp_path/'refs').mkdir();(tmp_path/'refs/mira.png').write_bytes(raw)
    r=compile(p,tmp_path)
    assert r['flow']
    ref=r['references']['jobs'][0]['references'][0]
    assert ref['status']=='AVAILABLE' and not ref['attached']
    b['references'][0]['essential']=False  # tampering never degrades an approved pin to an optional warning
    (tmp_path/'refs/mira.png').write_bytes(b'changed')
    assert compile(p,tmp_path)['flow'] is None
    b['references'][0]['path']='../outside.png'
    with pytest.raises(ValueError):compile(p,tmp_path)


def test_provider_strict_schema_retains_all_structured_state_fields():
    from services.api.providers import strict_schema
    schema=strict_schema(Package.model_json_schema())
    def check(node):
        if isinstance(node,dict):
            if node.get('type')=='object':
                assert node.get('additionalProperties') is False
                assert node.get('properties'), 'An open map would be erased by strict provider schema conversion'
            for v in node.values():check(v)
        elif isinstance(node,list):
            for v in node:check(v)
    check(schema)


def test_flashback_has_independent_chain_and_internal_numbers_do_not_leak(tmp_path):
    p=package();plan=p['visual_continuity'];plan['ledger']['shots'][2]['timeline']='memory'
    plan['ledger']['initial_states']['memory']={'door':'closed'}
    plan['bible']['assets'][1]['specifications']={'door':'1.60 m','coordinates':'x=24 y=50'}
    r=compile(p,tmp_path)
    assert r['flow']
    assert r['report']['scenes'][2]['state']['door']=='closed'
    assert 'x=24' not in json.dumps(r['flow']) and '1.60 m' not in json.dumps(r['flow'])


def test_prop_inventory_and_geography(tmp_path):
    p=package();plan=p['visual_continuity'];b=plan['bible'];shots=plan['ledger']['shots']
    b['assets'].append(dict(id='PROP_KEY',kind='prop',name='Key',description='One small ivory key with an unmarked rounded bow and a single short stem.',specifications={'count':'1'},provenance='Synthetic mystery inventory',design_status='approved',reference_ids=[]))
    shots[0]['asset_ids'].append('PROP_KEY');shots[0]['prop_counts']={'PROP_KEY':2}
    assert compile(p,tmp_path)['flow'] is None
    shots[0]['prop_counts']['PROP_KEY']=1
    assert compile(p,tmp_path)['flow']
    b['relationships']=[dict(subject='CHAR_MIRA',relation=r,object='BUILDING_COTTAGE',evidence='Synthetic fixed geography') for r in ('left_of','right_of')]
    assert compile(p,tmp_path)['flow'] is None


def test_explicit_water_state_cannot_contradict_ledger(tmp_path):
    p=package();plan=p['visual_continuity']
    plan['ledger']['initial_states']['present']['water']='low'
    plan['ledger']['shots'][0]['state_assertions']={'water':'high'}
    assert compile(p,tmp_path)['flow'] is None
    plan['ledger']['shots'][0]['state_assertions']['water']='low'
    assert compile(p,tmp_path)['flow']


@pytest.mark.parametrize('genre,species,object_name,beats',[
    ('Mystery','rabbit','key',['A rabbit discovers an empty key hook.','The rabbit finds the missing key beneath a leaf.','The rabbit returns the key to the hook.']),
    ('Comedy','otter','bag',['An otter picks up an identical bag by mistake.','The otter opens the bag and discovers carrots.','The otter returns the bag with an embarrassed smile.']),
    ('Betrayal','fox','gem',['A fox conceals a valuable gem behind its back.','The fox hands a plain pebble to a friend outside the crop.','The fox keeps the hidden gem and looks away.']),
    ('Romance','deer','flower',['A deer waits beside a familiar garden gate.','The deer leaves a small flower beside the gate.','The deer returns to find the flower carefully placed upright.']),
    ('Horror','badger','hatch',['A badger discovers a loose hatch beneath its home.','The badger lifts the hatch and peers into the dark.','The badger closes the hatch and steps back in fear.']),
    ('Adventure','squirrel','satchel',['A squirrel leaves a forest clearing with a satchel.','The squirrel crosses a rocky ridge with the satchel.','The squirrel reaches a sheltered valley with the satchel.']),
])
def test_six_genres_without_river_contamination(genre,species,object_name,beats,tmp_path):
    if genre=='Comedy':beats=['An otter and a hedgehog accidentally exchange identical bags.','The two animals discover that they have each taken the wrong bag.','The animals return the bags to their original owners.']
    if genre=='Romance':beats=['Two deer meet beside a familiar garden gate.','The two deer meet again and leave a flower beside the gate.','The deer return together to find the flower carefully placed upright.']
    p=package();p['characters'][0]['description']=f'An adult illustrated {species} with ivory facial features, charcoal eyes, warm brown body, proportionate limbs and a plain slate vest. Original expressive face, stable short rounded muzzle and natural tail.'
    plan=p['visual_continuity'];plan['bible']['assets']=plan['bible']['assets'][:1]
    plan['bible']['assets'][0]['description']=p['characters'][0]['description']
    plan['bible']['assets'].append(dict(id='PROP_STORY_OBJECT',kind='prop',name=object_name,description=f'One small {object_name} in muted ochre with a distinctive leaf-shaped mark, unlettered and reflecting ordinary light.',specifications={'count':'1'},provenance='Genre-specific synthetic design',design_status='approved',reference_ids=[]))
    if genre in ('Comedy','Romance'):
        other_species='hedgehog' if genre=='Comedy' else 'deer'
        description=f'An adult illustrated {other_species} with a compact body, ivory muzzle, dark oval eyes and a plain charcoal scarf. Shorter than the first character, with fixed natural limbs and consistent original facial features.'
        p['characters'].append(dict(id='C002',name='Neri',description=description,desire='Share the encounter'))
        plan['bible']['assets'].append(dict(id='CHAR_NERI',kind='character',name='Neri',description=description,specifications={'relative_height':'shorter than the first character','height_units':'0.9'},provenance='Explicit genre-specific companion',design_status='approved',reference_ids=[]))
        plan['bible']['relationships']=[dict(subject='CHAR_MIRA',relation='taller_than',object='CHAR_NERI',evidence='Explicit companion proportions')]
    if genre=='Comedy':
        prop=next(a for a in plan['bible']['assets'] if a['kind']=='prop')
        prop.update(description='Two identical small muted-ochre canvas bags, each with a rounded rectangular body, a short strap and one leaf-shaped stitched mark. Both are unlettered, ordinary cloth without glow.',specifications={'count':'2'})
    plan['bible']['geography']='A forest path joins a clearing, rocky ridge and sheltered valley.' if genre=='Adventure' else 'A stable garden clearing beside a small home with a path to the entrance.'
    plan['bible']['palette_lighting']='Warm restrained afternoon daylight supports '+genre+'.' if genre!='Horror' else 'Motivated low lamplight around the hatch, faces readable in ivory.'
    plan['ledger']['initial_states']={'present':{'object':'initial position'}}
    plan['ledger']['fixed_properties']={}
    for i,(s,shot) in enumerate(zip(p['scenes'],plan['ledger']['shots'])):
        s['narration_text']=beats[i];s['beat']=beats[i]
        if genre in ('Comedy','Romance'):s['character_ids']=['C001','C002']
        shot['storyboard_sha256']=continuity.storyboard_digest(s)
        shot.update(moment=beats[i],asset_ids=['CHAR_MIRA','PROP_STORY_OBJECT'],scale_checks=[],changes=[],prop_counts={'PROP_STORY_OBJECT':1},
                    expression_pose=f'The {species} has a readable, story-appropriate expression and holds a clear natural pose.',lighting=plan['bible']['palette_lighting'],
                    geography=plan['bible']['geography'],visible_state=f'The {object_name} is intact; the {species} wears the approved slate vest.',composition='Eye-level medium shot with readable face, hands and the important object.')
        if i:shot['changes']=[dict(key='object',before='initial position' if i==1 else 'second position',after='second position' if i==1 else 'final position',narration_evidence=beats[i])]
        if genre in ('Comedy','Romance'):
            shot['asset_ids'].append('CHAR_NERI');shot['character_map']['C002']='CHAR_NERI'
            shot['expression_pose']='Both animals have readable natural expressions, distinct silhouettes and separate hands. Preserve the first character as taller at equal camera depth.'
        if genre=='Comedy':shot['prop_counts']['PROP_STORY_OBJECT']=2
        if genre in ('Mystery','Romance') and i==0:
            shot['asset_ids'].remove('PROP_STORY_OBJECT');shot['prop_counts']={}
            shot['visible_state']='No carried object is visible yet; all characters keep their approved clothing.'
        if genre=='Adventure':
            location_id=['LOC_CLEARING','LOC_RIDGE','LOC_VALLEY'][i]
            geography=['A forest clearing with tall trunks around a path exiting uphill to the right.', 'A rocky ridge above the forest, with a winding path descending toward a sheltered valley.', 'A sheltered grassy valley below the rocky ridge, with the entry path visible behind the squirrel.'][i]
            plan['bible']['assets'].append(dict(id=location_id,kind='location',name=location_id.split('_')[1].title(),description=geography,specifications={},provenance='Explicit adventure route',design_status='approved',reference_ids=[]))
            shot['asset_ids'].append(location_id);shot['geography']=geography
    if genre=='Comedy':
        plan['ledger']['initial_states']['present']['bag_ownership']='original owners'
        plan['ledger']['shots'][0]['changes'].append(dict(key='bag_ownership',before='original owners',after='exchanged',narration_evidence=beats[0]))
        plan['ledger']['shots'][2]['changes'].append(dict(key='bag_ownership',before='exchanged',after='original owners',narration_evidence=beats[2]))
    narration=' '.join(beats);plan['bible']['narration_sha256']=hashlib.sha256(narration.encode()).hexdigest()
    result=compile(p,tmp_path,narration)
    assert result['flow'],result['report']
    rendered=json.dumps(result['flow']).lower()
    assert all(word not in rendered for word in ('river','lodge','survey','mara','alder'))
    if genre!='Horror':assert 'automatic horror' not in rendered
    # Carrying another episode's bible is deterministically rejected by story identity.
    plan['bible']['narration_sha256']=hashlib.sha256(NARRATION.encode()).hexdigest()
    assert compile(p,tmp_path,narration)['flow'] is None


def test_historical_river_regression_read_only(tmp_path):
    from scripts.continuity_regression import river_plan
    root=core.ROOT/'episodes/OF_R002_the-stakes-in-the-river'
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'episode.json',root/'04_google_flow/IMAGE_JOBS.json',root/'01_script/narration.txt')}
    source=json.loads((root/'episode.json').read_text(encoding='utf-8'));p=river_plan(source)
    r=continuity.compile_plan(p,source['data']['script']['narration'],'OF_R002',root)
    assert r['flow'] and len(r['flow']['jobs'])==20
    assert r['report']['status']=='WARNING'
    s2=r['flow']['jobs'][1]['prompt']
    assert 'whole lodge' in s2 and 'entire stake planted' in s2 and 'river itself remains low' in s2
    assert 'side elevation' not in s2.lower() and 'S002' not in s2
    for scene,job in zip(p['scenes'],r['flow']['jobs']):
        assert not continuity.lint(job['prompt'].split(continuity.STYLE)[0])
        for cid in scene['character_ids']:
            assert next(c['description'] for c in p['characters'] if c['id']==cid) in job['prompt']
    assert before=={path:hashlib.sha256(__import__('pathlib').Path(path).read_bytes()).hexdigest() for path in before}


def test_review_and_regeneration_preserve_plan_and_record_real_image_hash(store):
    from PIL import Image
    ep=creative.create_episode(IDEA);core.update_episode(ep['id'],'AWAITING_APPROVAL',script=SCRIPT)
    run=creative.approve(ep['id'],NARRATION)
    p=package();b=p['visual_continuity']['bible']
    b['assets'][0]['reference_ids']=['REF_MIRA']
    b['references']=[dict(id='REF_MIRA',category='character',path=None,sha256=None,approved=False,essential=False)]
    creative.complete_run(run['run_id'],p,manual=True)
    ep=core.episode(ep['id']);root=creative.epdir(ep);sid='S001'
    Image.new('RGB',(90,160),'gray').save(root/'05_assets/images/S001.png')
    original=core.read_json(root/'02_characters/VISUAL_BIBLE.json')
    client=TestClient(main.app);headers={'X-Odd-Controller':core.controller_token()}
    assert client.post(f'/api/episodes/{ep["id"]}/continuity/review',json=dict(scene_id=sid,path='05_assets/images/S001.png',status='PASS'),headers=headers).status_code==422
    response=client.post(f'/api/episodes/{ep["id"]}/continuity/review',json=dict(scene_id=sid,path='05_assets/images/S001.png',status='REJECT',inspected=True),headers=headers)
    assert response.status_code==200,response.text
    assert response.json()['inspection']=='OWNER_ATTESTED'
    response=client.post(f'/api/episodes/{ep["id"]}/continuity/regenerate/S001',headers=headers)
    assert response.status_code==200,response.text
    regenerated=Flow.model_validate(core.read_json(root/response.json()['path']))
    assert len(regenerated.jobs)==1
    assert regenerated.jobs[0].prompt==core.read_json(root/'04_google_flow/IMAGE_JOBS.json')['jobs'][0]['prompt']
    assert core.read_json(root/'02_characters/VISUAL_BIBLE.json')==original
    pin=client.post(f'/api/episodes/{ep["id"]}/continuity/references',json=dict(reference_id='REF_MIRA',path='05_assets/images/S001.png',approved=True),headers=headers)
    assert pin.status_code==200,pin.text
    assert pin.json()['attached'] is False
    pinned_path=root/pin.json()['reference']['path']
    pinned_bytes=pinned_path.read_bytes()
    Image.new('RGB',(90,160),'ivory').save(root/'05_assets/images/S001.png')
    assert pinned_path.read_bytes()==pinned_bytes
    assert client.get(f'/api/episodes/{ep["id"]}').json()['batch_review']['history'][-1]['current_image_matches'] is False
    assert client.post(f'/api/episodes/{ep["id"]}/continuity/references',json=dict(reference_id='REF_MIRA',path='05_assets/images/S001.png',approved=True),headers=headers).status_code==422
    assert core.read_json(root/'02_characters/VISUAL_BIBLE.json')==original
