"""Version two concept contracts, independent of the saved ten-idea v1 contract."""
from typing import Literal
from pydantic import Field,StrictInt
from .models import Strict
from .storytelling_models import HumanMirror, RetentionPlan, Preference, VoiceCalibration

CRITERIA=('Genre relevance','Hook clarity','Originality','Character motivation','Narrative escalation','Intentional ending','Visual feasibility','Curiosity','Short-form suitability','Batch diversity')

class ConceptAssessment(Strict):
    criterion:Literal['Genre relevance','Hook clarity','Originality','Character motivation','Narrative escalation','Intentional ending','Visual feasibility','Curiosity','Short-form suitability','Batch diversity']
    assessment:Literal['ready','revise']
    evidence:str=Field(min_length=12,max_length=400)

class StoryConcept(Strict):
    human_mirror: HumanMirror | None = None
    retention_plan: RetentionPlan | None = None
    idea_id:str=Field(pattern=r'^[A-Za-z0-9_-]{5,90}$')
    title:str=Field(min_length=3,max_length=150)
    category_group_id:str=Field(min_length=3,max_length=60)
    primary_genre_id:str=Field(min_length=3,max_length=60)
    secondary_genre_id:str|None=None
    logline:str=Field(min_length=25,max_length=500)
    premise:str=Field(min_length=60,max_length=1800)
    opening_visual_hook:str=Field(min_length=20,max_length=500)
    main_characters:list[str]=Field(min_length=1,max_length=6)
    central_conflict:str=Field(min_length=20,max_length=600)
    key_escalation:str=Field(min_length=20,max_length=600)
    ending_direction:str=Field(min_length=15,max_length=500)
    target_emotion:str=Field(min_length=5,max_length=200)
    visual_feasibility:str=Field(min_length=25,max_length=600)
    duration_seconds:StrictInt=Field(ge=15,le=120)
    quality_audit:list[ConceptAssessment]=Field(min_length=10,max_length=10)

class GenreIdeas(Strict):
    schema_version:Literal['2.0']
    category_group_id:str
    primary_genre_id:str
    ideas:list[StoryConcept]=Field(min_length=5,max_length=5)

class SessionSelection(Strict):
    human_mirror_preference: Preference = 'automatic'
    voice_calibration: VoiceCalibration | None = None
    category_group_id:str=Field(min_length=3,max_length=60)
    primary_genre_id:str|None=None
    secondary_genre_id:str|None=None
    surprise:bool=False

class BatchRequest(Strict):
    idempotency_key:str=Field(pattern=r'^[a-f0-9-]{32,36}$')
    expected_provider:Literal['codex_cli','claude_cli','manual','openai-compatible']|None=None

class CustomStory(Strict):
    idempotency_key:str=Field(pattern=r'^[a-f0-9-]{32,36}$')
    title:str=Field(min_length=3,max_length=150)
    premise:str=Field(default='',max_length=5000)
    keep_premise:bool=False
    expected_provider:Literal['codex_cli','claude_cli','manual','openai-compatible']|None=None
