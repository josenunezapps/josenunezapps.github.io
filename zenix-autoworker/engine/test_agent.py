import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import agent

class AgentTests(unittest.TestCase):
    def test_issue_url_requires_github_issue(self):
        self.assertIsNotNone(agent.ISSUE.fullmatch("https://github.com/example/project/issues/123"))
        for url in ("https://evil.test/example/project/issues/123",
                    "https://github.com/example/project/pulls/9",
                    "https://github.com/example/project/issues/9;echo bad"):
            self.assertIsNone(agent.ISSUE.fullmatch(url))

    def test_path_traversal_is_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            for relative in ("../pass.py","/etc/passwd",".github/workflows/ci.py","src/run.sh"):
                with self.assertRaises(ValueError):
                    agent.safe(base,relative)
            self.assertEqual(agent.safe(base,"src/fix.py"),(base/"src/fix.py").resolve())

    def test_symlink_escape_is_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            base=Path(tmp)
            try:(base/"link").symlink_to(outside,target_is_directory=True)
            except (OSError,NotImplementedError):self.skipTest("No symlinks on environment")
            with self.assertRaises(ValueError):
                agent.safe(base,"link/outside.py")

    def test_no_ai_without_key(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):
                agent.model({"title":"Fix","body":"text"},"README context")

    def test_money_signal_not_equivalent_to_verified_payment(self):
        self.assertEqual(agent.MONEY.findall("Bounty $200; payment not guaranteed"),["$200"])
        self.assertIsNone(agent.ISSUE.fullmatch("https://github.com/owner/repo"))

if __name__=="__main__":unittest.main()
