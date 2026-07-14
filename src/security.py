"""Cổng bảo mật: phát hiện secret, PII và các mẫu prompt injection."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


class SecurityError(ValueError):
    # Lỗi khi input không được phép gửi tới model bên ngoài
    pass


@dataclass(frozen=True)
class SecurityFinding:
    category: str  # "secret", "pii", "injection"
    label: str  # Nhãn cụ thể, vd "openai_like_key"


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (  # Mẫu phát hiện secret/key trong input
    ("openai_like_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("groq_api_key", re.compile(r"\bgsk_[A-Za-z0-9_-]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/.+=]{8,}"
        ),
    ),
)

PII_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (  # Mẫu phát hiện PII kèm replacement
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    (
        "phone",
        re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\d)"),
        "[REDACTED_PHONE]",
    ),
)

INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (  # Mẫu phát hiện prompt injection
    re.compile(r"(?i)\bignore (?:all |the )?(?:previous|prior) instructions\b"),
    re.compile(r"(?i)\breveal (?:the )?(?:system prompt|developer message|hidden prompt)\b"),
    re.compile(r"(?i)\bbỏ qua (?:mọi |tất cả )?(?:hướng dẫn|chỉ dẫn)"),
    re.compile(r"(?i)\btiết lộ (?:system prompt|prompt hệ thống|chỉ dẫn ẩn)"),
    re.compile(r"(?i)\bexfiltrat(?:e|ion)\b"),
)


def _find_labels(text: str, patterns: Iterable[tuple[str, re.Pattern[str]]]) -> list[str]:
    # Trả về danh sách nhãn của pattern khớp với text
    return [label for label, pattern in patterns if pattern.search(text)]


def contains_prompt_injection(text: str) -> bool:
    # Kiểm tra văn bản có chứa mẫu prompt injection hay không
    return any(pattern.search(text) for pattern in INJECTION_PATTERNS)


def inspect_user_input(text: str) -> tuple[str, list[SecurityFinding]]:
    # Từ chối nếu có secret/injection, che PII trước khi gửi đi
    if not isinstance(text, str) or not text.strip():
        raise SecurityError("Câu hỏi rỗng hoặc không hợp lệ.")

    secret_labels = _find_labels(text, SECRET_PATTERNS)  # Duyệt tất cả mẫu secret để tìm match
    if secret_labels:
        raise SecurityError(
            "Phát hiện dữ liệu có thể là secret. Hãy xóa hoặc thay bằng placeholder trước khi tiếp tục: "
            + ", ".join(secret_labels)
        )

    if contains_prompt_injection(text):
        raise SecurityError(
            "Câu hỏi chứa chỉ dẫn có dấu hiệu prompt injection nên không được gửi tới mô hình."
        )

    sanitized = text  # Bản sao sẽ được che PII
    findings: list[SecurityFinding] = []  # Tích lũy cảnh báo bảo mật
    for label, pattern, replacement in PII_PATTERNS:
        if pattern.search(sanitized):
            findings.append(SecurityFinding(category="pii", label=label))
            sanitized = pattern.sub(replacement, sanitized)

    return sanitized.strip(), findings


def sanitize_document_text(text: str) -> tuple[str, list[SecurityFinding]]:
    # Che secret và PII trong tài liệu trước khi đưa vào context của model
    sanitized = text  # Bản sao sẽ được che secret và PII
    findings: list[SecurityFinding] = []  # Tích lũy cảnh báo bảo mật

    for label, pattern in SECRET_PATTERNS:  # Duyệt từng mẫu secret để che
        if pattern.search(sanitized):
            findings.append(SecurityFinding(category="secret", label=label))
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

    for label, pattern, replacement in PII_PATTERNS:  # Duyệt từng mẫu PII để che
        if pattern.search(sanitized):
            findings.append(SecurityFinding(category="pii", label=label))
            sanitized = pattern.sub(replacement, sanitized)

    return sanitized, findings
