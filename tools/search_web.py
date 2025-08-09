from __future__ import annotations

import os
from typing import List, Optional

from ddgs import DDGS
from config_manager import load_api_config, get_config


def search_web(query: str, max_results: int = 5, region: str = "us-en", backend: str = "auto", timeout: int = 15, verify: bool = True) -> List[str]:
    """使用 DuckDuckGo 元搜索实时检索并返回链接列表。"""
    load_api_config()
    proxy = (
        get_config("PROXY_URL")
        or os.getenv("DDGS_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )

    links: List[str] = []
    seen: set[str] = set()

    with DDGS(proxy=proxy, timeout=timeout, verify=verify) as ddgs:
        try:
            results = ddgs.text(
                query=query,
                region=region,
                safesearch="off",
                max_results=max_results,
                backend=backend,
            )
        except Exception:
            results = []

    for item in results or []:
        href = item.get("href") or item.get("url") or item.get("content")
        if isinstance(href, str) and href and href not in seen:
            seen.add(href)
            links.append(href)
            if len(links) >= max_results:
                break
    return links

