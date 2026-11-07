"""Explicit synthetic QA fiction and generated audio fixtures; never user production."""
NARRATION='The key was gone. The door was open. She stayed outside.'
IDEA=dict(title='Disposable QA — The Open Door',genre='Mystery',premise='Synthetic pipeline test: an illustrated rabbit discovers an open doorway.',visual_hook='An empty key hook beside a door',narration_hook='The key was gone.',conflict='A missing key changes a choice',curiosity='Who opened the door?',emotion='Uncertainty',ending_type='Quiet choice',character_type='Expressive rabbit',feasibility='Three simple static views; one character and one doorway')
SCRIPT=dict(narration=NARRATION,brief='Disposable QA fiction for pipeline verification only.',findings=['Synthetic fixture, not a model-generated production story.'])
from .storytelling_fixtures import editorial_fields
SCRIPT.update(editorial_fields())
CHARACTER=dict(id='C001',name='Mira',description='A small illustrated ivory rabbit with two upright ears, charcoal eyes, muted slate coat, two forelegs and two hindlegs, round expressive face, no jewelry; fixed proportions and clean dark 2D ink outline.',desire='Understand the open door')
CRITERIA=['Opening attention','Curiosity','Emotional stakes','Mid-story progression','Visual comprehensibility','Micro-payoffs','Ending satisfaction','Shareability','Originality','Brand consistency']
def _legacy_package():
    scenes=[]
    for index,text in enumerate(['The key was gone.','The door was open.','She stayed outside.']):
        scenes.append(dict(scene_id=f'S{index+1:03d}',narration_text=text,beat=['Rabbit sees an empty key hook beside the closed entrance.','Rabbit sees that the same entrance is now open.','Rabbit remains outside and chooses not to cross the threshold.'][index],character_ids=['C001'],location='A quiet slate cottage porch, doorway at right, rabbit left, a single key hook beside the door.',props='One empty hook; one door, '+('closed' if index==0 else 'open')+'; no extra keys.',expression_pose='Rabbit stands left, ears upright, brows raised; gaze directed toward the doorway.',focus='The empty hook' if index==0 else 'The doorway threshold',focus_reason='The visible absence and changed entrance advance the mystery.',yellow_placement='One matte golden-yellow hook plate beside the entrance; no emitted light or glow.',lighting='Neutral soft daylight from upper left, restrained illustrated shadows toward right.',framing='Static portrait 9:16 medium shot, rabbit left and entrance right, clear negative space above center.',continuity='Same ivory rabbit, slate coat, single hook plate and cottage layout; no new props or costume.',protected_regions=[dict(x=.2,y=.48,width=.23,height=.2),dict(x=.55,y=.47,width=.08,height=.07)],caption_y=.46))
    return dict(characters=[CHARACTER],continuity_matrix='Rabbit stays left of the cottage doorway. One hook plate, no keys, slate coat unchanged. Door transitions closed to open; rabbit stays outside at end.',scenes=scenes,retention=[dict(criterion=c,rating='adequate',evidence='Synthetic QA fixture provides a visible event and coherent sequential scene coverage.',recommendation='Use actual production story review before publishing; this fixture is not a real Reel.') for c in CRITERIA],music_direction='A user-supplied quiet instrumental with restrained suspense; no vocals or sound effects.',publishing='Disposable QA only. Do not publish. This is an engineering verification fixture, not an audience claim.')

def package():
    from .continuity_fixtures import plan
    result = _legacy_package()
    result['visual_continuity'] = plan(result)
    return result
