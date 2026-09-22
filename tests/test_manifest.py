import unittest
from pathlib import Path
from levelupdiag_core.manifest import load_manifest, resolve_selection

class ManifestTests(unittest.TestCase):
    def test_baseline_dependencies_resolve(self):
        root=Path(__file__).resolve().parents[1]
        m=load_manifest(root)
        ids=[x["id"] for x in resolve_selection(m,"baseline")]
        self.assertIn("N00",ids); self.assertIn("N06",ids)
