"""The versioned JSON document is the single source of genre identities and meanings."""
import re
from .core import ROOT,read_json

PATH='brand/STORY_GENRES.json'

def load(root=ROOT):
    doc=read_json(root/PATH)
    if doc.get('schema_version')!='2.0' or not doc.get('version') or doc.get('brand')!='ODD FRAME':raise ValueError('Unsupported genre taxonomy')
    groups=doc.get('groups',[]);ids=[];group_ids=[]
    if len(groups)!=8:raise ValueError('The taxonomy must contain eight category groups')
    for group in groups:
        group_ids.append(group['id'])
        if not group.get('name') or not group.get('description') or not group.get('genres'):raise ValueError('Incomplete category group')
        for genre in group['genres']:
            if not re.fullmatch(r'[a-z][a-z0-9_]*',genre['id']) or not genre.get('name') or not genre.get('description'):raise ValueError('Incomplete genre definition')
            ids.append(genre['id'])
    if len(set(group_ids))!=8 or len(ids)!=24 or len(set(ids))!=24:raise ValueError('All 24 genres must occur exactly once')
    if groups[-1]['name']!='ROMANCE & OTHER':raise ValueError('The eighth category title is reserved for compatibility')
    return doc

def resolve(doc,group_id,genre_id):
    group=next((g for g in doc['groups'] if g['id']==group_id),None)
    if group is None:raise ValueError('Unknown category group')
    genre=next((g for g in group['genres'] if g['id']==genre_id),None)
    if genre is None:raise ValueError('The selected genre does not belong to this category group')
    return group,genre

def genre_by_id(doc,genre_id):
    return next((genre for group in doc['groups'] for genre in group['genres'] if genre['id']==genre_id),None)
