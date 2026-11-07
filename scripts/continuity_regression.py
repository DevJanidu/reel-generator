"""Explicit owner development migration. Reads historical inputs; writes artifacts only.

No model usage. Proposed details are never promoted to approved episode designs.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.api import continuity, core, skills, snapshots
from services.api.file_writer import EpisodeWriter
import os

if os.getenv('ODD_EPISODE_WORKER')=='1' or os.getenv('ODD_EXECUTION_MODE')=='episode':
    raise SystemExit('This regression migration is a development-only operation')


def river_plan(source):
    p = copy.deepcopy(source['data']['package'])
    assets = []
    def asset(id, kind, name, description, specifications=None, proposed=False):
        assets.append(dict(id=id,kind=kind,name=name,description=description,specifications=specifications or {},
                           provenance='Historical approved-script package; missing structural details explicitly proposed for review.',
                           design_status='proposed' if proposed else 'approved',reference_ids=['REF_'+id]))
    for c in p['characters']:
        asset('CHAR_'+c['name'].upper(),'character',c['name'],c['description'],{'source_character_id':c['id'],'height_units':'1' if c['id']=='C001' else '1.1'})
    asset('BUILDING_MARA_LODGE','building','Mara lodge',
          "Mara's compact rounded reed-and-stick lodge sits on the lower riverbank. Its low curved reed roof bears exactly three pale reed repair strips on the uphill path-facing side, bound side by side. Dark stick walls support the roof; the entrance faces uphill toward the path, to the right in this view. The doorway is comfortably taller than an adult beaver, and the roof spans several beaver body widths. The curved rear follows the rounded footprint; show no invented windows.",
          {'owner':'Mara','elevation':'lower bank; roof below planned flood contour','patch_count':'3','unspecified':'Exact dimensions, windows and rear construction absent from source.'},True)
    asset('BUILDING_ALDER_LODGE','building','Alder lodge',
          "Alder's new rounded stick-and-reed lodge stands on the dry upstream plateau, higher than the marked future flood boundary. Its intact curved reed roof and dark stick walls frame a single attached plank door facing downhill to the left. The doorway is comfortably taller than an adult beaver; the building spans several beaver body widths. The curved side and rear follow its rounded footprint. A narrow western window lights the guest alcove; show it only in interior views.",
          {'owner':'Alder','elevation':'safe upstream plateau above flood contour','unspecified':'Exact exterior architecture absent; proposed consistent reed construction.'},True)
    asset('LOC_RIVERBANK','location','Riverbank',
          'A river runs along the left of a rising bank. The low riverside ground lies left and the uphill path climbs to the right toward a dry upstream plateau. A separate bare resting shelf beside the path stays above the marked flood boundary and outside the upstream home plot.',
          {'contour':'All three stakes mark equal flood elevation, above lower lodge roof, below upstream plateau and resting shelf.'})
    asset('PROP_SURVEY_STAKE','prop','Survey stakes',
          'Slender unlettered matte golden-yellow wooden survey stakes, each a single straight shaft planted securely in the soil. The yellow surface indicates the planned reservoir boundary; it reflects light without emitting it. There are exactly three stakes in the landscape. They are separate from roof reeds, signboards and fence posts.',
          {'count':'3','indicator':'Source specifies yellow stakes, not a separately approved indicator band.','size':'Source does not fix numeric dimensions.'})
    asset('PROP_BLANKET','prop','Blanket','One plain slate wool blanket belonging to Mara, large enough to wrap her compact body. The soft folded cloth has no writing or pattern and never becomes a second blanket.')
    asset('PROP_BOWL','prop','Bowl','One shallow muted-ochre wooden bowl belonging to Mara, small enough to carry in a forepaw, with a distinctive three-leaf carving inside its rim. It is empty and unbroken; natural wood reflects light without glowing.')
    asset('PROP_BED','prop','Guest bed','One unused guest bed inside the upstream lodge alcove, covered by an undisturbed slate cover with one plain gray pillow. It remains unoccupied, without personal belongings or a second bed.')
    # Per-scene asset selection is deliberately confined to this regression fixture.
    selection = [
        ['BUILDING_MARA_LODGE','LOC_RIVERBANK','PROP_SURVEY_STAKE'],
        ['BUILDING_MARA_LODGE','LOC_RIVERBANK','PROP_SURVEY_STAKE'],
        ['BUILDING_MARA_LODGE','LOC_RIVERBANK'],['BUILDING_MARA_LODGE'],
        ['BUILDING_MARA_LODGE','BUILDING_ALDER_LODGE','LOC_RIVERBANK','PROP_SURVEY_STAKE'],
        *[['BUILDING_ALDER_LODGE','LOC_RIVERBANK','PROP_SURVEY_STAKE'] for _ in range(4)],
        ['BUILDING_MARA_LODGE','LOC_RIVERBANK','PROP_SURVEY_STAKE'],
        ['BUILDING_MARA_LODGE'],['LOC_RIVERBANK','PROP_SURVEY_STAKE'],
        *[['BUILDING_ALDER_LODGE','LOC_RIVERBANK','PROP_SURVEY_STAKE'] for _ in range(4)],
        ['BUILDING_MARA_LODGE','PROP_BLANKET','PROP_BOWL'],
        ['BUILDING_MARA_LODGE','LOC_RIVERBANK','PROP_SURVEY_STAKE'],
        ['LOC_RIVERBANK','PROP_BLANKET','PROP_BOWL'],['BUILDING_ALDER_LODGE','PROP_BED']]
    framing = [
        'Wide establishing shot from across the riverbank. Show the whole lower lodge and the entire planted stake on the higher slope; Mara is a small full-body figure on the roof with head, feet and tail inside comfortable margins.',
        "Cinematic wide shot at eye level from across the lower bank. Show the whole lodge, its doorway and patched roof, and the entire stake planted in the rising hillside to the right. Mara stands on the roof and looks toward the marker with alarm. The yellow marker is visibly higher than the roof in the real landscape. Keep roof and stake readable together without a forced perspective alignment.",
        'Medium two-shot of the roof repair, both faces, separate forepaws and tails clearly readable.',
        'Intimate medium close-up of Mara looking trustingly toward Alder at the right edge, with the seated repair reeds below their faces.',
        'Wide establishing shot showing the low lodge far downhill left and the dry new lodge on the higher plateau right, the path and the three planted stakes across the intervening bank. Mara is a small full-body figure on the path, with head, feet and tail in view.',
        *['Eye-level medium two-shot at the upstream doorway; Mara left, Alder right, with readable faces and separate silhouettes. Buildings remain much larger than the beavers; distant stakes stay small below the plateau.' for _ in range(2)],
        'Close profile of Alder beside the closed door; a small distant stake is glimpsed through a gap behind him. His expression is guarded.',
        'Wide shot of the dry upstream home and descending bank; include the whole building above the distant planted marker, and the two small beavers beside the door.',
        'Over-the-shoulder view past Mara toward her whole small lodge far downhill left; keep the patched roof and nearby planted stake clearly readable in their actual landscape positions.',
        'Close detail of the three finished reed roof repairs and bindings, filling the frame with textured illustrated roof material.',
        'Close-up reaction of Mara with her notched left ear and uneven tuft visible, a small planted stake on the hillside behind her; no full-body framing needed.',
        *['Eye-level medium two-shot at the upstream threshold; Mara left and Alder right, separate silhouettes and readable expressions, the door behind Alder.' for _ in range(4)],
        'Intimate medium interior shot of Mara carrying her folded blanket under one arm and holding the bowl in the other forepaw. Keep the bowl carving visible beneath her gaze.',
        'Wide shot of the whole empty lower lodge, its intact patched roof, doorway touched by floodwater and the entire planted stake above on the bank. Illustrated water fills the foreground.',
        'Medium-wide shot of Mara curled on bare higher ground, blanket wrapped around her and bowl beside her forepaws. The flooded bank is distant below left; she is safely above it.',
        'Medium interior shot of the pristine unoccupied guest bed and pillow in the upstream alcove, filled with restrained dusk light from the narrow left window.']
    water_low = 'The river is low and below the lower lodge doorstep; there is no present flooding.'
    shots=[]
    for i,s in enumerate(p['scenes']):
        cids={c:'CHAR_'+next(x['name'].upper() for x in p['characters'] if x['id']==c) for c in s['character_ids']}
        ids=list(cids.values())+selection[i]
        geography = 'Lower riverbank slopes down toward the river on the left; the path climbs right to the dry upstream plateau.'
        if i in (2,3,10,16,19):geography='The camera depicts the roof or interior at its established location; terrain outside the crop is not relocated.'
        state=s['props']+' '+(water_low if i<17 else 'Dusk: water covers the lower doorstep but stays below the marked boundary and safe resting shelf.')
        if i==2:state+=' Two repair strips are seated and the third is being fitted.'
        if i==3:state+=' Three repair strips are now seated.'
        if i in (0,1,4,9,17):state+=' The complete patched roof stays below the planned boundary marked on the hillside; the marker is not planted in the roof.'
        # Explicit scene snapshots for view state; temporal transitions below remain internal.
        moment=s['beat']
        if i==1:moment="Mara discovers that a yellow reservoir marker planted on the rising bank stands higher than her patched lodge roof. Her alarm reveals the threat to her home while the river itself remains low."
        checks=[]
        for c in cids.values():
            for b in ids:
                if b.startswith('BUILDING_'):
                    separate=(i in (4,9))
                    checks.append(dict(character_id=c,building_id=b,character_height=1.1 if c=='CHAR_ALDER' else 1,
                        door_height=1.5,perspective='separate_planes' if separate else 'same_plane',
                        character_plane='foreground' if separate else 'middle_ground',building_plane='background' if separate else 'middle_ground',
                        composition='Keep each beaver shorter than the doorway at equal depth. Distant lodges remain on their own landscape plane; never enlarge a beaver beside a distant roof.'))
        shots.append(dict(scene_id=s['scene_id'],storyboard_sha256=continuity.storyboard_digest(s),timeline='repair_memory' if i in (2,3) else 'present',asset_ids=ids,character_map=cids,
                          moment=moment,expression_pose=s['expression_pose'],lighting=s['lighting'].replace('Same neutral memory daylight','Neutral upper-left daylight for the earlier repair memory').replace('Same ','Neutral '),composition=framing[i],geography=geography,visible_state=state,changes=[],scale_checks=checks))
    def change(i,key,before,after):
        shots[i]['changes'].append(dict(key=key,before=before,after=after,narration_evidence=p['scenes'][i]['narration_text']))
    change(3,'repairs','two seated; third being fitted','three complete')
    change(5,'door','closed','attached, being fitted')
    change(6,'door','attached, being fitted','closed')
    shots[6]['changes'][-1].update(evidence_source='storyboard',narration_evidence='Door now closed after fitting')
    change(14,'door','closed','open inward')
    change(16,'belongings','at home','Mara carries blanket and bowl')
    change(17,'water','below doorstep','covering doorstep; below flood contour')
    change(18,'belongings','Mara carries blanket and bowl','blanket wrapped around Mara; bowl beside her')
    states={'present':{'water':'below doorstep','repairs':'three complete','door':'closed','belongings':'at home'},'repair_memory':{'water':'below doorstep','repairs':'two seated; third being fitted'}}
    for i,shot in enumerate(shots):
        current=states[shot['timeline']]
        for delta in shot['changes']:current[delta['key']]=delta['after']
        shot['state_assertions']=dict(current)
        shot['prop_counts']={aid:(3 if i==4 else 1) for aid in shot['asset_ids'] if aid.startswith('PROP_')}
    plan=dict(bible=dict(engine=continuity.ENGINE,version=continuity.VERSION,narration_sha256=source['data']['approval']['sha256'],
        assets=assets,relationships=[dict(subject='BUILDING_MARA_LODGE',relation='below',object='BUILDING_ALDER_LODGE',evidence='Approved narration and continuity matrix establish lower bank and safe upstream plot.')],
        geography=p['continuity_matrix'],palette_lighting='Charcoal and slate environmental materials frame readable ivory facial features and approved brown fur. Gold marks the focal physical clue; it is not a luminous overlay.',
        references=[dict(id='REF_'+a['id'],category=a['kind'],path=None,sha256=None,approved=False,essential=False) for a in assets]),
        ledger=dict(initial_states={'present':{'water':'below doorstep','repairs':'three complete','door':'closed','belongings':'at home'},'repair_memory':{'water':'below doorstep','repairs':'two seated; third being fitted'}},
            fixed_properties={'lower_lodge':'lower bank','upstream_lodge':'safe plateau','stake_count':'3','stake_contour':'above lower roof; below safe plateau'},shots=shots))
    p['visual_continuity']=plan
    return p


def main():
    root=core.ROOT/'episodes/OF_R002_the-stakes-in-the-river'
    source=json.loads((root/'episode.json').read_text(encoding='utf-8'))
    # Full pinned input loader verifies every source, master, stage and context
    # budget; no provider is invoked and no immutable historical input is repinned.
    pinned=snapshots.source_root(root)
    _,evidence=skills.model_request('06_FLOW_IMAGE_PROMPTS.md',{'purpose':'Explicit disposable cinematic compiler regression','approved_narration':source['data']['script']['narration']},
        dict(provider='manual',model='',output_tokens=12000,context_tokens=200000),root=pinned)
    p=river_plan(source)
    result=continuity.compile_plan(p,source['data']['script']['narration'],source['code'],root)
    out=core.ROOT/'artifacts/visual-continuity'/('OF_R002-'+core.now().replace(':','').replace('+','_'))
    out.mkdir(parents=True,exist_ok=False)
    writer=EpisodeWriter(out)
    writer.json('PACKAGE.json',p,replace=False)
    for name,key in [('VISUAL_BIBLE','bible'),('STORY_STATE_LEDGER','ledger'),('REFERENCE_MANIFEST','references'),('CONTINUITY_VALIDATION','report')]:
        writer.json(name+'.json',result[key],replace=False)
    writer.json('PROVENANCE.json',dict(pinned_inputs=evidence,source_episode_sha256=core.sha((root/'episode.json').read_bytes()),
        source_queue_sha256=core.sha((root/'04_google_flow/IMAGE_JOBS.json').read_bytes()),
        notes=['Disposable version; production episode untouched.','Structure details absent from historical source are proposed.','No images generated or inspected.','No numeric stake elevations invented.']),replace=False)
    original=json.loads((root/'04_google_flow/IMAGE_JOBS.json').read_text(encoding='utf-8'))
    comparison=dict(method='Deterministic prompt-text comparison, not generated-image comparison',
        original_scene_count=len(original['jobs']),
        original_findings=[dict(scene_id=j['scene_id'],findings=continuity.lint(j['prompt'].split('STRICT 2D:')[0])) for j in original['jobs']],
        revised_findings=[] if not result['flow'] else [dict(scene_id=j['scene_id'],findings=continuity.lint(j['prompt'].split(continuity.STYLE)[0])) for j in result['flow']['jobs']],
        visual_inspection='NOT_PERFORMED',extension_import='UNVERIFIED')
    writer.json('COMPARISON.json',comparison,replace=False)
    if result['flow']:
        writer.json('IMAGE_JOBS.json',result['flow'],replace=False)
        writer.text('IMAGE_PROMPTS.md','\n\n'.join('## '+j['scene_id']+'\n'+j['prompt'] for j in result['flow']['jobs']),replace=False)
        for i in range(0,len(result['flow']['jobs']),10):
            writer.json(f'batches/batch_{i//10+1:02d}.json',{**result['flow'],'jobs':result['flow']['jobs'][i:i+10]},replace=False)
    print(json.dumps(dict(output=str(out),status=result['report']['status'],issue_count=len(result['report']['issues'])),indent=2))
    if not result['flow']:raise SystemExit(1)


if __name__=='__main__':main()
