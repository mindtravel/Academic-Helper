"""
最简单的 DeepSeek 工具调用示例：

- 通过 DeepSeek 的 OpenAI 兼容接口启用工具调用（function calling）
- 定义一个 "search_web" 工具，实时返回搜索链接
- 自动读取 .api_config 中的 API Key 与代理（见 config_manager）

运行：
  python deepseek_tool_mcp_min.py "给我找3个关于强化学习入门的链接"
"""

from __future__ import annotations

import json
import sys, os

import openai

from config_manager import load_api_config, get_config

from tools.search_web import search_web
from tools.text_from_url import text_from_url
from tools.zotero_integration import save_papers_to_zotero, ZoteroIntegration
from tools.search_arxiv import search_arxiv
from tools.search_scholar import search_scholar_pdfs
from tools.pdf_downloader import download_pdfs
from tools.markdown_notes import write_markdown_note
from tools.pdf_reader import read_pdf

from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory



def run_with_langchain(query: str) -> None:
    """使用 LangChain 改写的主要 LLM 工具调用循环（最多10轮，可提前退出）。"""
    # 加载配置并适配 DeepSeek 的 OpenAI 兼容接口
    load_api_config()
    deepseek_key = get_config("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("请先在 .api_config 中配置 DEEPSEEK_API_KEY")
        return
    os.environ["OPENAI_API_KEY"] = deepseek_key
    os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com/v1"

    llm = ChatOpenAI(model="deepseek-chat", temperature=0)

    # 将现有函数包装为 LangChain 工具（只暴露常用参数，避免模型误填冗余参数）
    def _search_web_min(query: str, max_results: int = 10) -> list[str]:
        return search_web(query=query, max_results=max_results)

    def _text_from_url_min(url: str, timeout: int = 15, max_chars: int = 4000) -> dict:
        return text_from_url(url=url, timeout=timeout, max_chars=max_chars)

    def _search_arxiv_min(keywords: str, max_results: int = 10, year_from: int | None = None) -> list[dict]:
        return search_arxiv(keywords=keywords, max_results=max_results, year_from=year_from)

    def _search_scholar_min(keywords: str, max_results: int = 10) -> list[dict]:
        return search_scholar_pdfs(keywords=keywords, max_results=max_results)

    def _zotero_router(
        action: str,
        collection_name: str | None = None,
        parent_collection: str | None = None,
        collection_key: str | None = None,
        item_key: str | None = None,
        paper: dict | None = None,
        papers: list[dict] | None = None,
    ) -> dict:
        api_key = get_config("ZOTERO_API_KEY")
        user_id = get_config("ZOTERO_USER_ID")
        if not api_key or not user_id:
            return {"ok": False, "error": "zotero_not_configured"}
        z = ZoteroIntegration(api_key, user_id)
        # if action == "save_papers":
        #     return {"ok": bool(save_papers_to_zotero(papers or [], collection_name=collection_name))}
        if action == "create_collection":
            key = z.create_collection(collection_name or "", parent_collection=parent_collection)
            return {"ok": bool(key), "collection_key": key or ""}
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
        if action == "move_item":
            ok = z.move_item_to_collection(item_key or "", collection_key or "")
            return {"ok": bool(ok)}
        if action == "list_collections":
            return {"ok": True, "collections": z.get_collections()}
        return {"ok": False, "error": "unknown_action"}

    def _pdf_downloader(papers: list[dict], download_dir: str) -> dict:
        return download_pdfs(papers, download_dir)

    def _write_note(title: str, content: str, folder: str | None = None, append: bool = True) -> dict:
        return write_markdown_note(title=title, content=content, folder=folder, append=append)

    def _read_pdf(file_path: str, max_chars: int = 8000, password: str | None = None) -> dict:
        return read_pdf(file_path=file_path, max_chars=max_chars, password=password)

    tools = [
        StructuredTool.from_function(_search_web_min, name="search_web", description='''
            使用 DuckDuckGo 实时检索，返回前N条网页链接。"
        '''),
        StructuredTool.from_function(_text_from_url_min, name="text_from_url", description='''
            抓取URL网页并返回标题与正文文本（最多max_chars字符）。
        '''),
        StructuredTool.from_function(_search_scholar_min, name="search_scholar", description='''
            Google Scholar & Web PDF 搜索。你需要提供关键词，尽量返回包含 PDF 链接的条目。
            在这些有PDF链接的条目中，尽量选择论文最终发表的会议/期刊对应的文献库，而不是arxiv等预印本。
        '''),
        StructuredTool.from_function(_search_arxiv_min, name="search_arxiv", description='''
            arxiv搜索接口。如果你需要寻找一篇论文的URL和pdf等，但是其他正式的途径中都没有搜到论文的url，可以调用这个工具来搜索arxiv上的相关论文。
            你需要提供关键词，返回的结果会包含标题、作者、出版日期、摘要和PDF链接等信息。
        '''),
        StructuredTool.from_function(_zotero_router, name="zotero", description='''
            Zotero 聚合工具，通过 action 路由不同操作
            (create_collection：创建新文件夹，需要根据任务名称生成文件夹的名称
            /add_item：添加论文到Zotero的特定文件夹，需要提供论文的标题、作者、出版日期、摘要和PDF链接等信息
            /move_item：移动论文到Zotero的特定文件夹
            /list_collections：
            )
        '''),
        StructuredTool.from_function(_pdf_downloader, name="pdf_downloader", description='''
            批量下载论文PDF到指定目录（参数：papers[{title,pdf_url}], download_dir）
        '''),
        StructuredTool.from_function(_write_note, name="write_markdown_note", description='''
            记录 Markdown 笔记：将内容追加/写入到指定笔记目录（参数：title, content, folder?, append?）
        '''),
        StructuredTool.from_function(_read_pdf, name="read_pdf", description='''
            读取本地PDF文件并提取文本内容，用于分析PDF文档。返回提取的文本、页数等元数据。
            参数：file_path（PDF文件路径，如"./downloads/paper.pdf"）, max_chars（最大字符数，默认8000）, password（密码，可选）
            返回：{ok, text, meta:{pages}, error}
        '''),
    ]

    system_text = (
        "当你完成任务时，你需要最大限度地调用给定的工具吸收互联网上的信息作为严格的佐证，并且细致地辨别不合理的信息。"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_text),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    # executor = AgentExecutor(agent=agent, tools=tools, memory=memory, max_iterations=10, verbose=True)
    executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)

    # 首次运行
    try:
        result = executor.invoke({"input": query})
        print(result.get("output", ""))
    except KeyboardInterrupt:
        print("\n已中断。")
        return

    # 交互式继续：允许用户在任务结束后继续下达新指令，沿用上下文与工具
    while True:
        try:
            user_cmd = input("\n继续指令(回车结束)：").strip()
        except KeyboardInterrupt:
            print("\n已中断。")
            break
        if not user_cmd or user_cmd.lower() in {"exit", "quit", "q"}:
            break
        try:
            result = executor.invoke({"input": user_cmd})
            print(result.get("output", ""))
        except KeyboardInterrupt:
            print("\n已中断。")
            break


if __name__ == "__main__":
    # q = "给我找3个关于强化学习入门的链接"
    # q = "KV Cache的原理是什么？如何在推理时节省KV Cache，通过阅读相应的网页学习该领域的知识，系统地告诉我该领域的研究脉络和代表性论文的名字、年份、会议、和主要内容，将代表性论文保存到我的Zotero中。"
    # q = "KV Cache优化领域中的Group Query Attention是怎么工作的"
    # q = "帮我找一些关于KV Cache层间优化的论文，并保存到我的Zotero中"
    # q = "帮我找一些关于KV Cache层间优化的论文，并下载pdf文件"
    # q = "帮我找一些关于KV Cache优化的网页介绍，将内容整理成一份markdown笔记"
    # q = "帮我上网查找资料，形成一份北京有趣citywalk路线的笔记"
    # q = "阅读attention is all you need的论文原文并总结其内容"
    q = "我想去北京旅游，请帮我制定一个为期三天的旅游计划，并将其保存为markdown笔记"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    # run(q)
    run_with_langchain(q)

