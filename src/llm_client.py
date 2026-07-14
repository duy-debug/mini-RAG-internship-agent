"""Client Groq Responses API tối thiểu, chỉ dùng thư viện chuẩn Python."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"  # Base URL mặc định của Groq API
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"  # Model mặc định nếu không set GROQ_MODEL


class LLMError(RuntimeError):
    # Lỗi khi gọi model bên ngoài thất bại
    pass


def load_dotenv(path: str | Path = ".env") -> None:
    # Đọc cặp KEY=VALUE từ file mà không ghi đè biến môi trường có sẵn
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():  # Duyệt từng dòng trong file .env
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def is_configured() -> bool:
    # Kiểm tra đã có Groq API key trong biến môi trường hoặc file .env chưa
    load_dotenv()
    return bool(os.getenv("GROQ_API_KEY"))


def _extract_output_text(payload: dict[str, Any]) -> str:
    # Chỉ lấy câu trả lời cuối từ phản hồi Groq Responses API, bỏ qua reasoning

    parts: list[str] = []  # Tích lũy các output_text từ response

    for item in payload.get("output", []):
        # Bỏ qua item có type là reasoning
        if item.get("type") != "message":
            continue

        # Chỉ lấy message của assistant
        if item.get("role") != "assistant":
            continue

        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue

            # Chỉ lấy output_text, không lấy reasoning_text
            if content.get("type") != "output_text":
                continue

            text = content.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

    return "\n".join(parts).strip()


def generate(
    instructions: str,
    user_input: str,
    *,
    model: str | None = None,
    timeout_seconds: int = 60,
) -> str:
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")  # API key cho Groq
    if not api_key:
        raise LLMError("Thiếu biến môi trường GROQ_API_KEY.")

    selected_model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)  # Model sẽ dùng
    base_url = os.getenv("GROQ_BASE_URL", DEFAULT_GROQ_BASE_URL).rstrip("/")  # Base URL có thể tuỳ chỉnh

    body = json.dumps(  # Payload JSON gửi lên Groq Responses API
        {
            "model": selected_model,
            "instructions": instructions,
            "input": user_input,
        }
    ).encode("utf-8")

    request = Request(  # HTTP request tới Groq API
        f"{base_url}/responses",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "mini-rag-internship-agent/1.0",
        },
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMError(f"Groq API trả HTTP {exc.code}: {safe_body}") from exc
    except URLError as exc:
        raise LLMError(f"Không kết nối được tới Groq API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise LLMError("Groq API trả dữ liệu JSON không hợp lệ.") from exc

    text = _extract_output_text(payload)  # Trích xuất nội dung text từ response JSON
    if not text:
        raise LLMError("Không đọc được nội dung trả lời từ Groq Responses API.")
    return text
