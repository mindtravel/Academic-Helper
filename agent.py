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

import tools.tools_definitions
from tools.tools_definitions import tools_api

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


    system_text = (
        "当你完成任务时，你需要最大限度地调用给定的工具吸收互联网上的信息作为严格的佐证，并且细致地辨别不合理的信息。"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_text),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools_api, prompt)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    # executor = AgentExecutor(agent=agent, tools=tools, memory=memory, max_iterations=10, verbose=True) # 限制最大对话轮数
    executor = AgentExecutor(agent=agent, tools=tools_api, memory=memory, verbose=True) # 不限制

    # 设置全局任务文件夹
    tools.tools_definitions.task_folder = make_folder(query)
    
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

