"""Công cụ truy xuất nội bộ nhỏ, dùng TF-IDF từ thư viện chuẩn Python."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
from collections import Counter
from typing import Iterable

from .security import contains_prompt_injection, sanitize_document_text


TOKEN_RE = re.compile(r"[A-Za-zÀ-ỹ0-9_./:-]+", re.UNICODE)  # Regex tách token tiếng Việt có dấu


@dataclass(frozen=True)
class Chunk:
    chunk_id: str  # ID dạng filename#cN
    filename: str  # Tên file gốc
    text: str  # Nội dung văn bản
    score: float = 0.0  # Điểm TF-IDF cosine với câu hỏi


def tokenize(text: str) -> list[str]:
    # Tách text thành list token chữ thường
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _split_paragraphs(text: str) -> list[str]:
    # Tách văn bản thành các đoạn (paragraph) dựa trên dòng trống
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return paragraphs


def chunk_document(filename: str, text: str, max_chars: int = 900) -> list[Chunk]:
    # Chia nhỏ tài liệu theo section ##, nếu section dài quá thì cắt tiếp theo kích thước
    raw_sections = [
        section.strip()
        for section in re.split(r"(?m)(?=^##\s+)", text)
        if section.strip()
    ]
    chunks: list[Chunk] = []

    # Bỏ qua section chỉ có tiêu đề H1, không chứa nội dung trả lời
    if raw_sections and all(
        line.startswith("#") or not line.strip()
        for line in raw_sections[0].splitlines()
    ):
        raw_sections = raw_sections[1:]

    for section in raw_sections:  # Duyệt từng section để chunk
        if len(section) <= max_chars:
            if not contains_prompt_injection(section):
                chunk_id = f"{filename}#c{len(chunks) + 1}"
                chunks.append(Chunk(chunk_id=chunk_id, filename=filename, text=section))
            continue

        paragraphs = _split_paragraphs(section)
        current: list[str] = []
        current_len = 0

        def flush() -> None:
            nonlocal current, current_len
            if current:
                chunk_text = "\n\n".join(current).strip()
                if chunk_text and not contains_prompt_injection(chunk_text):
                    chunk_id = f"{filename}#c{len(chunks) + 1}"
                    chunks.append(
                        Chunk(chunk_id=chunk_id, filename=filename, text=chunk_text)
                    )
                current = []
                current_len = 0

        for paragraph in paragraphs:  # Duyệt từng đoạn văn để gộp thành chunk
            if len(paragraph) > max_chars:
                flush()
                for offset in range(0, len(paragraph), max_chars):  # Cắt paragraph quá dài thành nhiều chunk
                    piece = paragraph[offset : offset + max_chars].strip()
                    if piece and not contains_prompt_injection(piece):
                        chunk_id = f"{filename}#c{len(chunks) + 1}"
                        chunks.append(
                            Chunk(chunk_id=chunk_id, filename=filename, text=piece)
                        )
                continue

            extra = len(paragraph) + (2 if current else 0)
            if current and current_len + extra > max_chars:
                flush()
            current.append(paragraph)
            current_len += extra

        flush()

    return chunks


def load_chunks(docs_dir: str | Path) -> list[Chunk]:
    # Đọc tất cả file .md/.txt trong thư mục, sanitize và chunk
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục tài liệu: {docs_path}")

    chunks: list[Chunk] = []
    for path in sorted(docs_path.iterdir()):  # Duyệt từng file trong thư mục tài liệu
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            raw = path.read_text(encoding="utf-8")
            sanitized, _ = sanitize_document_text(raw)
            chunks.extend(chunk_document(path.name, sanitized))

    if not chunks:
        raise ValueError("Không có chunk hợp lệ để truy xuất.")
    return chunks


def _idf(chunks: Iterable[Chunk]) -> dict[str, float]:
    # Tính IDF (Inverse Document Frequency) cho toàn bộ chunk collection
    chunks_list = list(chunks)
    doc_frequency: Counter[str] = Counter()
    for chunk in chunks_list:  # Duyệt từng chunk để đếm tần suất xuất hiện của token
        doc_frequency.update(set(tokenize(chunk.text)))

    total = len(chunks_list)
    return {
        token: math.log((1 + total) / (1 + frequency)) + 1.0
        for token, frequency in doc_frequency.items()
    }


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    # Tính TF-IDF vector từ tokens
    counts = Counter(tokens)
    total = max(len(tokens), 1)
    return {
        token: (count / total) * idf.get(token, 1.0)
        for token, count in counts.items()
    }


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    # Tính cosine similarity giữa hai TF-IDF vector
    common = set(a).intersection(b)
    numerator = sum(a[token] * b[token] for token in common)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return numerator / (norm_a * norm_b)


def retrieve(
    question: str,
    docs_dir: str | Path,
    top_k: int = 4,
) -> list[Chunk]:
    # Trả về top-k chunk cho câu hỏi
    if top_k < 1:
        raise ValueError("top_k phải lớn hơn hoặc bằng 1.")

    chunks = load_chunks(docs_dir)
    idf = _idf(chunks)
    query_vector = _vector(tokenize(question), idf)

    scored: list[Chunk] = []
    for chunk in chunks:  # Duyệt từng chunk để tính điểm cosine similarity
        score = _cosine(query_vector, _vector(tokenize(chunk.text), idf))
        scored.append(
            Chunk(
                chunk_id=chunk.chunk_id,
                filename=chunk.filename,
                text=chunk.text,
                score=score,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]
