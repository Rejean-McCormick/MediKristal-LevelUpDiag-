import sys, tempfile, unittest
from pathlib import Path
from levelupdiag_core.commands import run_command

class CommandTests(unittest.TestCase):
    def test_argument_array_no_shell(self):
        with tempfile.TemporaryDirectory() as d:
            r=run_command([sys.executable,"-c","print('ok')"],cwd=Path(d),timeout_seconds=10)
            self.assertEqual(r["exit_code"],0)
            self.assertIn("ok",r["stdout_tail"])
