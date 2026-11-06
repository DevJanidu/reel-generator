"""Read agent-authored samples as manual fixtures; no provider or model invocation."""
import json
from pathlib import Path
from services.api.storytelling_models import LOGIC_DOMAINS

DATA=json.loads((Path(__file__).parent/'data/storytelling_v31_samples.json').read_text('utf-8'))

def script_sample(index=0):
    row=DATA['scripts'][index]
    connection=row['human_connection']
    mirror=dict(mode=row['mode'],has_meaningful_parallel=connection is not None,
                human_behavior={'comedy':'Recognition and accidental status','betrayal':'Exploiting a trusted collaborator','romance':'Mutual affection and fear of rejection'}.get(row['genre']) if connection else None,
                real_world_connection=connection,storytelling_approach=row['mirror_reason'],reflective_ending_recommended=False,reason=row['mirror_reason'])
    audit=dict(version='3.1',opening_hook=row['narration'].split('. ')[0]+'.',early_stakes=row['beats'][1],
               main_conflict=row['promise'],narrative_progression=row['beats'],first_meaningful_discovery=row['first_discovery'],
               major_turning_point=row['turning_point'],story_promise=row['promise'],main_payoff=row['payoff'],ending_type=row['ending'],
               plot_threads=[dict(question=row['promise'],handling='intentionally_open' if row['genre']=='horror' else 'answered',evidence=row['payoff'])],
               logic_checks=[dict(domain=domain,assessment='warning',evidence='Editorial/visual verification remains necessary. '+row['logic_warning']) for domain in LOGIC_DOMAINS],
               duration_note=DATA['duration'])
    return dict(narration=row['narration'],brief=row['brief'],human_mirror=mirror,retention_audit=audit,findings=[row['editorial_review'],'Agent-authored manual regression example; not a live provider result or approved production script.'])

SECOND_COMEDY_BATCH=[
 ('The Substitute Star','An illustrated penguin magician and a wooden coat rack','A penguin receives a coat rack instead of a stand-in for his first magic show. The hooks catch his props, and the audience interprets the falling objects as an exceptional trick.','Can a performer finish the show when the inanimate substitute gets all the applause?','The audience stops clapping whenever the penguin bows without the rack.','The next poster gives the rack top billing and labels the penguin as its assistant.'),
 ('The Waterproof Soup','A beaver chef and a nervous otter waiter','A beaver chef promises soup that will never spill. He freezes every bowl solid, and the waiter proudly serves ice blocks while the guests wait patiently for their dinner to become possible.','How will guests eat a soup that cannot escape its bowl?','The waiter starts lending tiny scarves to increasingly cold diners.','The chef wins a dessert prize while still insisting he runs a soup restaurant.'),
 ('The Traveling Mirror','A wolf barber and one very polished portable mirror','A barber wheels a mirror outside to attract customers. A goose refuses to leave the handsome customer reflected in it, and every attempt to move the queue merely moves the goose closer to her own reflection.','Can a barber get a first customer past a customer who is not actually there?','The goose begins recommending hairstyles to the reflection and requests matching appointments.','The barber opens a second chair for the imaginary customer and finally gets paid for both.'),
 ('The Reserved Puddle','A flamingo usher and two illustrated frogs','An usher sells front-row puddle seats for a garden concert. A light shower joins all the puddles, leaving him trying to distinguish expensive water from ordinary water using increasingly soggy paper ropes.','How can an usher preserve a seating chart that the rain keeps rearranging?','The frogs float their reserved cushions straight through the imaginary dividing line.','The usher announces free seating and is politely asked to stop standing on the stage.'),
 ('The Tiny Drum Solo','A tortoise drummer and a mouse stage manager','A tortoise rents a drum kit by the inch to save money. The tiny drums fit inside a teacup, but his huge ceremonial drumsticks turn the miniature finale into an elaborate exercise in holding very still.','Can a grand entrance survive an instrument smaller than the drummer badge?','The manager raises the cup on increasingly tall pedestals until it is level with the tortoise face.','The tortoise taps once with a toothpick and receives the longest standing ovation of the night.')
]
