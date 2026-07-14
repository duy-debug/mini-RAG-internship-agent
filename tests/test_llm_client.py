import json
import os
import unittest
from unittest.mock import patch

from src.llm_client import generate


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            {
                "output": [
                    {"content": [{"type": "output_text", "text": "Kết quả Groq"}]}
                ]
            }
        ).encode("utf-8")


class LLMClientTests(unittest.TestCase):
    @patch("src.llm_client.urlopen")
    def test_uses_groq_responses_endpoint(self, mocked_urlopen):
        mocked_urlopen.return_value = _FakeResponse()
        env = {
            "GROQ_API_KEY": "gsk_test_key_not_real_123456",
            "GROQ_MODEL": "openai/gpt-oss-20b",
        }
        with patch.dict(os.environ, env, clear=False):
            result = generate("system", "question")

        self.assertEqual(result, "Kết quả Groq")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://api.groq.com/openai/v1/responses",
        )
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "openai/gpt-oss-20b")


if __name__ == "__main__":
    unittest.main()
