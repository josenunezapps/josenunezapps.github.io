import unittest,tempfile
from pathlib import Path
from bountyboard import normalize,snapshot
def task(**kw):
    b={"id":"cmv1drg8n000n8gea8dhluykb","title":"Python parser","status":"OPEN",
       "reward":5000,"currency":"USD","allowAgents":True,"category":"Development & Tech",
       "_count":{"claims":0},"maxHunters":1}
    b.update(kw);return b
class BountyBoardTests(unittest.TestCase):
    def test_agent_eligible_when_open_and_unclaimed(self):
        b=normalize({"bounties":[task()]})[0]
        self.assertTrue(b["eligible_for_agent"])
        self.assertFalse(b["payment_verified"])
    def test_disallow_agent_when_poster_refuses(self):
        b=normalize({"bounties":[task(allowAgents=False)]})[0]
        self.assertFalse(b["eligible_for_agent"])
    def test_reject_physical_work(self):
        b=normalize({"bounties":[task(category="Data & Research")]})[0]
        self.assertFalse(b["eligible_for_agent"])
    def test_no_slots(self):
        b=normalize({"bounties":[task(_count={"claims":1})]})[0]
        self.assertFalse(b["eligible_for_agent"])
    def test_zero_money_not_candidate(self):
        self.assertEqual(normalize({"bounties":[task(reward=0)]}),[])
    def test_unknown_schema(self):
        with self.assertRaises(ValueError):normalize([])
    def test_provider_failure_reported(self):
        with tempfile.TemporaryDirectory() as d:
            def fail():raise OSError("outage")
            out=snapshot(Path(d)/"x.json",fail)
            self.assertEqual(out["source_status"],"unavailable")
if __name__=="__main__":unittest.main()
