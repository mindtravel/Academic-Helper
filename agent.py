"""
最简单的 DeepSeek 工具调用示例：

- 通过 DeepSeek 的 OpenAI 兼容接口启用工具调用（function calling）
- 定义一个 "search_web" 工具，实时返回搜索链接
- 自动读取 .api_config 中的 API Key 与代理（见 config_manager）

运行：
  python agent.py "给我找3个关于强化学习入门的链接"
"""

from __future__ import annotations

import json
import sys
import os

import openai

from config_manager import load_api_config, get_config
from user import setting

from tools.tools_definitions import (
    search_web_min,
    text_from_url_min,
    search_arxiv_min,
    search_scholar_min,
    zotero_router,
    pdf_downloader,
    markdown_note_min,
    read_pdf_min,
)

from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory


def make_folder(query):
    """创建任务文件夹并返回路径"""
    
    os.makedirs("./results", exist_ok=True)
    
    from datetime import datetime
    # 生成报告文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c for c in query[:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_query = safe_query.replace(' ', '_')
    
    folder_path = f"./results/{timestamp}_{safe_query}"
    os.makedirs(folder_path, exist_ok=True)
    
    return folder_path
    

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

    tools = [
        StructuredTool.from_function(search_web_min, name="search_web", description='''
            使用 DuckDuckGo 实时检索，返回前N条网页链接。"
        '''),
        StructuredTool.from_function(text_from_url_min, name="text_from_url", description='''
            抓取URL网页并返回标题与正文文本（最多max_chars字符）。
        '''),
        StructuredTool.from_function(search_scholar_min, name="search_scholar", description='''
            Google Scholar & Web PDF 搜索。你需要提供关键词，尽量返回包含 PDF 链接的条目。
            在这些有PDF链接的条目中，尽量选择论文最终发表的会议/期刊对应的文献库，而不是arxiv等预印本。
        '''),
        StructuredTool.from_function(search_arxiv_min, name="search_arxiv", description='''
            arxiv搜索接口。如果你需要寻找一篇论文的URL和pdf等，但是其他正式的途径中都没有搜到论文的url，可以调用这个工具来搜索arxiv上的相关论文。
            你需要提供关键词，返回的结果会包含标题、作者、出版日期、摘要和PDF链接等信息。
        '''),
        StructuredTool.from_function(zotero_router, name="zotero", description='''
            Zotero 聚合工具，通过 action 路由不同操作
            (create_collection：创建新文件夹，需要根据任务名称生成文件夹的名称
            /add_item：添加论文到Zotero的特定文件夹，需要提供论文的标题、作者、出版日期、摘要和PDF链接等信息
            /move_item：移动论文到Zotero的特定文件夹
            /list_collections：
            )
        '''),
        StructuredTool.from_function(pdf_downloader, name="pdf_downloader", description='''
            批量下载论文PDF到指定目录（参数：papers[{title,pdf_url}], folder）
        '''),
        StructuredTool.from_function(markdown_note_min, name="markdown_note", description='''
            记录 Markdown 笔记，在指定笔记目录中添加或删除内容（参数：title, content, folder?, append?）
        '''),
        StructuredTool.from_function(read_pdf_min, name="read_pdf_min", description='''
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
    # executor = AgentExecutor(agent=agent, tools=tools, memory=memory, max_iterations=10, verbose=True) # 限制最大对话轮数
    executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True) # 不限制

    # 设置全局任务文件夹
    task_folder = make_folder(query)
    
    # 更新 tools_definitions 中的全局变量
    import tools.tools_definitions
    tools.tools_definitions.task_folder = task_folder
    
    # 首次运行，输入是query    
    output = executor.invoke({"input": query})

    # 交互式继续：允许用户在任务结束后继续下达新指令，沿用上下文与工具
    while True:
        user_cmd = input("\n继续指令(回车结束)：").strip()
        if not user_cmd:
            break
        
        output = executor.invoke({"input": user_cmd})
        # print(output.get("output", ""))
        
    # save_report(query, output) # 保存最终报告

if __name__ == "__main__":
    q = setting.prompt
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    # run(q)
    run_with_langchain(q)

