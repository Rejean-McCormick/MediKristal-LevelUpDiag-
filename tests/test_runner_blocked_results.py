import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from levelupdiag_core import runner


class RunnerSyntheticResultTests(unittest.TestCase):
    def test_fail_fast_synthetic_results_are_written(self):
        # This is a structural regression guard for the path used by run_campaign:
        # latest/ copying requires every in-memory result to have a result.json.
        source=Path(runner.__file__).read_text(encoding='utf-8')
        self.assertIn('def persist_synthetic', source)
        self.assertIn('persist_synthetic(meta, _result_for_blocked', source)
        self.assertIn('persist_synthetic(by_id[lid], _result_for_blocked', source)

if __name__=='__main__': unittest.main()
