import tempfile
import unittest
import zipfile
from pathlib import Path

from levelupdiag_ui import detect_target_kind, summary_text


class UIHelperTests(unittest.TestCase):
    def test_detect_repository_and_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "MediKristal"
            (repo / "backend").mkdir(parents=True)
            (repo / "contracts").mkdir()
            (repo / "backend" / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (repo / "contracts" / "openapi.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(detect_target_kind(repo), "repository")

            archive = root / "target.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("hello.txt", "ok")
            self.assertEqual(detect_target_kind(archive), "zip")
            self.assertIsNone(detect_target_kind(root / "missing.zip"))

    def test_summary_text_contains_verdict_and_levels(self):
        rendered = summary_text({
            "selection": "release",
            "verdict": "WARN",
            "run_id": "run-1",
            "target_repo_root": "/tmp/MediKristal",
            "levels": [{"id": "MK20", "verdict": "PASS", "name": "Contracts"}],
        })
        self.assertIn("Verdict: WARN", rendered)
        self.assertIn("MK20", rendered)
        self.assertIn("Contracts", rendered)


if __name__ == "__main__":
    unittest.main()
