"""Optional, versioned editorial data; legacy episode contracts remain readable."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class EditorialModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

Preference = Literal['automatic', 'encourage_when_natural', 'pure_entertainment']
LOGIC_DOMAINS = ('Physical rules', 'Object possession', 'Doors and locks', 'Character knowledge',
                 'Geography', 'Chronology', 'Motivations', 'Consequences', 'Character continuity', 'Resolution')

class HumanMirror(EditorialModel):
    mode: Literal['natural', 'subtle', 'none']
    has_meaningful_parallel: bool
    human_behavior: str | None
    real_world_connection: str | None
    storytelling_approach: str = Field(min_length=10, max_length=1200)
    reflective_ending_recommended: bool
    reason: str = Field(min_length=10, max_length=1200)

    @model_validator(mode='after')
    def coherent(self):
        if self.mode == 'none':
            if self.has_meaningful_parallel or self.human_behavior is not None or self.real_world_connection is not None or self.reflective_ending_recommended:
                raise ValueError('Pure entertainment must not fabricate a parallel or reflective ending')
        elif not self.has_meaningful_parallel or not (self.human_behavior or '').strip() or not (self.real_world_connection or '').strip():
            raise ValueError('Natural/subtle mode needs a concrete meaningful parallel')
        return self

class RetentionPlan(EditorialModel):
    opening_understanding: str = Field(min_length=10, max_length=800)
    early_conflict: str = Field(min_length=10, max_length=800)
    developments: list[str] = Field(min_length=1, max_length=12)
    payoff: str = Field(min_length=10, max_length=800)
    exposition_risk: str = Field(min_length=8, max_length=800)

class PlotThread(EditorialModel):
    question: str = Field(min_length=5, max_length=500)
    handling: Literal['answered', 'intentionally_open', 'removed']
    evidence: str = Field(min_length=10, max_length=900)

class LogicCheck(EditorialModel):
    domain: Literal['Physical rules', 'Object possession', 'Doors and locks', 'Character knowledge',
                    'Geography', 'Chronology', 'Motivations', 'Consequences', 'Character continuity', 'Resolution']
    assessment: Literal['clear', 'warning', 'not_applicable']
    evidence: str = Field(min_length=10, max_length=900)

class RetentionAudit(EditorialModel):
    version: Literal['3.1']
    opening_hook: str = Field(min_length=10, max_length=900)
    early_stakes: str = Field(min_length=10, max_length=900)
    main_conflict: str = Field(min_length=10, max_length=900)
    narrative_progression: list[str] = Field(min_length=1, max_length=18)
    first_meaningful_discovery: str | None
    major_turning_point: str | None
    story_promise: str = Field(min_length=10, max_length=900)
    main_payoff: str = Field(min_length=10, max_length=900)
    ending_type: str = Field(min_length=3, max_length=120)
    plot_threads: list[PlotThread] = Field(min_length=1, max_length=12)
    logic_checks: list[LogicCheck] = Field(min_length=10, max_length=10)
    duration_note: str = Field(min_length=10, max_length=900)

    @model_validator(mode='after')
    def all_logic_domains(self):
        if {x.domain for x in self.logic_checks} != set(LOGIC_DOMAINS):
            raise ValueError('Audit must address all ten distinct logic/continuity domains')
        return self

class VoiceCalibration(EditorialModel):
    voice: str = Field(min_length=2, max_length=160)
    measured_words: int = Field(gt=0, le=10000, strict=True)
    measured_seconds: float = Field(gt=0, le=3600)
    source: str = Field(min_length=5, max_length=500)
    observed_at: str = Field(min_length=10, max_length=80)

    @model_validator(mode='after')
    def dated(self):
        from datetime import datetime
        datetime.fromisoformat(self.observed_at.replace('Z','+00:00'))
        return self
