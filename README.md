# 学术智能Agent

一个基于Python的命令行学术论文搜索和下载工具，支持智能关键词生成、自动PDF下载和Zotero集成。

## 功能特性

- 🔍 **智能搜索**：使用大语言模型将中文查询转换为英文关键词
- 📚 **多平台支持**：arXiv、Google Scholar、Semantic Scholar、PubMed
- 💾 **自动下载**：自动下载PDF文件到指定目录
- 📖 **Zotero集成**：将论文信息保存到Zotero中，支持自定义文件夹
- 🤖 **AI推荐**：基于用户兴趣推荐相关论文
- 🚀 **自动化**：无需手动操作，全自动流程

## 安装依赖

```bash
pip install -r requirements.txt
```

## API配置

### DeepSeek API（推荐，更便宜）

1. 注册 [DeepSeek](https://platform.deepseek.com/) 账号
2. 获取API Key
3. 设置环境变量：

```powershell
$env:DEEPSEEK_API_KEY="你的DeepSeek_API_Key"
```

**价格优势**：
- DeepSeek：约 $0.14/1M tokens
- OpenAI GPT-3.5：约 $0.50/1M tokens
- **节省约70%成本**

**关于联网搜索**：
- DeepSeek API本身不提供联网搜索功能
- 本工具通过arXiv API直接获取论文信息
- 论文数据来自arXiv官方RSS feed，实时更新

### OpenAI API（备选）

```powershell
$env:OPENAI_API_KEY="你的OpenAI_API_Key"
```

### Zotero集成配置

1. 获取Zotero API Key：
   - 登录 [Zotero](https://www.zotero.org/)
   - 进入设置 → API → 创建新的API Key

2. 获取用户ID：
   - 在Zotero设置页面查看用户ID

3. 设置环境变量：

```powershell
$env:ZOTERO_API_KEY="你的Zotero_API_Key"
$env:ZOTERO_USER_ID="你的Zotero_用户ID"
```

## 使用方法

### 自动测试模式

```bash
python agent.py
```

默认搜索"搜索近五年强化学习的论文"，支持选择保存方式：
- **选项1**：下载PDF到本地文件夹
- **选项2**：保存到Zotero（推荐）
- **选项3**：两种方式都执行

### 自定义搜索

修改 `agent.py` 中的 `query` 变量：

```python
query = "你的搜索查询"
```

## 项目结构

```
GUIAgent/
├── agent.py              # 主程序入口
├── llm.py               # 大语言模型API调用
├── searcher.py          # 学术平台搜索
├── downloader.py        # PDF下载管理
├── zotero_integration.py # Zotero集成模块
├── requirements.txt     # 依赖包列表
├── README.md           # 项目文档
├── .zotero_config      # Zotero配置文件
├── debug/              # 调试脚本文件夹
│   ├── setup_zotero.py      # Zotero配置向导
│   ├── get_user_id.py       # 获取Zotero用户ID
│   ├── test_zotero.py       # Zotero集成测试
│   ├── debug_zotero.py      # Zotero API调试
│   ├── debug_create_collection.py # 创建文件夹调试
│   ├── debug_add_item.py    # 添加论文调试
│   └── debug_move_item.py   # 移动论文调试
└── downloads/          # PDF下载目录
```

## 支持的学术平台

- **arXiv**：计算机科学、数学、物理等预印本
- **Google Scholar**：综合性学术搜索
- **Semantic Scholar**：AI驱动的学术搜索
- **PubMed**：生物医学文献

## Zotero集成功能

### 主要特性

- **自动创建文件夹**：在Zotero中自动创建指定文件夹
- **完整元数据**：保存论文标题、作者、摘要、发布日期等
- **PDF链接**：自动添加PDF下载链接作为附件
- **智能标签**：自动添加arXiv、来源、工具标签
- **批量处理**：支持批量添加多篇论文

### 使用流程

1. 配置Zotero API Key和用户ID
2. 运行程序并选择"保存到Zotero"
3. 输入目标文件夹名称（可选）
4. 程序自动将论文信息保存到Zotero

## 调试工具

`debug/` 文件夹包含各种调试脚本：

- **setup_zotero.py**：Zotero配置向导
- **get_user_id.py**：获取Zotero用户ID
- **test_zotero.py**：测试Zotero集成功能
- **debug_*.py**：各种API调试脚本

如需调试Zotero集成问题，可以运行：
```bash
python debug/test_zotero.py
```

## 错误处理

- 网络连接问题：自动重试和代理设置
- API调用失败：优雅降级到原始查询
- 下载失败：跳过并继续处理其他文件
- Zotero集成：详细的错误提示和回退机制

## 注意事项

1. 确保网络连接正常
2. 配置正确的API Key
3. 下载目录需要写入权限
4. 大量下载时注意磁盘空间
5. Zotero集成需要有效的API Key和用户ID

## 开发计划

- [x] 支持更多学术平台
- [x] 添加Zotero集成
- [ ] 添加论文摘要分析
- [ ] 实现批量搜索功能
- [ ] 添加搜索历史记录
- [ ] 支持自定义下载目录
- [ ] 添加更多学术数据库支持 