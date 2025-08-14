#!/usr/bin/env python3
"""
带有评价模型的改进Agent版本 - 任务模型和评价模型协作执行
"""

from __future__ import annotations

import json
import sys, os
from typing import Dict, List, Any, Tuple

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
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class TaskEvaluator:
    """任务评价模型"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.evaluation_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个严格的任务评价专家。你需要评估任务执行模型的工作质量。

评价标准：
1. **信息完整性** (30分): 是否全面回答了用户的问题，涵盖了所有关键点
2. **信息准确性** (25分): 提供的信息是否准确、可靠，有充分的证据支持
3. **工具使用效率** (20分): 是否合理使用了可用的工具，搜索策略是否有效
4. **逻辑清晰度** (15分): 回答是否逻辑清晰，结构合理
5. **任务完成度** (10分): 是否真正完成了用户要求的任务

评分规则：
- 90-100分: 优秀，任务完全完成，可以终止
- 70-89分: 良好，需要小幅改进
- 50-69分: 一般，需要显著改进
- 0-49分: 较差，需要大幅改进

请严格按照以下JSON格式返回评价结果：
{
    "overall_score": 85,
    "completion_status": "needs_improvement",
    "detailed_evaluation": {
        "information_completeness": {"score": 25, "comment": "..."},
        "information_accuracy": {"score": 20, "comment": "..."},
        "tool_usage_efficiency": {"score": 18, "comment": "..."},
        "logical_clarity": {"score": 12, "comment": "..."},
        "task_completion": {"score": 8, "comment": "..."}
    },
    "improvement_suggestions": ["建议1", "建议2", "建议3"],
    "should_continue": true,
    "termination_reason": null
}

completion_status可能的值：
- "completed": 任务完全完成，可以终止
- "needs_improvement": 需要改进
- "incomplete": 任务不完整，需要继续

should_continue: true表示需要继续执行，false表示可以终止
termination_reason: 如果should_continue为false，说明终止原因"""),
            ("human", """用户问题: {user_query}

任务执行历史:
{execution_history}

当前回答:
{current_response}

请评价任务执行质量并决定是否需要继续改进。""")
        ])
    
    def evaluate(self, user_query: str, execution_history: str, current_response: str) -> Dict[str, Any]:
        """评价任务执行质量"""
        try:
            # 构建评价消息
            messages = self.evaluation_prompt.format_messages(
                user_query=user_query,
                execution_history=execution_history,
                current_response=current_response
            )
            
            # 调用评价模型
            response = self.llm.invoke(messages)
            evaluation_text = response.content
            
            # 解析JSON响应
            try:
                evaluation = json.loads(evaluation_text)
                return evaluation
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回默认评价
                return {
                    "overall_score": 60,
                    "completion_status": "needs_improvement",
                    "detailed_evaluation": {
                        "information_completeness": {"score": 15, "comment": "JSON解析失败，需要重新评估"},
                        "information_accuracy": {"score": 15, "comment": "JSON解析失败，需要重新评估"},
                        "tool_usage_efficiency": {"score": 12, "comment": "JSON解析失败，需要重新评估"},
                        "logical_clarity": {"score": 9, "comment": "JSON解析失败，需要重新评估"},
                        "task_completion": {"score": 6, "comment": "JSON解析失败，需要重新评估"}
                    },
                    "improvement_suggestions": ["评价模型响应格式错误，需要重新执行"],
                    "should_continue": True,
                    "termination_reason": None
                }
                
        except Exception as e:
            print(f"评价模型出错: {e}")
            return {
                "overall_score": 50,
                "completion_status": "needs_improvement",
                "detailed_evaluation": {},
                "improvement_suggestions": [f"评价过程出错: {e}"],
                "should_continue": True,
                "termination_reason": None
            }

def run_with_evaluator(query: str) -> None:
    """使用评价模型的改进执行链路"""
    
    # 加载配置
    load_api_config()
    deepseek_key = get_config("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("请先在 .config 中配置 DEEPSEEK_API_KEY")
        return
    os.environ["OPENAI_API_KEY"] = deepseek_key
    os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com/v1"

    # 创建LLM实例
    llm = ChatOpenAI(model="deepseek-chat", temperature=0)
    
    # 创建评价模型
    evaluator = TaskEvaluator(llm)

    # 任务模型工具定义
    def _search_web_min(query: str, max_results: int = 10) -> list[str]:
        return search_web(query=query, max_results=max_results)

    def _text_from_url_min(url: str, timeout: int = 15, max_chars: int = 4000) -> dict:
        return text_from_url(url=url, timeout=timeout, max_chars=max_chars)

    def _search_arxiv_min(keywords: str, max_results: int = 10, year_from: int | None = None) -> list[dict]:
        return search_arxiv(keywords=keywords, max_results=max_results, year_from=year_from)

    def _search_scholar_min(keywords: str, max_results: int = 10) -> list[dict]:
        # 优先使用arXiv搜索，避免Google Scholar反爬虫
        print(f"🔍 搜索学术论文: {keywords}")
        print("📚 优先使用arXiv搜索，避免Google Scholar反爬虫问题")
        
        # 首先尝试arXiv搜索
        arxiv_results = search_arxiv(keywords, max_results)
        if arxiv_results:
            print(f"✅ arXiv搜索成功，找到 {len(arxiv_results)} 篇论文")
            return arxiv_results
        
        # 如果arXiv没有结果，再尝试Google Scholar
        print("⚠️ arXiv搜索无结果，尝试Google Scholar...")
        try:
            scholar_results = search_scholar_pdfs(keywords, max_results)
            if scholar_results:
                print(f"✅ Google Scholar搜索成功，找到 {len(scholar_results)} 篇论文")
                return scholar_results
            else:
                print("❌ Google Scholar搜索失败或无结果")
                return []
        except Exception as e:
            print(f"❌ Google Scholar搜索出错: {e}")
            return []

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
        
        if action == "create_collection":
            key = z.create_collection(collection_name or "", parent_collection=parent_collection)
            return {"ok": bool(key), "collection_key": key or ""}
        if action == "add_item":
            if not collection_key and collection_name:
                collection_key = z.find_or_create_collection(collection_name)
            if not collection_key:
                return {"ok": False, "error": "missing_collection_key"}

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
        StructuredTool.from_function(_search_arxiv_min, name="search_arxiv", description='''
            arxiv搜索接口。如果你需要寻找一篇论文的URL和pdf等，但是其他正式的途径中都没有搜到论文的url，可以调用这个工具来搜索arxiv上的相关论文。
            你需要提供关键词，返回的结果会包含标题、作者、出版日期、摘要和PDF链接等信息。
        '''),
        StructuredTool.from_function(_search_scholar_min, name="search_scholar", description='''
            智能学术搜索：优先使用arXiv搜索，避免Google Scholar反爬虫问题。
            你需要提供关键词，尽量返回包含 PDF 链接的条目。
            在这些有PDF链接的条目中，尽量选择论文最终发表的会议/期刊对应的文献库，而不是arxiv等预印本。
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

    # 任务模型系统提示
    task_system_text = (
        "你是任务执行专家。你需要使用可用的工具来完成任务，提供准确、完整、有证据支持的回答。"
        "对于学术论文搜索，优先使用search_arxiv工具，它更稳定可靠。"
        "确保你的回答逻辑清晰，信息准确，并充分满足用户的需求。"
    )
    
    task_prompt = ChatPromptTemplate.from_messages([
        ("system", task_system_text),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 创建任务执行器
    task_agent = create_tool_calling_agent(llm, tools, task_prompt)
    task_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    task_executor = AgentExecutor(agent=task_agent, tools=tools, memory=task_memory, verbose=True)

    # 执行循环
    max_iterations = 5  # 最大迭代次数
    iteration = 0
    execution_history = []
    
    print(f"🎯 开始执行任务: {query}")
    print("=" * 60)
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 第 {iteration} 轮执行")
        print("-" * 40)
        
        try:
            # 任务模型执行
            result = task_executor.invoke({"input": query})
            current_response = result.get("output", "")
            
            # 记录执行历史
            execution_history.append({
                "iteration": iteration,
                "response": current_response,
                "tools_used": result.get("intermediate_steps", [])
            })
            
            print(f"\n📝 任务模型回答:")
            print(current_response)
            
            # 构建执行历史文本
            history_text = ""
            for hist in execution_history:
                history_text += f"第{hist['iteration']}轮:\n{hist['response']}\n\n"
            
            # 评价模型评估
            print(f"\n🔍 评价模型评估中...")
            evaluation = evaluator.evaluate(query, history_text, current_response)
            
            print(f"\n📊 评价结果:")
            print(f"总体评分: {evaluation['overall_score']}/100")
            print(f"完成状态: {evaluation['completion_status']}")
            print(f"是否需要继续: {evaluation['should_continue']}")
            
            if evaluation.get('improvement_suggestions'):
                print(f"改进建议:")
                for i, suggestion in enumerate(evaluation['improvement_suggestions'], 1):
                    print(f"  {i}. {suggestion}")
            
            # 检查是否需要终止
            if not evaluation['should_continue']:
                print(f"\n✅ 任务完成！终止原因: {evaluation.get('termination_reason', '评价模型认为任务已充分完成')}")
                break
            
            # 如果评分很高，也可以考虑终止
            if evaluation['overall_score'] >= 90:
                print(f"\n🎉 任务完成度很高 (评分: {evaluation['overall_score']})，终止执行")
                break
            
            # 继续下一轮，更新查询以包含改进建议
            if evaluation.get('improvement_suggestions'):
                improvement_text = "请根据以下建议改进你的回答:\n" + "\n".join(evaluation['improvement_suggestions'])
                query = f"{query}\n\n{improvement_text}"
            
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断执行")
            break
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            break
    
    if iteration >= max_iterations:
        print(f"\n⚠️ 达到最大迭代次数 ({max_iterations})，停止执行")
    
    print("\n" + "=" * 60)
    print("🏁 执行完成")

if __name__ == "__main__":
    # 测试查询
    q = "阅读attention is all you need的论文原文并总结其内容"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    run_with_evaluator(q)
