import requests
import feedparser
from typing import List, Dict, Optional


def search_arxiv(keywords: str, max_results: int = 10, year_from: Optional[int] = None) -> List[Dict]:
    """使用 arXiv API 搜索论文，返回结构化结果。

    注意：按原行为强制不使用代理（proxies={}）。
    """
    base_url = "http://export.arxiv.org/api/query?"
    query = f"search_query=all:{'+'.join(keywords.split())}&start=0&max_results={max_results}"
    url = base_url + query

    resp = requests.get(url, proxies={})
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)

    results: List[Dict] = []
    for entry in getattr(feed, 'entries', []) or []:
        published = entry.published.split('T')[0] if hasattr(entry, 'published') else ''
        try:
            year = int(published[:4]) if published else None
        except Exception:
            year = None
        if year_from and year and year < year_from:
            continue
        results.append({
            "title": getattr(entry, 'title', ''),
            "authors": [a.name for a in getattr(entry, 'authors', [])],
            "pdf_url": next((l.href for l in getattr(entry, 'links', []) if getattr(l, 'type', '') == "application/pdf"), None),
            "published": published,
            "summary": getattr(entry, 'summary', ''),
            "source": "arXiv",
        })
    return results

