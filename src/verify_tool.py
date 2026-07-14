"""Công cụ xác minh tính hợp lệ của citation và mức độ groundedness."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Sequence

from .retrieval_tool import Chunk, tokenize


CITATION_RE = re.compile(r"\[([A-Za-z0-9_.-]+\.(?:md|txt)#c\d+)\]")

GROUNDEDNESS_THRESHOLD_LIGHT = 0.20
GROUNDEDNESS_THRESHOLD_HEAVY = 0.35

STOPWORDS = {
    "và", "là", "có", "được", "của", "cho", "trong", "khi", "một", "các",
    "the", "a", "an", "to", "of", "is", "are", "be", "with", "or",
}


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    level: str
    valid_citations: list[str]
    invalid_citations: list[str]
    groundedness: float
    checks: dict[str, bool]
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _content_tokens(text: str) -> set[str]:
    # Trả về set token có nghĩa (bỏ stopwords, bỏ token ngắn)
    return {
        token for token in tokenize(text)
        if len(token) > 2 and token not in STOPWORDS
    }


def verify_answer(
    answer: str,
    sources: Sequence[Chunk],
    level: str = "light",
) -> VerificationResult:
    if level not in {"light", "heavy"}:
        raise ValueError("level phải là 'light' hoặc 'heavy'.")

    source_by_id = {source.chunk_id: source for source in sources}
    citations = CITATION_RE.findall(answer)
    valid = sorted({citation for citation in citations if citation in source_by_id})
    invalid = sorted({citation for citation in citations if citation not in source_by_id})

    answer_without_citations = CITATION_RE.sub("", answer)
    answer_tokens = _content_tokens(answer_without_citations)

    cited_text = "\n".join(source_by_id[citation].text for citation in valid)
    source_tokens = _content_tokens(cited_text)
    overlap = len(answer_tokens.intersection(source_tokens))
    groundedness = overlap / max(len(answer_tokens), 1)

    uncertainty_answer = any(
        phrase in answer.lower()
        for phrase in (
            "chưa đủ để kết luận",
            "không tìm thấy",
            "chưa tìm thấy",
            "không có thông tin",
        )
    )

    min_groundedness = GROUNDEDNESS_THRESHOLD_LIGHT if level == "light" else GROUNDEDNESS_THRESHOLD_HEAVY
    checks = {
        "non_empty": bool(answer.strip()),
        "has_valid_citation_or_uncertainty": bool(valid) or uncertainty_answer,
        "no_invalid_citation": not invalid,
        "grounded_enough": groundedness >= min_groundedness or uncertainty_answer,
    }
    if level == "heavy":
        checks["heavy_requires_citation"] = bool(valid)

    reasons: list[str] = []
    if not checks["non_empty"]:
        reasons.append("Câu trả lời rỗng.")
    if not checks["has_valid_citation_or_uncertainty"]:
        reasons.append("Thiếu citation hợp lệ hoặc tuyên bố không đủ thông tin.")
    if not checks["no_invalid_citation"]:
        reasons.append("Có citation không nằm trong context.")
    if not checks["grounded_enough"]:
        reasons.append(
            f"Groundedness {groundedness:.2f} thấp hơn ngưỡng {min_groundedness:.2f}."
        )
    if level == "heavy" and not checks["heavy_requires_citation"]:
        reasons.append("Tác vụ verify nặng bắt buộc có citation hợp lệ.")

    return VerificationResult(
        passed=all(checks.values()),
        level=level,
        valid_citations=valid,
        invalid_citations=invalid,
        groundedness=round(groundedness, 3),
        checks=checks,
        reasons=reasons,
    )
