from __future__ import annotations

from typing import Dict, Optional
import os

from pypdf import PdfReader


def read_pdf(file_path: str, max_chars: int = 80000, password: Optional[str] = None) -> Dict[str, str]:
    """读取本地 PDF，提取文本（前 max_chars 字符）。

    返回: { ok, meta:{pages}, text }
    """
    if not os.path.exists(file_path):
        return {"ok": "false", "error": "file_not_found", "path": file_path}

    try:
        reader = PdfReader(file_path)
        if reader.is_encrypted:
            try:
                reader.decrypt(password or "")
            except Exception:
                return {"ok": "false", "error": "decrypt_failed"}

        texts: list[str] = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        full_text = "\n".join(texts).strip()
        return {
            "ok": "true",
            "meta": {"pages": len(reader.pages)},
            "text": full_text[: max(0, int(max_chars))],
        }
    except Exception as e:
        return {"ok": "false", "error": str(e)}

