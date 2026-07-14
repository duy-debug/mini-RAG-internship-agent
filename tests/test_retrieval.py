import unittest
from pathlib import Path

from src.retrieval_tool import retrieve


ROOT = Path(__file__).resolve().parents[1]


class RetrievalTests(unittest.TestCase):
    def test_security_question_retrieves_security_doc(self):
        chunks = retrieve(
            "Có được commit API key lên Git không?",
            ROOT / "data/docs",
            top_k=3,
        )
        self.assertEqual(chunks[0].filename, "security_policy.md")

    def test_branch_question_retrieves_coding_doc(self):
        chunks = retrieve(
            "Branch tính năng mới đặt tên thế nào?",
            ROOT / "data/docs",
            top_k=3,
        )
        self.assertEqual(chunks[0].filename, "coding_rules.md")


if __name__ == "__main__":
    unittest.main()
