import os
import pytest
from services.api.file_catalog import public_catalog
from services.api.file_writer import UnsafePath


def test_catalog_includes_real_empty_and_nested_directories(tmp_path):
    (tmp_path/'05_assets/images/approved').mkdir(parents=True)
    (tmp_path/'05_assets/narration').mkdir()
    image = tmp_path/'05_assets/images/approved/S001.png'
    image.write_bytes(b'image-fixture')
    entries = public_catalog(tmp_path)
    by_path = {entry['path']: entry for entry in entries}
    assert by_path['05_assets/narration']['kind'] == 'directory'
    assert by_path['05_assets/images/approved/S001.png']['size_bytes'] == len(b'image-fixture')
    assert by_path['05_assets/images/approved/S001.png']['modified_at'].endswith('+00:00')
    assert all(not entry['path'].startswith(str(tmp_path)) for entry in entries)


def test_catalog_never_traverses_private_state_or_serves_temps(tmp_path):
    (tmp_path/'.production/runtime').mkdir(parents=True)
    (tmp_path/'.production/runtime/private.json').write_text('private')
    (tmp_path/'draft.tmp').write_text('partial')
    (tmp_path/'public.txt').write_text('public')
    assert [item['path'] for item in public_catalog(tmp_path)] == ['public.txt']


def test_catalog_rejects_hard_link_aliases(tmp_path):
    source = tmp_path/'source.txt'
    source.write_text('fixture')
    os.link(source, tmp_path/'alias.txt')
    with pytest.raises(UnsafePath):
        public_catalog(tmp_path)
