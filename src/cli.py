"""Giao diện dòng lệnh cho mini-RAG agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .agent import RAGAgent
from .llm_client import LLMError
from .security import SecurityError


def build_parser() -> argparse.ArgumentParser:
    # Xây dựng CLI parser với subcommand ask
    parser = argparse.ArgumentParser(description="Mini-RAG Internship Assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask", help="Đặt câu hỏi cho agent")
    ask.add_argument("question", help="Câu hỏi cần tra cứu")
    ask.add_argument("--docs", default="data/docs", help="Thư mục tài liệu")
    ask.add_argument(
        "--skill",
        default="skills/rag-answer/SKILL.md",
        help="Đường dẫn skill",
    )
    ask.add_argument("--top-k", type=int, default=4)
    ask.add_argument(
        "--verify",
        choices=["auto", "light", "heavy"],
        default="auto",
    )
    ask.add_argument("--offline", action="store_true")
    ask.add_argument("--json", action="store_true", dest="as_json")

    chat = subparsers.add_parser("chat", help="Hỏi đáp tương tác nhiều câu")
    chat.add_argument("--docs", default="data/docs", help="Thư mục tài liệu")
    chat.add_argument(
        "--skill",
        default="skills/rag-answer/SKILL.md",
        help="Đường dẫn skill",
    )
    chat.add_argument("--top-k", type=int, default=4)
    chat.add_argument(
        "--verify",
        choices=["auto", "light", "heavy"],
        default="auto",
    )
    chat.add_argument("--offline", action="store_true")
    return parser


def _print_result(result) -> None:
    print(result.answer)
    print("\n---")
    print(f"Mode: {result.mode}")
    print(f"Verify: {result.verify_level}")
    print(f"Passed: {result.verification['passed']}")
    print(f"Human review required: {result.human_review_required}")
    if result.verification["reasons"]:
        print("Reasons:")
        for reason in result.verification["reasons"]:
            print(f"- {reason}")


def _build_agent(args) -> RAGAgent:
    return RAGAgent(
        docs_dir=Path(args.docs),
        skill_path=Path(args.skill),
        top_k=args.top_k,
    )


def _cmd_ask(args) -> int:
    agent = _build_agent(args)
    try:
        result = agent.answer(
            args.question,
            verify_level=args.verify,
            offline=args.offline,
        )
    except (SecurityError, LLMError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    _print_result(result)
    return 0


def _cmd_chat(args) -> int:
    agent = _build_agent(args)
    print("Mini-RAG Chat (gõ 'exit' hoặc Ctrl+C để thoát)")
    print("-" * 40)
    while True:
        try:
            question = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in ("exit", "quit", "thoát"):
            break
        try:
            result = agent.answer(
                question,
                verify_level=args.verify,
                offline=args.offline,
            )
            _print_result(result)
        except (SecurityError, LLMError, FileNotFoundError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
        print()
    return 0


def main() -> int:
    # Điểm vào chính: phân tích tham số dòng lệnh và chạy agent
    args = build_parser().parse_args()

    if args.command == "ask":
        return _cmd_ask(args)
    if args.command == "chat":
        return _cmd_chat(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
