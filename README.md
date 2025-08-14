# LLM智能Agent - 学术研究助手

一个基于LangChain和DeepSeek的智能学术研究助手，集成了多种工具功能，支持网络搜索、学术论文检索、PDF处理、Zotero文献管理和笔记记录等功能。

## 🚀 核心特性

- **🤖 智能对话**：基于DeepSeek大语言模型的自然语言交互
- **🔍 多源搜索**：支持DuckDuckGo网络搜索、Google Scholar、arXiv学术搜索
- **📚 文献管理**：完整的Zotero集成，支持文件夹创建、论文添加、移动等操作
- **📄 PDF处理**：PDF下载、文本提取、批量处理
- **📝 笔记记录**：自动生成Markdown格式的研究笔记
- **🌐 网页抓取**：智能提取网页内容并转换为结构化文本
- **🔄 交互式对话**：支持多轮对话，保持上下文连续性

## 📋 功能模块

### 搜索工具
- **search_web**: 使用DuckDuckGo进行实时网络搜索
- **search_scholar**: Google Scholar学术搜索，优先返回PDF链接
- **search_arxiv**: arXiv预印本搜索，获取最新研究论文

### 内容处理
- **text_from_url**: 网页内容抓取和文本提取
- **read_pdf**: 本地PDF文件文本提取
- **pdf_downloader**: 批量PDF下载管理

### 文献管理
- **zotero**: 完整的Zotero集成工具
  - 创建文件夹 (create_collection)
  - 添加论文 (add_item)
  - 移动论文 (move_item)
  - 列出文件夹 (list_collections)

### 笔记系统
- **write_markdown_note**: 自动生成Markdown格式研究笔记

## 🛠️ 安装配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置文件设置

创建 `.config` 文件并配置以下参数：

```bash
# DeepSeek API配置（推荐，价格更便宜）
DEEPSEEK_API_KEY=your_deepseek_api_key

# OpenAI API配置（备选）
OPENAI_API_KEY=your_openai_api_key

# Zotero集成配置
ZOTERO_API_KEY=your_zotero_api_key
ZOTERO_USER_ID=your_zotero_user_id

# 网络代理配置
PROXY_URL=your_proxy_url

# 默认配置
DEFAULT_QUERY=搜索近五年强化学习的论文
DEFAULT_DOWNLOAD_DIR=./downloads
DEFAULT_ZOTERO_COLLECTION=学术智能Agent
```

### 3. API密钥获取

#### DeepSeek API（推荐）
1. 访问 [DeepSeek平台](https://platform.deepseek.com/)
2. 注册账号并获取API Key
3. 价格优势：约 $0.14/1M tokens（比OpenAI便宜70%）

#### Zotero API
1. 登录 [Zotero](https://www.zotero.org/)
2. 进入设置 → API → 创建新的API Key
3. 在设置页面查看用户ID

## 🎯 使用方法

### 基本使用

```bash
python agent.py "帮我找一些关于强化学习的论文并保存到Zotero"
```

### 交互式对话

程序启动后支持多轮对话：

```bash
python agent.py
# 输入初始查询
# 继续指令(回车结束)：帮我下载这些论文的PDF
# 继续指令(回车结束)：将这些内容整理成笔记
# 继续指令(回车结束)：exit
```

### 使用示例

#### 1. 学术论文搜索与保存
```bash
python agent.py "帮我找一些关于KV Cache优化的论文，并保存到我的Zotero中"
```

#### 2. 网络资料整理
```bash
python agent.py "帮我上网查找资料，形成一份北京有趣citywalk路线的笔记"
```

#### 3. 技术研究
```bash
python agent.py "KV Cache的原理是什么？通过阅读相应的网页学习该领域的知识，系统地告诉我该领域的研究脉络和代表性论文"
```

## 📁 项目结构

```
LLMagent/
├── agent.py                 # 主程序入口（LangChain集成）
├── config_manager.py        # 配置管理器
├── .config                  # 配置文件
├── requirements.txt         # 依赖包列表
├── README.md               # 项目文档
├── tools/                  # 工具模块
│   ├── search_web.py       # 网络搜索
│   ├── search_scholar.py   # 学术搜索
│   ├── search_arxiv.py     # arXiv搜索
│   ├── text_from_url.py    # 网页内容提取
│   ├── pdf_downloader.py   # PDF下载
│   ├── pdf_reader.py       # PDF文本提取
│   ├── zotero_integration.py # Zotero集成
│   └── markdown_notes.py   # 笔记记录
└── downloads/              # PDF下载目录
```

## 🔧 技术架构

### LangChain集成
- 使用LangChain的Agent框架
- 支持结构化工具调用
- 内置对话记忆功能
- 最多10轮对话限制（可配置）

### 工具系统
- 基于LangChain的StructuredTool
- 自动参数验证和类型检查
- 错误处理和重试机制
- 代理配置支持

### 配置管理
- 统一的配置管理器
- 环境变量自动设置
- 配置验证和状态检查
- 多API支持（DeepSeek/OpenAI）

## 🎨 特色功能

### 智能工具路由
- 自动选择合适的搜索工具
- 智能参数填充
- 结果去重和排序
- 容错和降级处理

### 文献管理自动化
- 自动创建Zotero文件夹
- 批量论文添加
- 元数据自动填充
- 智能标签生成

### 研究笔记生成
- 自动生成Markdown格式
- 时间戳记录
- 内容追加模式
- 文件夹组织

## ⚠️ 注意事项

1. **网络配置**：确保网络连接正常，如需代理请配置PROXY_URL
2. **API限制**：注意各API的调用频率限制
3. **存储空间**：大量PDF下载时注意磁盘空间
4. **权限设置**：确保下载目录有写入权限
5. **Zotero同步**：Zotero操作需要有效的API Key和用户ID


## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

MIT License

---


**让AI助手成为您学术研究的得力助手！** 🎓 
