from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class Idea(Strict):
    title: str=Field(min_length=3,max_length=150)
    genre: str=Field(min_length=3)
    premise: str=Field(min_length=10)
    visual_hook: str=Field(min_length=10)
    narration_hook: str=Field(min_length=5)
    conflict: str=Field(min_length=5)
    curiosity: str=Field(min_length=5)
    emotion: str
    ending_type: str
    character_type: str
    feasibility: str=Field(min_length=5)

class Ideas(Strict):
    ideas: list[Idea]=Field(min_length=10,max_length=10)

class Script(Strict):
    narration: str=Field(min_length=30,max_length=15000)
    brief: str=Field(min_length=10)
    findings: list[str]=Field(min_length=1)

class Character(Strict):
    id: str=Field(pattern=r'^C\d{3}$')
    name: str
    description: str=Field(min_length=80)
    desire: str=Field(min_length=5)

class Region(Strict):
    x: float=Field(ge=0,le=1)
    y: float=Field(ge=0,le=1)
    width: float=Field(gt=0,le=1)
    height: float=Field(gt=0,le=1)

class Scene(Strict):
    scene_id: str=Field(pattern=r'^S\d{3}$')
    narration_text: str=Field(min_length=1)
    beat: str=Field(min_length=15)
    character_ids: list[str]
    location: str=Field(min_length=30)
    props: str=Field(min_length=10)
    expression_pose: str=Field(min_length=20)
    focus: str=Field(min_length=5)
    focus_reason: str=Field(min_length=10)
    yellow_placement: str=Field(min_length=20)
    lighting: str=Field(min_length=20)
    framing: str=Field(min_length=20)
    continuity: str=Field(min_length=20)
    protected_regions: list[Region]=Field(min_length=1)
    caption_y: float=Field(default=.46,ge=.2,le=.7)
    # Cinematic Flow editing hints. The renderer only trusts values validated here; unknown names are rejected.
    transition_in: Literal['cut','crossfade','dip_to_dark']='cut'
    transition_reason: str=Field(default='',max_length=240)
    caption_style: Literal['default','soft_fade']='default'
    emphasis_phrase: str=Field(default='',max_length=80)

class AuditItem(Strict):
    criterion: Literal['Opening attention','Curiosity','Emotional stakes','Mid-story progression','Visual comprehensibility','Micro-payoffs','Ending satisfaction','Shareability','Originality','Brand consistency']
    rating: Literal['strong','adequate','revise']
    evidence: str=Field(min_length=10)
    recommendation: str=Field(min_length=5)

class Package(Strict):
    characters: list[Character]=Field(min_length=1)
    continuity_matrix: str=Field(min_length=80)
    scenes: list[Scene]=Field(min_length=1,max_length=100)
    retention: list[AuditItem]=Field(min_length=10,max_length=10)
    music_direction: str=Field(min_length=30)
    publishing: str=Field(min_length=30)

class Job(Strict):
    job_id: str
    scene_id: str
    type: Literal['image']
    prompt: str=Field(min_length=300)
    source_image: None=None
    output_name: str

class Flow(Strict):
    schema_version: Literal['1.0']='1.0'
    episode_id: str
    jobs: list[Job]
