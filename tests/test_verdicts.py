import unittest
from levelupdiag_core.verdicts import campaign_verdict

class VerdictTests(unittest.TestCase):
    def test_required_skip_blocks(self):
        rs=[{"level_id":"N1","verdict":"SKIP"}]
        self.assertEqual(campaign_verdict(rs,{"N1":True}),"BLOCKED")
    def test_optional_skip_is_not_blocking(self):
        rs=[{"level_id":"N1","verdict":"SKIP"}]
        self.assertEqual(campaign_verdict(rs,{"N1":False}),"PASS")
    def test_optional_fail_still_fails(self):
        rs=[{"level_id":"N1","verdict":"FAIL"}]
        self.assertEqual(campaign_verdict(rs,{"N1":False}),"FAIL")
