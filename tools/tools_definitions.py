from .search_web import search_web
from .text_from_url import text_from_url
from .zotero_integration import save_papers_to_zotero, ZoteroIntegration
from .search_arxiv import search_arxiv
from .search_scholar import search_scholar_pdfs
from .pdf_downloader import download_pdfs
from .markdown_notes import write_markdown_note
from .pdf_reader import read_pdf

from config_manager import get_config

# 将现有函数包装为 LangChain 工具（只暴露常用参数，避免模型误填冗余参数）

task_folder = ""
def search_web_min(query: str, max_results: int = 10) -> list[str]:
    """网页搜索工具"""
    return search_web(query=query, max_results=max_results)

def text_from_url_min(url: str, timeout: int = 15, max_chars: int = 4000) -> dict:
    """网页文本提取工具"""
    return text_from_url(url=url, timeout=timeout, max_chars=max_chars)

def search_arxiv_min(keywords: str, max_results: int = 10, year_from: int | None = None) -> list[dict]:
    """arxiv搜索工具"""
    return search_arxiv(keywords=keywords, max_results=max_results, year_from=year_from)

def search_scholar_min(keywords: str, max_results: int = 10) -> list[dict]:
    """谷歌学术搜索工具"""
    return search_scholar_pdfs(keywords=keywords, max_results=max_results)

def zotero_router(
    action: str,
    collection_name: str | None = None,
    parent_collection: str | None = None,
    collection_key: str | None = None,
    item_key: str | None = None,
    paper: dict | None = None,
    papers: list[dict] | None = None,
) -> dict:
    """zotero工具路由"""
    # 初始化zotero API
    api_key = get_config("ZOTERO_API_KEY")
    user_id = get_config("ZOTERO_USER_ID")
    if not api_key or not user_id:
        return {"ok": False, "error": "zotero_not_configured"}
    z = ZoteroIntegration(api_key, user_id)
    # if action == "save_papers":
    #     return {"ok": bool(save_papers_to_zotero(papers or [], collection_name=collection_name))}
    
    # 创建论文集
    if action == "create_collection":
        key = z.create_collection(collection_name or "", parent_collection=parent_collection)
        return {"ok": bool(key), "collection_key": key or ""}
    
    # 向论文集中添加论文
    if action == "add_item":
        # 解析目标集合
        if not collection_key and collection_name:
            collection_key = z.find_or_create_collection(collection_name)
        if not collection_key:
            return {"ok": False, "error": "missing_collection_key"}

        # 支持单条或批量
        if papers and isinstance(papers, list):
            added = 0
            total = len(papers)
            for p in papers:
                if z.add_item(p or {}, collection_key=collection_key):
                    added += 1
            return {"ok": added > 0, "added": added, "total": total}
        else:
            ok = z.add_item(paper or {}, collection_key=collection_key)
            return {"ok": bool(ok), "added": 1 if ok else 0, "total": 1}
        
    # 移动论文到论文集
    if action == "move_item":
        ok = z.move_item_to_collection(item_key or "", collection_key or "")
        return {"ok": bool(ok)}
    
    # 列出zotero中的论文集
    if action == "list_collections":
        return {"ok": True, "collections": z.get_collections()}
    return {"ok": False, "error": "unknown_action"}

def pdf_downloader(papers: list[dict], folder: str = "downloads") -> dict:
    """
    pdf 下载工具
    folder: 下载目录，默认使用任务文件夹
    """    

    return download_pdfs(papers, f"{task_folder}/{folder}")

def markdown_note_min(title: str, content: str, folder: str = "reports", append: bool = True) -> dict:
    """
    笔记记录工具
    folder: 笔记文件夹，默认使用任务文件夹
    """
    return write_markdown_note(title=title, content=content, folder=f"{task_folder}/{folder}", append=append)

def read_pdf_min(file_path: str, max_chars: int = 8000, password: str | None = None) -> dict:
    """pdf阅读工具"""
    return read_pdf(file_path=file_path, max_chars=max_chars, password=password)
