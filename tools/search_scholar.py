from __future__ import annotations

from typing import List, Dict
import os

from config_manager import load_api_config, get_config


def search_scholar_pdfs(keywords: str, max_results: int = 10) -> List[Dict[str, str]]:
    """查找与关键词相关的论文并尽量返回可用的 PDF 链接。

    优先：Google Scholar（scholarly）→ 回退：通用 PDF 搜索（ddgs filetype:pdf）。
    返回字段：title, pdf_url(可能为空), page_url(可能为空), source
    """
    load_api_config()

    results: List[Dict[str, str]] = []

    # 1) 优先使用 scholarly（如可用）
    try:
        from scholarly import scholarly  # type: ignore
        import time

        print(f"正在搜索: {keywords}")
        search = scholarly.search_pubs(keywords)
        
        # 添加超时机制
        start_time = time.time()
        timeout = 30  # 30秒超时
        
        for _ in range(max_results):
            if time.time() - start_time > timeout:
                print("Google Scholar搜索超时，切换到备用搜索")
                break
                
            try:
                pub = next(search)
            except StopIteration:
                break
            except Exception as e:
                print(f"Google Scholar搜索出错: {e}")
                break
                
            try:
                filled = scholarly.fill(pub)
            except Exception:
                filled = pub

            bib = filled.get("bib", {}) if isinstance(filled, dict) else {}
            title = bib.get("title") or bib.get("pub_title") or ""
            pdf_url = filled.get("eprint_url") if isinstance(filled, dict) else None
            page_url = filled.get("pub_url") if isinstance(filled, dict) else None

            entry = {
                "title": title or "",
                "pdf_url": pdf_url or "",
                "page_url": page_url or "",
                "source": "Google Scholar",
            }
            results.append(entry)

            if len(results) >= max_results:
                break
    except Exception as e:
        print(f"Google Scholar不可用: {e}")
        # scholarly 不可用或被风控，回退到 ddgs
        pass

    # 2) 回退：使用 ddgs 搜索 PDF 链接
    if len(results) < max_results:
        try:
            from ddgs import DDGS  # type: ignore

            proxy = (
                get_config("PROXY_URL")
                or os.getenv("DDGS_PROXY")
                or os.getenv("HTTPS_PROXY")
                or os.getenv("HTTP_PROXY")
            )

            print(f"使用DuckDuckGo搜索PDF: {keywords}")
            q = f"{keywords} filetype:pdf"
            seen_links: set[str] = set()
            
            # 添加超时机制
            start_time = time.time()
            timeout = 20  # 20秒超时
            
            with DDGS(proxy=proxy, timeout=10, verify=True) as ddgs:
                for item in ddgs.text(q, max_results=max_results * 3, backend="auto"):
                    if time.time() - start_time > timeout:
                        print("DuckDuckGo搜索超时")
                        break
                        
                    href = (item.get("href") or item.get("url") or item.get("content") or "").strip()
                    title = (item.get("title") or "").strip()
                    if not href:
                        continue
                    lower = href.lower()
                    if not (lower.endswith(".pdf") or "pdf" in lower):
                        # 不是明显的 PDF 链接，跳过，避免误报
                        continue
                    if href in seen_links:
                        continue
                    seen_links.add(href)
                    results.append({
                        "title": title,
                        "pdf_url": href,
                        "page_url": "",
                        "source": "web-pdf",
                    })
                    if len(results) >= max_results:
                        break
        except Exception as e:
            print(f"DuckDuckGo搜索出错: {e}")
            pass

    return results[:max_results]

