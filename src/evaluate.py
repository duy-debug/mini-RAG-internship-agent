"""Đánh giá chất lượng retrieval và câu trả lời trên tập dữ liệu JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from .agent import RAGAgent


def keyword_coverage(answer: str, keywords: list[str]) -> float:
    # Tính tỉ lệ keywords có trong answer (dùng cho evaluate)
    lowered = answer.lower()
    if not keywords:
        return 1.0
    hits = sum(1 for keyword in keywords if keyword.lower() in lowered)
    return hits / len(keywords)


def evaluate(
    dataset_path: Path,
    agent: RAGAgent,
    *,
    offline: bool,
) -> tuple[list[dict], dict]:
    # Chạy agent trên toàn bộ dataset và trả về rows + summary
    rows: list[dict] = []  # Tích lũy kết quả từng case
    with dataset_path.open("r", encoding="utf-8") as handle:
        cases = [json.loads(line) for line in handle if line.strip()]  # Đọc dataset từ JSONL

    for case in cases:  # Duyệt từng câu hỏi trong dataset để đánh giá
        result = agent.answer(
            case["question"],
            verify_level=case.get("verify_level", "auto"),
            offline=offline,
        )
        retrieved_docs = {source["filename"] for source in result.sources}  # Tên file đã retrieve
        coverage = keyword_coverage(result.answer, case.get("expected_keywords", []))  # Keyword overlap
        retrieval_hit = case["expected_doc"] in retrieved_docs  # File đúng có trong top-k không
        citation_validity = (  # Tất cả citation hợp lệ và có ít nhất một citation
            len(result.verification["invalid_citations"]) == 0
            and bool(result.verification["valid_citations"])
        )

        rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "retrieval_hit": retrieval_hit,
                "keyword_coverage": round(coverage, 3),
                "citation_validity": citation_validity,
                "verification_passed": result.verification["passed"],
                "verify_level": result.verify_level,
                "answer": result.answer,
            }
        )

    summary = {  # Tổng hợp số liệu đánh giá toàn bộ dataset
        "cases": len(rows),
        "retrieval_hit_at_k": round(mean(row["retrieval_hit"] for row in rows), 3),
        "mean_keyword_coverage": round(mean(row["keyword_coverage"] for row in rows), 3),
        "citation_validity_rate": round(mean(row["citation_validity"] for row in rows), 3),
        "verification_pass_rate": round(
            mean(row["verification_passed"] for row in rows), 3
        ),
    }
    return rows, summary


def render_markdown(rows: list[dict], summary: dict) -> str:
    # Render kết quả evaluate dưới dạng Markdown
    lines = [
        "# Mini-RAG Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Cases: {summary['cases']}",
        f"- Retrieval hit@k: {summary['retrieval_hit_at_k']:.1%}",
        f"- Mean keyword coverage: {summary['mean_keyword_coverage']:.1%}",
        f"- Citation validity: {summary['citation_validity_rate']:.1%}",
        f"- Verification pass rate: {summary['verification_pass_rate']:.1%}",
        "",
        "## Cases",
        "",
    ]
    for row in rows:  # Duyệt từng kết quả để render thành dòng Markdown
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Question: {row['question']}",
                f"- Verify level: {row['verify_level']}",
                f"- Retrieval hit: {row['retrieval_hit']}",
                f"- Keyword coverage: {row['keyword_coverage']:.1%}",
                f"- Citation validity: {row['citation_validity']}",
                f"- Verification passed: {row['verification_passed']}",
                f"- Answer: {row['answer']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    # CLI entry point cho evaluation script
    parser = argparse.ArgumentParser(description="Evaluate mini-RAG")
    parser.add_argument("--dataset", default="data/eval/questions.jsonl")
    parser.add_argument("--docs", default="data/docs")
    parser.add_argument("--skill", default="skills/rag-answer/SKILL.md")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    agent = RAGAgent(args.docs, args.skill)
    rows, summary = evaluate(
        Path(args.dataset),
        agent,
        offline=args.offline,
    )
    report = render_markdown(rows, summary)
    print(report)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
