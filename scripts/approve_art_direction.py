"""Owner-only development activation; never run from an episode or implicitly on import."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.api.core import ROOT,read_json,write_json,now
from services.api.skills import validate_art_direction,art_direction_receipt


def approve(source_root=ROOT,approved_by='local owner via explicit development command'):
    if os.getenv('ODD_EPISODE_WORKER')=='1' or os.getenv('ODD_EXECUTION_MODE')=='episode':
        raise ValueError('Episode workers cannot approve global creative skills')
    path=source_root/'brand/SKILLS_MANIFEST.json'
    manifest=read_json(path);registry=manifest['visual_art_direction']
    candidate=registry['candidate'];validate_art_direction(candidate,source_root)
    receipt={**candidate,'status':'approved','approved_by':approved_by,'approved_at':now()}
    registry.update(approved=receipt,required=True)
    write_json(path,manifest)
    return receipt


def main():
    parser=argparse.ArgumentParser(description='Validate the v3 candidate; activate only after explicit owner approval.')
    parser.add_argument('--approve',action='store_true',help='Record owner approval for this exact skill/profile checksum for FUTURE snapshots only')
    args=parser.parse_args()
    if args.approve:receipt=approve()
    else:
        manifest=read_json(ROOT/'brand/SKILLS_MANIFEST.json')
        receipt=art_direction_receipt(validate_art_direction(manifest['visual_art_direction']['candidate']))
    import json
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
