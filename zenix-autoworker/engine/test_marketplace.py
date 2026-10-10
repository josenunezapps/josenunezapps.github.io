import tempfile,unittest,json
from pathlib import Path
from marketplace import normalize,snapshot
def response(*items):return [{"result":{"data":{"json":{"items":list(items)}}}}]
def bounty(amount=5000,url="https://github.com/acme/project/issues/7"):
    return {"id":"abc","task":{"url":url,"title":"Fix bug"},"org":{"handle":"acme","github_handle":"acme"},"reward":{"amount":amount}}
class MarketplaceTests(unittest.TestCase):
    def test_no_listing(self):self.assertEqual(normalize(response()),[])
    def test_price_is_listed_not_guaranteed(self):
        x=normalize(response(bounty()))[0]
        self.assertEqual(x["reward_usd_listed"],50)
        self.assertFalse(x["payment_verified"])
        self.assertTrue(x["sponsor_match"])
    def test_reject_bad_money_and_domains(self):
        self.assertEqual(normalize(response(bounty(0),bounty(400,"https://example.com"))),[])
    def test_deduplicate(self):self.assertEqual(len(normalize(response(bounty(),bounty()))),1)
    def test_unknown_schema(self):
        with self.assertRaises(ValueError):normalize({"items":[]})
    def test_provider_failure_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            def fail():raise OSError("service unavailable")
            v=snapshot(Path(d)/"data.json",fail)
            self.assertEqual(v["source_status"],"unavailable")
            self.assertIsNotNone(v["error"])
    def test_provider_confirmed_zero(self):
        with tempfile.TemporaryDirectory() as d:
            v=snapshot(Path(d)/"data.json",lambda:[])
            self.assertEqual(v["source_status"],"ok")
            self.assertEqual(v["listed_count"],0)
if __name__=="__main__":unittest.main()
