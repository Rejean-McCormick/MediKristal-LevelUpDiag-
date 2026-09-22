import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package_files():
    files = []
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if rel.name == 'suite-manifest.json':
            continue
        if '__pycache__' in rel.parts or '.levelupdiag' in rel.parts:
            continue
        files.append(rel.as_posix())
    return sorted(files)


class SuiteManifestTests(unittest.TestCase):
    def test_manifest_is_complete_and_hashes_match(self):
        manifest = json.loads((ROOT / 'suite-manifest.json').read_text(encoding='utf-8'))
        declared = {row['path']: row for row in manifest['files']}
        self.assertEqual(sorted(declared), package_files())
        self.assertIn('LevelUpDiag-MediKristal.pyw', declared)
        self.assertIn('levelupdiag_ui.py', declared)
        for rel, row in declared.items():
            data = (ROOT / rel).read_bytes()
            self.assertEqual(row['bytes'], len(data), rel)
            self.assertEqual(row['sha256'], hashlib.sha256(data).hexdigest(), rel)


if __name__ == '__main__':
    unittest.main()
