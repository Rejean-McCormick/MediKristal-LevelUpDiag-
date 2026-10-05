import json
import os
import unittest
from pathlib import Path

from tools.refresh_suite_manifest import build_manifest

ROOT = Path(__file__).resolve().parents[1]


class SuiteManifestTests(unittest.TestCase):
    @unittest.skipIf(
        os.environ.get("LEVELUPDIAG_FAST_CI") == "1",
        "strict package integrity is a manual/release check",
    )
    def test_manifest_is_complete_and_hashes_match(self):
        current = json.loads((ROOT / "suite-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(current, build_manifest(ROOT))
        declared = {row["path"] for row in current["files"]}
        self.assertIn("LevelUpDiag-MediKristal.pyw", declared)
        self.assertIn("levelupdiag_ui.py", declared)


if __name__ == "__main__":
    unittest.main()
