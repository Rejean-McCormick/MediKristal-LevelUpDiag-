import json
import tempfile
import unittest
from pathlib import Path

from levels._mk_common import operation_map, parse_pinned_requirements
from levelupdiag_core.manifest import load_manifest, resolve_selection

ROOT=Path(__file__).resolve().parents[1]

class MediKristalProfileTests(unittest.TestCase):
    def test_release_campaign_contains_all_specific_levels(self):
        manifest=load_manifest(ROOT)
        ids={x['id'] for x in resolve_selection(manifest,'release')}
        for lid in ('MK10','MK20','MK30','MK40','MK50','MK60','MK70','MK80'):
            self.assertIn(lid,ids)

    def test_operation_map_ignores_non_operation_keys(self):
        api={'paths':{'/x':{'parameters':[],'get':{'operationId':'getX'},'post':{'operationId':'postX'}}}}
        self.assertEqual(set(operation_map(api)),{'getX','postX'})

    def test_requirement_parser_rejects_unpinned(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'requirements.lock'; path.write_text('fastapi>=1\n',encoding='utf-8')
            with self.assertRaises(ValueError): parse_pinned_requirements(path)

if __name__=='__main__': unittest.main()
