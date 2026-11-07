"""Engineering metadata, explicitly not a creative-quality or live-provider claim."""
from services.api.storytelling_models import LOGIC_DOMAINS

def no_mirror():
    return dict(mode='none',has_meaningful_parallel=False,human_behavior=None,real_world_connection=None,
                storytelling_approach='Keep this synthetic engineering story entertainment-first.',
                reflective_ending_recommended=False,reason='No human analogy is asserted by this engineering fixture.')

def editorial_fields():
    return dict(human_mirror=no_mirror(),retention_audit=dict(version='3.1',
        opening_hook='A changed visible situation creates a specific question in this synthetic fixture.',
        early_stakes='The character must decide how to respond to the changed situation.',
        main_conflict='The character cannot yet account for what has changed.',
        narrative_progression=['Notice an absence.','Observe a changed state.','Choose a response.'],
        first_meaningful_discovery='The visible state differs from expectation.',major_turning_point=None,
        story_promise='Observe a surprising situation and the character response.',main_payoff='The final choice intentionally leaves the cause open.',
        ending_type='Intentionally unresolved engineering fixture',
        plot_threads=[dict(question='What caused the change?',handling='intentionally_open',evidence='The fixture tests pipeline mechanics, not a publishable locked-room solution.')],
        logic_checks=[dict(domain=d,assessment='warning' if d in ('Doors and locks','Resolution') else 'not_applicable',
                          evidence='Synthetic test scope only; this entry is not proof of editorial coherence.') for d in LOGIC_DOMAINS],
        duration_note='Engineering fixture is deliberately short; no measured voice sample or 40–55 second claim.'))

def retention_plan():
    return dict(opening_understanding='A clear unusual situation is visible immediately.',early_conflict='A concrete character goal runs into a visible obstacle.',
                developments=['A new consequence changes the character choice.'],payoff='A genre-specific consequence resolves the central situation.',
                exposition_risk='Engineering fixture; editorial quality needs separate review.')
