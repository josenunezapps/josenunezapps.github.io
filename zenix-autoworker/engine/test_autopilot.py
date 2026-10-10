import unittest
from autopilot import triage
ALGORA={"source_status":"ok","opportunities":[{"id":"algora:1","url":"https://github.com/x/y/issues/1","title":"Fix API","reward_usd_listed":100,"sponsor_match":True}]}
BOARD={"source_status":"ok","opportunities":[{"id":"bountyboard:1","source_listing":"https://www.bountyboard.work/bounties","title":"Python task","reward_listed":50,"currency":"USD","eligible_for_agent":True},{"id":"bountyboard:2","title":"Physical task","reward_listed":95,"currency":"EUR","eligible_for_agent":False}]}
class AutopilotTests(unittest.TestCase):
    def test_conservative_triage(self):
        results=triage(ALGORA,BOARD)
        self.assertEqual(len(results),2)
        self.assertFalse(results[0]["payment_verified"])
        self.assertNotIn("bountyboard:2",[x["id"] for x in results])
    def test_no_fabricated_jobs_if_source_fails(self):
        self.assertEqual(len(triage({"source_status":"unavailable","opportunities":ALGORA["opportunities"]},BOARD)),1)
    def test_empty_market(self):
        self.assertEqual(triage({"source_status":"ok","opportunities":[]},{"source_status":"ok","opportunities":[]}),[])
if __name__=="__main__":unittest.main()
