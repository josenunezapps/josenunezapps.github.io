import hashlib,tempfile,unittest
from pathlib import Path
from reviews import prepare,advance,read
URL="https://github.com/acme/repo/issues/42"
class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.f=Path(self.t.name)/"reviews.json"
        prepare(URL,"Fix a bug",path=self.f)
    def tearDown(self):self.t.cleanup()
    def change(self,action,actor="josenunezapps",**kw):return advance(URL,action,actor,path=self.f,**kw)
    def test_approval_requires_owner(self):
        with self.assertRaises(PermissionError):self.change("approve_apply","another-user")
        self.assertEqual(self.change("approve_apply")["status"],"approved_to_apply")
    def test_no_skipping(self):
        with self.assertRaises(ValueError):self.change("mark_applied",evidence=URL)
    def test_complete_gate(self):
        self.change("approve_apply");self.change("mark_applied",evidence=URL)
        with self.assertRaises(ValueError):self.change("approve_delivery")
        digest=hashlib.sha256(b"reviewed code").hexdigest()
        self.change("ready_delivery",sha256=digest);self.change("approve_delivery")
        x=self.change("mark_delivered",evidence=URL)
        self.assertEqual(x["status"],"delivered")
        self.assertEqual(x["delivery_sha256"],digest)
        self.assertEqual(len(x["history"]),6)
    def test_no_nonissue_urls(self):
        with self.assertRaises(ValueError):prepare("https://other.example/job","X",path=self.f)
    def test_duplicate_prepare_does_not_erase_state(self):
        self.change("approve_apply")
        self.assertEqual(prepare(URL,"New name",path=self.f)["status"],"approved_to_apply")
if __name__=="__main__":unittest.main()
