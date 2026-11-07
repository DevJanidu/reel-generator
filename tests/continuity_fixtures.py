"""Synthetic structured plan for integration fixtures; no live generation."""
import hashlib
from services.api.continuity import storyboard_digest


def plan(package):
    c=package['characters'][0]
    cid='CHAR_MIRA'
    building='BUILDING_COTTAGE'
    narration=' '.join(s['narration_text'] for s in package['scenes'])
    asset=lambda id,kind,description:dict(id=id,kind=kind,name=id.split('_',1)[1].title(),description=description,specifications={'height_units':'1'} if kind=='character' else {},provenance='Explicit synthetic test design',design_status='approved',reference_ids=[])
    shots=[]
    for i,s in enumerate(package['scenes']):
        shots.append(dict(scene_id=s['scene_id'],storyboard_sha256=storyboard_digest(s),timeline='present',asset_ids=[cid,building],character_map={c['id']:cid},
            moment=s['beat'],expression_pose=s['expression_pose'],lighting=s['lighting'],composition='Eye-level medium shot of the rabbit beside the cottage entrance; the character is comfortably shorter than the door.',
            geography='The rabbit stands left of the doorway; the cottage porch remains on the right.',
            visible_state=s['props'],changes=[] if i!=1 else [dict(key='door',before='closed',after='open',narration_evidence=s['narration_text'])],
            scale_checks=[dict(character_id=cid,building_id=building,character_height=1,door_height=1.6,perspective='same_plane',character_plane='middle_ground',building_plane='middle_ground',composition='The rabbit and doorway share a depth plane; the door is comfortably taller than the rabbit.')]))
    return dict(bible=dict(narration_sha256=hashlib.sha256(narration.encode()).hexdigest(),assets=[asset(cid,'character',c['description']),asset(building,'building','A quiet slate cottage porch with a single attached door at the right, and one empty key hook beside it. The doorway is taller than the rabbit.')],relationships=[],geography='Rabbit left, cottage doorway right; the porch and cottage stay fixed.',palette_lighting='Neutral daylight appropriate to this quiet mystery, with one matte gold hook.',references=[]),ledger=dict(initial_states={'present':{'door':'closed'}},fixed_properties={'cottage':'right'},shots=shots))
