from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, Optional

from config_manager import get_config, load_api_config


def _slugify(text: str) -> str:
    text = text.strip()
    # 替换非法文件名字符
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    # 合并空白
    text = re.sub(r"\s+", "_", text)
    return text[:120] or "note"


def write_markdown_note(
    title: str,
    content: str,
    folder: Optional[str] = None,
    append: bool = True,
) -> Dict[str, str]:
    """将内容以 Markdown 形式记录到本地文件。

    - title: 笔记标题（用于文件名与文档标题）
    - content: 笔记正文（Markdown）
    - folder: 目标文件夹，默认从 .api_config 的 NOTES_DIR 或 ./result/notes
    - append: 若存在同名文件是否追加；否则覆盖写入
    返回: { ok, path }
    """
    load_api_config()
    base_dir = folder or get_config("NOTES_DIR", "./result/notes")
    os.makedirs(base_dir, exist_ok=True)

    filename = f"{_slugify(title)}.md"
    path = os.path.join(base_dir, filename)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"# {title}\n\n> Created: {now}\n\n"
    body = f"{content.strip()}\n"

    mode = "a" if append and os.path.exists(path) else "w"
    with open(path, mode, encoding="utf-8") as f:
        if mode == "w":
            f.write(header)
        else:
            # 追加时插入分隔与时间戳
            f.write("\n\n---\n\n")
            f.write(f"> Updated: {now}\n\n")
        f.write(body)

    return {"ok": True, "path": path}

