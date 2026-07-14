import unittest

from src.retrieval_tool import Chunk
from src.verify_tool import verify_answer


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            Chunk(
                chunk_id="security_policy.md#c1",
                filename="security_policy.md",
                text="Không ghi API key trong source code. Secret phải đọc từ biến môi trường.",
                score=1.0,
            )
        ]

    def test_valid_grounded_answer_passes(self):
        result = verify_answer(
            "Không ghi API key trong source code; hãy dùng biến môi trường. "
            "[security_policy.md#c1]",
            self.sources,
            level="heavy",
        )
        self.assertTrue(result.passed)

    def test_fake_citation_fails(self):
        result = verify_answer(
            "Có thể commit key. [missing.md#c9]",
            self.sources,
            level="heavy",
        )
        self.assertFalse(result.passed)
        self.assertIn("missing.md#c9", result.invalid_citations)


if __name__ == "__main__":
    unittest.main()
