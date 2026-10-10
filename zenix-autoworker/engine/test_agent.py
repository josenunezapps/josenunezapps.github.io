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

    def test_free_model_used_when_variable_empty(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"test-dummy","AUTO_WORKER_MODEL":""}):
            with patch.object(agent,"api",return_value={"choices":[{"message":{"content":'{"summary":"ok","files":[]}'}}]}) as mocked:
                result=agent.model({"title":"QA","body":"Test"},"")
                self.assertEqual(result["summary"],"ok")
                self.assertEqual(mocked.call_args.args[2]["model"],"poolside/laguna-s-2.1:free")

    def test_tool_call_parses_structured_solution(self):
        tool_response={"choices":[{"message":{"content":"",
            "tool_calls":[{"function":{"name":"submit_solution",
                "arguments":'{"summary":"ok","files":[{"path":"sample.py","content":"print(1)"}]}'}}]}}]}
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"test-dummy","AUTO_WORKER_MODEL":""}):
            with patch.object(agent,"api",return_value=tool_response):
                result=agent.model({"title":"QA","body":"Test"},"")
                self.assertEqual(result["files"][0]["path"],"sample.py")

    def test_model_empty_reply_is_explicit_error(self):
        response={"model":"poolside/laguna-s-2.1:free",
            "choices":[{"finish_reason":"length","message":{"content":""}}]}
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"test-dummy","AUTO_WORKER_MODEL":""}):
            with patch.object(agent,"api",return_value=response):
                with self.assertRaisesRegex(RuntimeError,"contenido vacio"):
                    agent.model({"title":"QA","body":"Test"},"")

    def test_paid_model_rejected(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"test-dummy","AUTO_WORKER_MODEL":"openai/gpt-4"}):
            with self.assertRaises(ValueError):
                agent.model({"title":"QA","body":"Test"},"")

    def test_money_signal_not_equivalent_to_verified_payment(self):
        self.assertEqual(agent.MONEY.findall("Bounty $200; payment not guaranteed"),["$200"])
        self.assertIsNone(agent.ISSUE.fullmatch("https://github.com/owner/repo"))

if __name__=="__main__":unittest.main()
