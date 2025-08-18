from config_manager import get_config
from langchain.tools import StructuredTool
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
# 将现有函数包装为 LangChain 工具（只暴露常用参数，避免模型误填冗余参数）

task_folder = ""


# search_web = TavilySearch(max_results=10)

@tool
def search_web_tool(query: str, max_results: int = 10) -> list[str]:
    """
    使用 DuckDuckGo 实时检索，返回前N条网页链接 
    
    Args:
        query: 搜索关键词
        max_results: （可选）最大搜索结果数量
    """
    from .search_web import search_web
    return search_web(query=query, max_results=max_results)

@tool
def text_from_url_tool(url: str, timeout: int = 15, max_chars: int = 4000) -> dict:
    """
    抓取URL网页并返回标题与正文文本（最多max_chars字符）
    """
    from .text_from_url import text_from_url
    return text_from_url(url=url, timeout=timeout, max_chars=max_chars)

@tool
def search_arxiv_tool(keywords: str, max_results: int = 10, year_from: int | None = None) -> list[dict]:
    """
    arxiv搜索接口。如果你需要寻找一篇论文的URL和pdf等，但是其他正式的途径中都没有搜到论文的url，可以调用这个工具来搜索arxiv上的相关论文。
    你需要提供关键词，返回的结果会包含标题、作者、出版日期、摘要和PDF链接等信息。
    """
    from .search_arxiv import search_arxiv
    return search_arxiv(keywords=keywords, max_results=max_results, year_from=year_from)

@tool
def search_scholar_tool(keywords: str, max_results: int = 10) -> list[dict]:
    '''
    Google Scholar & Web PDF 搜索。你需要提供关键词，尽量返回包含 PDF 链接的条目
    在这些有PDF链接的条目中，尽量选择论文最终发表的会议/期刊对应的文献库，而不是arxiv等预印本。
    '''
    from .search_scholar import search_scholar_pdfs
    return search_scholar_pdfs(keywords=keywords, max_results=max_results)

@tool
def zotero_router(
    action: str,
    collection_name: str | None = None,
    parent_collection: str | None = None,
    collection_key: str | None = None,
    item_key: str | None = None,
    paper: dict | None = None,
    papers: list[dict] | None = None,
) -> dict:
    '''
    Zotero 聚合工具路由，通过 action 路由不同操作
    (create_collection：创建新文件夹，需要根据任务名称生成文件夹的名称
    /add_item：添加论文到Zotero的特定文件夹，需要提供论文的标题、作者、出版日期、摘要和PDF链接等信息
    /move_item：移动论文到Zotero的特定文件夹
    /list_collections：
    )
    '''
    # 初始化zotero API
    from .zotero_integration import save_papers_to_zotero, ZoteroIntegration

    api_key = get_config("ZOTERO_API_KEY")
    user_id = get_config("ZOTERO_USER_ID")
    if not api_key or not user_id:
        return {"ok": False, "error": "zotero_not_configured"}
    z = ZoteroIntegration(api_key, user_id)
    
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

@tool
def pdf_downloader_tool(papers: list[dict], folder: str = "downloads") -> dict:
    '''
    批量下载论文PDF到指定目录
    
    Args:
        papers: 需要下载的论文的列表，内容为[{title,pdf_url}]
        folder: 下载目录，默认使用任务文件夹
    '''
    from .pdf_downloader import download_pdfs
    import tools.tools_definitions
    return download_pdfs(papers, f"{tools.tools_definitions.task_folder}/{folder}")

@tool
def markdown_note_tool(title: str, content: str, folder: str = "reports", append: bool = True) -> dict:
    '''
    记录 Markdown 笔记，在指定笔记目录中添加或删除内容
    
    Args:
        title: 笔记的标题
        content: 笔记的内容
        folder: （可选）保存笔记的文件夹
        append: （可选）是否以追加方式记录笔记
    '''
    from .markdown_notes import write_markdown_note
    import tools.tools_definitions
    return write_markdown_note(title=title, content=content, folder=f"{tools.tools_definitions.task_folder}/{folder}", append=append)

@tool
def read_pdf_tool(file_path: str, max_chars: int = 8000, password: str | None = None) -> dict:
    """pdf阅读工具"""
    from .pdf_reader import read_pdf
    return read_pdf(file_path=file_path, max_chars=max_chars, password=password)

tools_api = [
    search_web_tool,
    text_from_url_tool,
    search_scholar_tool,
    search_arxiv_tool,
    zotero_router,
    pdf_downloader_tool,
    markdown_note_tool,
    read_pdf_tool
]