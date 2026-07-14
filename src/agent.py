"""Agent điều phối luồng: security -> retrieve -> answer -> verify -> repair."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Sequence

from .llm_client import LLMError, generate, is_configured
from .retrieval_tool import Chunk, retrieve
from .security import SecurityFinding, inspect_user_input
from .verify_tool import VerificationResult, verify_answer


RISK_KEYWORDS = {
    "api key", "access token", "password", "secret", "private key",
    "bảo mật", "phân quyền", "authorization", "authentication",
    "production", "migration", "thanh toán", "payment", "rotate", "revoke",
    "dữ liệu khách hàng", "dữ liệu cá nhân",
}


@dataclass(frozen=True)
class AgentResult:
    question: str
    sanitized_question: str
    answer: str
    mode: str
    verify_level: str
    sources: list[dict]
    verification: dict
    security_findings: list[dict]
    human_review_required: bool

    def to_dict(self) -> dict:
        return asdict(self)


def classify_verify_level(question: str) -> str:
    # Xác định verify_level dựa trên sự xuất hiện của risk keywords trong câu hỏi
    lowered = question.lower()
    return "heavy" if any(keyword in lowered for keyword in RISK_KEYWORDS) else "light"


def _format_sources(sources: Sequence[Chunk]) -> str:
    # Format danh sách chunk thành text SOURCE_ID + CONTENT để đưa vào prompt
    return "\n\n".join(
        f"SOURCE_ID: {source.chunk_id}\nCONTENT:\n{source.text}"
        for source in sources
    )


def _load_skill(skill_path: str | Path) -> str:
    # Đọc nội dung file skill Markdown
    path = Path(skill_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy skill: {path}")
    return path.read_text(encoding="utf-8")


def _token_overlap(question_tokens: set[str], sentence: str) -> int:
    # Đo độ overlap token giữa câu hỏi và một câu trong source
    sentence_tokens = set(
        re.findall(r"[A-Za-zÀ-ỹ0-9_./:-]+", sentence.lower())
    )
    return len(question_tokens.intersection(sentence_tokens))


def _offline_answer(question: str, sources: Sequence[Chunk]) -> str:
    # Phương án fallback trích xuất nội dung dùng cho demo và test
    # Chỉ lấy câu từ chunk đứng đầu, tránh ghép đoạn không liên quan
    if not sources or sources[0].score <= 0:
        return "Tài liệu hiện có chưa đủ để kết luận."

    source = sources[0]
    question_tokens = set(re.findall(r"[A-Za-zÀ-ỹ0-9_./:-]+", question.lower()))
    candidates = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", source.text)
        if sentence.strip() and not sentence.startswith("#")
    ]

    if not candidates:
        return "Tài liệu hiện có chưa đủ để kết luận."

    best_index = max(
        range(len(candidates)),
        key=lambda index: _token_overlap(question_tokens, candidates[index]),
    )
    selected_indices = [best_index]

    neighbours = [
        index for index in (best_index - 1, best_index + 1)
        if 0 <= index < len(candidates)
    ]
    if neighbours:
        selected_indices.append(
            max(neighbours, key=lambda index: _token_overlap(question_tokens, candidates[index]))
        )

    selected = [candidates[index] for index in sorted(set(selected_indices))]

    if not selected:
        return "Tài liệu hiện có chưa đủ để kết luận."
    return " ".join(f"{sentence} [{source.chunk_id}]" for sentence in selected)


def _build_prompt(
    question: str,
    sources: Sequence[Chunk],
    verify_level: str,
) -> str:
    # Xây dựng prompt hoàn chỉnh với question, sources và verify_level cho LLM
    return f"""QUESTION:
{question}

VERIFY_LEVEL:
{verify_level}

SOURCES:
{_format_sources(sources)}

TASK:
Trả lời QUESTION theo skill và chỉ sử dụng SOURCES.

Yêu cầu bắt buộc:
- Chỉ trả lời bằng tiếng Việt.
- Chỉ xuất câu trả lời cuối cùng.
- Không hiển thị phân tích, suy luận, bản nháp hoặc giải thích cách trả lời.
- Không dịch hoặc nhắc lại câu hỏi.
- Giữ nguyên chính xác các chuỗi code, tên branch và ký hiệu trong nguồn.
- Đặt citation ngay sau thông tin tương ứng.
- Nếu SOURCES không đủ, trả lời: "Tài liệu hiện có chưa đủ để kết luận."
"""


def _repair_prompt(
    question: str,
    answer: str,
    sources: Sequence[Chunk],
    verification: VerificationResult,
) -> str:
    # Xây dựng prompt yêu cầu LLM sửa lỗi từ verification
    issues = "; ".join(verification.reasons) or "Không rõ lỗi."
    return f"""QUESTION:
{question}

DRAFT_ANSWER:
{answer}

VERIFICATION_ISSUES:
{issues}

SOURCES:
{_format_sources(sources)}

TASK:
Viết lại câu trả lời để khắc phục toàn bộ lỗi verify.
Chỉ dùng SOURCES và chỉ dùng SOURCE_ID có thật làm citation.
Vì đây là verify nặng, thêm câu nhắc cần con người review trước khi áp dụng.
"""


class RAGAgent:
    # Điều phối luồng chính: security -> retrieve -> generate/offline -> verify -> repair

    def __init__(
        self,
        docs_dir: str | Path = "data/docs",
        skill_path: str | Path = "skills/rag-answer/SKILL.md",
        top_k: int = 4,
    ) -> None:
        self.docs_dir = Path(docs_dir)
        self.skill_path = Path(skill_path)
        self.top_k = top_k

    def answer(
        self,
        question: str,
        *,
        verify_level: str = "auto",
        offline: bool = False,
    ) -> AgentResult:
        # Pipeline: security -> retrieve -> answer -> verify -> repair
        sanitized_question, findings = inspect_user_input(question)

        selected_level = (
            classify_verify_level(sanitized_question)
            if verify_level == "auto"
            else verify_level
        )
        if selected_level not in {"light", "heavy"}:
            raise ValueError("verify_level phải là auto, light hoặc heavy.")

        sources = retrieve(sanitized_question, self.docs_dir, top_k=self.top_k)
        skill = _load_skill(self.skill_path)

        mode = "offline-extractive"
        if offline or not is_configured():
            answer = _offline_answer(sanitized_question, sources)
        else:
            answer = generate(skill, _build_prompt(sanitized_question, sources, selected_level))
            mode = "groq-responses"

        verification = verify_answer(answer, sources, selected_level)

        if (
            selected_level == "heavy"
            and not verification.passed
            and mode == "groq-responses"
        ):
            try:
                answer = generate(
                    skill,
                    _repair_prompt(
                        sanitized_question,
                        answer,
                        sources,
                        verification,
                    ),
                )
                verification = verify_answer(answer, sources, selected_level)
                mode = "groq-responses-repaired"
            except LLMError:
                # Giữ draft cũ và yêu cầu human review.
                pass

        human_review_required = selected_level == "heavy" or not verification.passed

        return AgentResult(
            question=question,
            sanitized_question=sanitized_question,
            answer=answer,
            mode=mode,
            verify_level=selected_level,
            sources=[
                {
                    "chunk_id": source.chunk_id,
                    "filename": source.filename,
                    "score": round(source.score, 4),
                }
                for source in sources  # Duyệt từng chunk để đóng gói vào dict kết quả
            ],
            verification=verification.to_dict(),
            security_findings=[
                {"category": finding.category, "label": finding.label}
                for finding in findings  # Duyệt từng cảnh báo bảo mật để đóng gói vào dict
            ],
            human_review_required=human_review_required,
        )
