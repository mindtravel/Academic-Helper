from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional

from config_manager import load_api_config

try:
    # get_proxy_url 在扩展接口中提供；如不可用，则回退到环境变量
    from config_manager import get_proxy_url  # type: ignore
except Exception:  # pragma: no cover - 兼容旧实现
    get_proxy_url = None  # type: ignore


def text_from_url(url: str, timeout: int = 15, max_chars: int = 4000) -> Dict[str, str]:
    """抓取网页并提取标题与正文文本（返回真实数据，不伪造）。

    - 自动读取 .api_config 的 PROXY_URL（若可用）
    - 对于非文本内容，仅返回 content_type 与大小信息
    """
    load_api_config()

    proxy: Optional[str] = None
    if callable(get_proxy_url):  # 优先从 .api_config/环境变量读取统一代理
        proxy = get_proxy_url(None)

    proxies = {"http": proxy, "https": proxy} if proxy else None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout, proxies=proxies)
        status_ok = (200 <= resp.status_code < 300)
    except Exception as e:
        return {
            "url": url,
            "error": "request_failed",
            "message": str(e),
        }

    if not status_ok:
        return {
            "url": url,
            "error": "http_error",
            "status_code": resp.status_code,
            "reason": resp.reason,
        }

    content_type = (resp.headers.get("Content-Type") or "").lower()
    if ("text" in content_type) or ("html" in content_type) or (content_type == ""):
        resp.encoding = resp.apparent_encoding or resp.encoding
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""

        # 尝试常见主内容容器
        main = soup.select_one("article, main, #content, .content")
        text = (main.get_text(" ", strip=True) if main else soup.get_text(" ", strip=True))

        text = text[: max(0, int(max_chars))]
        return {
            "url": url,
            "title": title,
            "text": text,
        }

    # 非文本内容（如 PDF/图片等）返回元信息
    return {
        "url": url,
        "content_type": content_type,
        "size_bytes": str(len(resp.content)),
    }

