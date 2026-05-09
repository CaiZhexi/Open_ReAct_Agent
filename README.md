# ReAct-Agent 智能知识库系统

> 企业级 Agentic RAG 系统 - 结合多模态工具、增量式推理与多层安全防御

ReAct-Agent 是一个结合多模态工具、调度器推理与多级检索的企业级知识库问答系统。项目采用 Flask + SQLite + Faiss 搭建完整后端，并提供现代化的 Web 管理界面与丰富的 API，支持 Agent 决策、网络搜索、Python 代码执行等高级能力。

---

## 📖 目录

- [功能亮点](#-功能亮点)
- [系统架构概览](#-系统架构概览)
- [环境要求](#-环境要求)
- [快速开始](#-快速开始)
- [模型配置](#-模型配置)
- [系统配置](#️-系统配置)
- [运行服务](#️-运行服务)
- [Web 界面使用指南](#-web-界面使用指南)
- [API 速览](#-api-速览)
- [V2 Agentic RAG 流程](#-v2-agentic-rag-流程)
- [数据与存储](#-数据与存储)
- [Python 代码执行器](#-python-代码执行器)
- [项目结构](#-项目结构)
- [脚本工具使用](#️-脚本工具使用)
- [文档导航](#-文档导航)
- [使用场景与最佳实践](#-使用场景与最佳实践)
- [常见问题与解决方案](#-常见问题与解决方案)
- [已知限制与改进计划](#-已知限制与改进计划)
- [贡献指南](#-贡献指南)
- [许可证与维护](#-许可证与维护)

---

## ✨ 功能亮点

### 核心能力

- **双模式支持**：V2 完整版（增量式上下文迭代）+ Lite 简化版（Plan → Execute → Answer 顺序执行），满足不同场景需求
- **Agentic RAG**：以工具平等为核心，支持知识库检索、重排、Python 执行、网络搜索等多种动作组合
- **多级检索与重排**：向量检索 → 轻量重排 → 高精重排，提升召回与相关性
- **多任务分解**：自动识别并拆解复杂查询为多个子任务，并行跟踪处理
- **流式输出**：支持 Markdown 和 LaTeX 实时渲染，提升用户体验

### 智能特性

- **对话历史管理**：支持多轮对话上下文，理解代词指代和上下文引用
- **智能置信度评估**：回答生成后自动评估质量，综合考虑完整性、准确性和工具使用情况
- **工具调用限制**：智能管理各工具调用次数，避免过度调用和资源浪费
- **任务完整性检查**：严格验证所有子任务完成状态，确保不遗漏任何问题

### 文档与数据

- **批量文档处理**：异步队列管理文件上传、分块、向量化，实时反馈处理进度
- **多格式支持**：支持 TXT、PDF、DOCX、XLSX、Markdown 等多种文档格式
- **向量存储**：基于 Faiss 的高效向量检索，支持大规模文档库

### 安全与监控

- **多层安全防御**：
  - LLM 安全审查：检测恶意请求和系统管理操作
  - AST 静态审计：代码执行前的语法树分析
  - 进程隔离执行：沙箱环境中运行代码
  - 白名单机制：仅允许预定义的安全模块和函数
  - 资源限额：内存、CPU、文件大小、递归深度等多重限制
  
- **Python 代码执行器**：
  - 支持数学计算、数据分析、可视化等
  - 预装 NumPy、Pandas、SymPy、Matplotlib、Plotly 等科学计算库
  - HSL（High-Security Level）执行器提供最高级别安全保障
  
- **IO 日志系统**：
  - 完整记录 API 请求和 LLM 调用
  - 支持日志分析和格式化工具
  - 便于调试、审计和性能分析

### 用户体验

- **现代化前端**：
  - 知识库管理、文档上传、问答流程可视化
  - 支持停止生成、下载 LLM 输入输出
  - 工具面板展示执行详情、耗时和结果
  - Markdown 和 LaTeX 实时渲染
  
- **完善文档**：
  - 架构设计文档（V2_ARCHITECTURE.md）
  - API参考文档（API_REFERENCE.md）
  - 安全设计文档（SECURITY.md）
  - 部署指南（DEPLOYMENT.md）
  - 开发指南（DEVELOPMENT.md）

---

## 🧱 系统架构概览

### 核心组件

- **Flask 应用层**：提供 REST API 与 Web 界面，支持 CORS 跨域
- **数据存储层**：
  - `DatabaseManager`：SQLite 数据库管理（知识库、文档、队列、分块等）
  - `VectorStore`：基于 Faiss 的向量索引及元数据管理
- **文档处理层**：
  - `DocumentProcessingQueue`：异步队列处理文档上传、分块、向量化
  - `DocumentProcessor`：文档解析与分块逻辑
- **Agent 层**：
  - **V2 完整版**：`V2Agent` 增量式上下文迭代，统一认知空间
  - **Lite 简化版**：`LiteDispatcher` 顺序执行，Plan → Execute → Answer
- **工具层**：
  - `search`：知识库检索（最多10次）
  - `web_search`：网络搜索（最多3次）
  - `python_code`：代码执行（最多10次）
  - `tool_registry`：工具注册与调用统计
- **执行器层**：
  - `PythonExecutor`：默认执行器
  - `PythonExecutorV2`：进程隔离执行器（HSL）
  - `ExecutorFactory`：执行器工厂，支持动态切换
  - `ExecutorMonitor`：执行监控、审计和速率限制
- **API 客户端层**：
  - 统一的 LLM、Embedding、Rerank、Search API 客户端
  - 支持 IO 日志记录

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Web 界面                             │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────┴─────────────────────────────────────┐
│                      Flask 应用层                           │
│  ├─ 路由蓝图：kb_bp, doc_bp, rag_bp, rag_v2_bp            │
│  ├─ 中间件：IO 日志、请求监控                             │
│  └─ 健康检查、静态文件服务                                 │
└─────────────┬─────────────────────────────┬─────────────────┘
              │                             │
    ┌─────────┴─────────┐       ┌──────────┴──────────┐
    │ Lite Dispatcher   │       │     V2 Agent        │
    │  简化并行架构     │       │  增量式迭代架构      │
    └─────────┬─────────┘       └──────────┬──────────┘
              │                             │
              └─────────────┬───────────────┘
                            │
            ┌───────────────┴────────────────┐
            │         工具层 (Tools)         │
            │  - search (知识库检索)         │
            │  - web_search (网络搜索)       │
            │  - python_code (代码执行)      │
            └───────────────┬────────────────┘
                            │
        ┌───────────────────┼────────────────────┐
        │                   │                    │
┌───────┴────────┐  ┌───────┴────────┐  ┌───────┴────────┐
│  VectorStore   │  │  API Clients   │  │ Python Executor│
│  (Faiss索引)   │  │ (LLM/Search)   │  │   (HSL沙箱)    │
└────────────────┘  └────────────────┘  └────────────────┘
        │
┌───────┴────────┐
│ DatabaseManager│
│  (SQLite DB)   │
└────────────────┘
```

### 架构特点

- **模块化设计**：各层职责清晰，易于维护和扩展
- **双模式并存**：V2/Lite 模式可独立运行，互不干扰
- **工具平等原则**：所有工具在同一层级，由 Agent 动态选择
- **流式友好**：全链路支持流式输出，提升用户体验
- **安全优先**：多层安全防御，从请求审查到代码执行全程保护

详细架构请参阅 `docs/V2_ARCHITECTURE.md` 文档。

---

## 🛠 环境要求

**系统要求**：
- 操作系统：macOS / Linux / Windows
- Python：3.10 或 3.11（推荐 3.10）
- 虚拟环境：venv（必需，请在项目根目录创建）

**依赖**：
- 详见 `requirements.txt`（所有依赖会自动安装）

**API Key 配置**（按需配置，支持多提供商）：
- **Embedding 模型**：SiliconFlow（或 OpenAI、Cohere等）
- **Chat 模型**：阿里云百炼（或 OpenAI、DeepSeek、Anthropic等）
- **Rerank 模型**：SiliconFlow（或 Cohere、Jina AI等）
- **搜索服务**：Metaso（或 Serper、Tavily等）

> ⚠️ 必须在项目根目录创建虚拟环境 `venv`，不要在其他位置创建。

---

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/CaiZhexi/Open_ReAct_Agent.git
cd Open_ReAct_Agent

# 2. 创建虚拟环境（项目根目录）
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate       # macOS / Linux
# 或
venv\Scripts\activate        # Windows PowerShell

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 6. 初始化数据目录（首次运行时自动完成）
mkdir -p data/vectors
```

---

## 🔐 模型配置

系统支持多提供商混合使用，每个功能模块可独立配置：

### 当前配置

项目默认使用以下服务提供商：

- **Embedding 模型**：SiliconFlow - Qwen/Qwen3-Embedding-8B (1024维)
- **Chat 模型**：阿里云百炼 - qwen-flash
- **Rerank 模型**：SiliconFlow - Qwen/Qwen3-Reranker-0.6B
- **搜索服务**：Metaso 搜索引擎

### 配置方式

1. 复制环境变量模板文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的 API 密钥：
```bash
# ==================== Embedding 模型配置 ====================
EMBED_API_KEY=your-embed-api-key
EMBED_API_URL=https://api.siliconflow.cn/v1/embeddings
EMBED_MODEL=Qwen/Qwen3-Embedding-8B
EMBED_DIMENSIONS=1024

# ==================== Chat 模型配置 ====================
CHAT_API_KEY=your-chat-api-key
CHAT_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
CHAT_MODEL=qwen-flash

# ==================== Rerank 模型配置 ====================
RERANK_API_KEY=your-rerank-api-key
RERANK_API_URL=https://api.siliconflow.cn/v1/rerank
RERANK_MODEL=Qwen/Qwen3-Reranker-0.6B

# ==================== 网络搜索配置 ====================
SEARCH_API_KEY=your-search-api-key
SEARCH_API_URL=https://metaso.cn/api/v1/search
```

### 多提供商支持

系统支持混合使用不同提供商：
- **OpenAI**：GPT-4、text-embedding-3-large 等
- **DeepSeek**：DeepSeek-V3 等
- **Anthropic**：Claude 系列
- **Cohere**：Embed、Rerank 模型
- **Jina AI**：Reranker 模型

详见 `config.py` 中的详细注释说明

---

## ⚙️ 系统配置

### 🔐 安全配置（必读）

> 项目在 2026/05 完成了一次全面安全加固（详见 `SECURITY.md` / commit `05e6333`）。以下环境变量是**部署前必须检查**的项：

| 变量 | 默认 | 说明 |
|---|---|---|
| `SECRET_KEY` | 无 | **必填**，长度 ≥ 32 的强随机字符串。未设置或使用默认占位符时**拒绝启动**。生成：`python -c "import secrets; print(secrets.token_urlsafe(48))"`。开发环境可用 `DEV_MODE=true` 生成临时随机 key |
| `FLASK_DEBUG` | `False` | 生产必须保持 False；Werkzeug debug console 存在远程代码执行风险 |
| `HOST` | `127.0.0.1` | 默认仅绑定本机环回。要对外暴露需显式 `export HOST=0.0.0.0`，且务必配合鉴权 + 前置反代/防火墙 |
| `PORT` | `5004` | 服务端口 |
| `CORS_ORIGINS` | 仅 `127.0.0.1:5004` / `localhost:5004` | 逗号分隔的可信来源白名单，如 `https://your.example.com` |
| `APP_API_KEY` | 无 | 设置后所有写接口（`/api/v2/chat`、`/clear_files`、`/delete_file`、`/kb/*/delete`、文档上传等）强制校验 `X-API-Key` 头。生产强烈建议设置 |
| `IO_LOG_KEEP_RAW` | `false` | 是否把 LLM 的 `raw_request/raw_response` 落盘（仍会脱敏）。生产不建议开启 |
| `PYTHON_EXECUTOR_DISABLE_NETWORK` | `true` | 沙箱子进程禁用 `socket` 相关调用，防 SSRF |
| `PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN` | `true` | 允许沙箱内 `open()`；上传的文件会先复制进沙箱，只能访问副本，读不到宿主文件 |

### 多层安全防御一览

- **API Key / Authorization / Cookie 等 header 落盘前自动脱敏**（`<redacted>`）；LLM `messages` 按敏感字段递归脱敏
- **写接口强制鉴权**（`APP_API_KEY` 设置后生效），CORS 仅放白名单 origin
- **Python 执行器**：AST 静态审计（禁用 `__reduce__` / `__class_getitem__` / `__subclasses__` 等逃逸 gadget）→ 正则审计 → 进程隔离 → 资源限额 → 沙箱目录 → 禁网
- **uploads 文件复制进沙箱**：即便底层 C 扩展绕过 safe_open，也只能读沙箱副本
- **Prompt Injection 防御**：外部检索结果用 `<untrusted_source>` 包裹，system prompt 声明忽略其中指令
- **统一错误响应**：前端只看到 `error_id`，详细栈仅进日志
- **速率限制**：每用户每分钟 20 次 / 每小时 100 次 Python 执行，全局 100/分钟

### 回归测试

```bash
SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") \
  ./venv/bin/python -m unittest tests.test_security_regression -v
# 21 tests — 覆盖脱敏 / 沙箱 / AST / 鉴权 / CORS / prompt 包裹 / path traversal / foreign_keys
```

### 核心配置（config.py）

**文档处理配置**：
```python
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'xlsx', 'md'}
CHUNK_SIZE = 500  # 文档分块大小
CHUNK_OVERLAP = 50  # 分块重叠大小
```

**Agentic RAG 配置**：
```python
INITIAL_RETRIEVAL_TOP_K = 50  # 初始检索数量
LIGHT_RERANK_TOP_K = 20  # 轻量重排保留数量
FINAL_RERANK_TOP_K = 5  # 最终重排数量
CONFIDENCE_THRESHOLD = 0.7  # 置信度阈值
MAX_RETRY_ATTEMPTS = 2  # 最大重试次数
AGENT_DECISION_THRESHOLD = 0.3  # Agent决策阈值
```

**调度器配置**：
```python
USE_DISPATCHER = True  # 是否使用调度器架构
DISPATCHER_MAX_STEPS = 10  # 调度器最大执行步数
DISPATCHER_TOOL_TIMEOUT = 30  # 工具执行超时时间（秒）
DISPATCHER_LOG_LEVEL = 'INFO'  # 日志级别
```

**提示词模板**：

所有提示词统一在 `PromptTemplates` 类中管理，包括：
- V2 Plan/Evaluate/Answer 提示词
- Lite Plan/Answer 提示词
- Python 代码生成提示词
- 安全审查提示词
- 置信度评估提示词

详见 `config.py` 第 284-1503 行。

---

## ▶️ 运行服务

### 推荐方式：使用 app.py
```bash
source venv/bin/activate
python app.py          # 端口 5004
```

启动后会自动：
- 启动 Flask Web 服务器
- 初始化文档处理队列
- 启用 IO 日志系统（可通过环境变量控制）

控制台输出示例：
```
================================================================================
启动 RAG 知识库问答系统
================================================================================
📋 文档处理队列: 已启动
🌐 访问地址: http://localhost:5004
📚 API健康检查: http://localhost:5004/api/health
🆕 新功能: 批量文档上传 + Agentic RAG
🚀 V2架构: 增量式上下文迭代 - /api/v2/chat
📊 V2架构信息: /api/v2/info
📝 IO日志: logs/api_io_20251006_111244.jsonl
📊 日志状态: http://localhost:5004/api/io-logs
================================================================================
```

### IO 日志控制

默认启用 IO 日志，记录所有 API 请求和 LLM 调用：
```bash
# 禁用 IO 日志
export ENABLE_IO_LOGGING=false
python app.py

# 启用 IO 日志（默认）
export ENABLE_IO_LOGGING=true
python app.py
```

日志文件位置：`logs/api_io_*.jsonl`

---

## 🧭 Web 界面使用指南

- **知识库管理**：创建/重命名/删除知识库，查看处理进度与向量统计
- **文档管理**：上传 TXT/PDF/DOCX/XLSX/MD，支持批量上传与进度提示
- **Agentic 问答**：切换 V2/Lite 模式，实时查看工具调用步骤、执行日志及置信度
- **工具面板**：展示各工具执行详情、耗时和结果，可折叠查看
- **流式输出**：支持 Markdown 和 LaTeX 实时渲染

---

## 🔌 API 速览

### 核心接口

| 模块 | 端点 | 说明 |
| --- | --- | --- |
| 健康检查 | `GET /api/health` | 查看系统状态与模型配置 |
| IO 日志 | `GET /api/io-logs` | 查看 IO 日志统计信息 |
| 知识库 | `GET /api/kb/list`<br>`POST /api/kb/create`<br>`DELETE /api/kb/{id}/delete` | 管理知识库与统计信息 |
| 文档 | `POST /api/docs/upload/{kb_id}`<br>`POST /api/docs/batch-upload/{kb_id}` | 单文件与批量上传、状态查询 |
| RAG 问答 (Lite) | `POST /api/rag/agentic-chat` | Lite 模式 RAG 问答（流式输出） |
| 工具管理 | `GET /api/rag/tools`<br>`GET /api/rag/tools/stats` | 查看已注册工具及执行统计 |

### V2 架构接口（增量式上下文迭代）

| 端点 | 说明 |
| --- | --- |
| `POST /api/v2/chat` | V2 增量式问答接口，支持流式输出 |
| `GET /api/v2/info` | V2 架构信息与配置 |

### V2 架构特点

- **增量式上下文迭代**：动态构建和扩展上下文，避免冗余
- **多任务分解**：自动识别并拆解复杂查询为多个子任务
- **工具调用限制**：智能管理工具调用次数，避免过度调用
- **完整性检查**：严格验证所有子任务完成状态

详见 `docs/V2_ARCHITECTURE.md` 文档，包含完整的架构说明和流程图。

### API 参数详解

**POST /api/v2/chat 参数说明**：
- `query`（必需）：用户问题，字符串类型
- `stream`（可选）：是否流式输出，布尔值，默认 `true`
- `history`（可选）：对话历史，数组格式 `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`
- `selected_files`（可选）：用户选中的数据文件列表，用于数据分析任务

**POST /api/rag/agentic-chat 参数说明**：
- `query`（必需）：用户问题
- `kb_ids`（可选）：指定知识库 ID 列表，默认使用所有知识库
- `stream`（可选）：是否流式输出，默认 `true`

完整参数与返回结构请参考 `app/routes/rag_v2.py` 文件。

---

## 🧠 V2 Agentic RAG 流程

V2 架构采用增量式上下文迭代，核心流程如下：

1. **Plan（规划）**：分析当前上下文，决定下一步行动
   - 识别是否需要任务分解
   - 选择合适的工具（search/web_search/python_code）
   - 检查工具调用次数限制

2. **Tool Using（工具执行）**：调用选定的工具
   - 知识库检索：向量搜索相关文档
   - 网络搜索：获取实时信息
   - Python 执行：进行数学计算和数据分析

3. **Evaluate（评估）**：判断信息是否充分
   - 检查所有子任务完成状态
   - 评估证据质量和完整性
   - 决定是否继续迭代或生成答案

4. **Streaming Output（流式输出）**：生成最终答案
   - 支持 Markdown 和 LaTeX 格式
   - 逐字流式输出，提升用户体验

5. **Finish（完成）**：最终质量评估
   - 综合评估答案质量
   - 计算置信度分数
   - 生成评估理由

详细流程图请参阅 `docs/V2_ARCHITECTURE.md` 文档。

---

## 💾 数据与存储

- **SQLite 文件**：`data/knowledge_base.db`
- **向量索引**：`data/vectors/kb_<id>/faiss.index`
- **元数据**：`data/vectors/kb_<id>/metadata.json`
- **IO 日志**：`logs/api_io_*.jsonl`
- **上传临时文件**：由队列处理完成后自动清理

数据库结构与队列策略请参考 `app/models/database.py`、`app/services/document_queue.py`。

---

## 🐍 Python 代码执行器

系统内置安全的 Python 代码执行环境，支持多种科学计算库，采用多层安全防御机制。

### 执行器类型

1. **默认执行器** (`PythonExecutor`)
   - 基础白名单机制
   - 受限内置函数
   - 适用于低风险环境

2. **HSL 执行器** (`PythonExecutorV2`)
   - High-Security Level（高安全级别）
   - AST 静态审计 + 进程隔离
   - 资源限额 + 沙箱文件系统
   - 生产环境推荐

通过环境变量切换：
```bash
export PYTHON_EXECUTOR_TYPE=process_isolated  # HSL执行器（推荐）
export PYTHON_EXECUTOR_TYPE=default           # 默认执行器
```

### 预装模块

**核心数值计算**：
- `math` - 基础数学函数（sqrt, sin, cos, factorial等）
- `cmath` - 复数数学
- `statistics` - 统计函数（mean, stdev, median等）
- `decimal` - 高精度小数
- `fractions` - 分数运算
- `random` - 随机数生成

**高级科学计算**：
- `numpy` - 数组计算与线性代数
- `scipy` - 科学计算（积分、优化、信号处理等）
- `mpmath` - 任意精度数学
- `sympy` - 符号数学（方程求解、微分、积分等）

**数据分析**：
- `pandas` - 数据处理与分析
- `statsmodels` - 统计模型
- `sklearn` - 机器学习（scikit-learn）

**可视化**：
- `matplotlib` - 标准绘图库
- `plotly` - 交互式图表
- `plotnine` - ggplot2 风格绘图

**扩展计算**：
- `numpy_financial` - 金融计算
- `xarray` - 多维标记数组
- `geopandas` - 地理空间数据

**标准库**：
- `datetime` - 日期时间处理
- `collections` - 数据结构（Counter, defaultdict等）
- `itertools` - 迭代工具（combinations, permutations等）
- `re` - 正则表达式
- `json` - JSON 处理

### 多层安全防御

#### 第一层：LLM 安全审查
- 请求前检测恶意意图
- 识别系统管理操作
- 拒绝敏感文件访问

#### 第二层：AST 静态审计
- 代码执行前语法树分析
- 检测危险函数调用（eval, exec, __import__等）
- 禁止访问私有属性（__xxx__）
- 防止模块导入绕过

#### 第三层：白名单机制
- 仅允许预定义的安全模块
- 受限的内置函数集合
- 禁止危险函数（open, compile, exec等）

#### 第四层：进程隔离 + 资源限额
- 独立进程执行（HSL）
- 内存限制（默认 256MB）
- CPU 时间限制（默认 10秒）
- 文件大小限制（默认 10MB）
- 递归深度限制（默认 1000）

#### 第五层：沙箱文件系统
- 临时目录隔离
- 默认禁止文件 IO
- 可选只读/可选写入
- 环境变量净化

#### 第六层：执行监控
- 实时监控执行状态
- 审计日志记录
- 速率限制（防止滥用）

### 配置选项

在 `config.py` 中可自定义：

```python
# 执行器类型
PYTHON_EXECUTOR_TYPE = 'process_isolated'  # 或 'default'

# 基础限制
PYTHON_EXECUTOR_TIMEOUT = 10  # 超时时间（秒）
PYTHON_EXECUTOR_MAX_OUTPUT = 5000  # 最大输出长度
PYTHON_EXECUTOR_MAX_CODE_LENGTH = 10000  # 最大代码长度

# 资源限制（HSL 执行器）
PYTHON_EXECUTOR_MAX_MEMORY_MB = 256  # 最大内存
PYTHON_EXECUTOR_MAX_CPU_TIME = 10  # 最大 CPU 时间
PYTHON_EXECUTOR_MAX_FILE_SIZE_MB = 10  # 最大文件大小

# 安全配置
PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN = False  # 是否允许 open()
PYTHON_EXECUTOR_SANDBOX_ALLOW_WRITE = False  # 是否允许写入
PYTHON_EXECUTOR_SANITIZE_ENV = True  # 是否净化环境变量
PYTHON_EXECUTOR_RECURSION_LIMIT = 1000  # 递归深度上限

# 监控配置
PYTHON_EXECUTOR_ENABLE_MONITORING = True  # 启用监控
PYTHON_EXECUTOR_ENABLE_AUDIT = True  # 启用审计日志
PYTHON_EXECUTOR_ENABLE_RATE_LIMIT = True  # 启用速率限制
PYTHON_EXECUTOR_RATE_LIMIT_PER_MINUTE = 20  # 每分钟最大执行次数
PYTHON_EXECUTOR_RATE_LIMIT_PER_HOUR = 100  # 每小时最大执行次数

# 白名单配置
PYTHON_ALLOWED_MODULES = {...}  # 详见 config.py 第 161-265 行
PYTHON_ALLOWED_BUILTINS = [...]  # 详见 config.py 第 268-281 行
```

### 添加自定义模块到白名单

在 `config.py` 中修改 `PYTHON_ALLOWED_MODULES` 字典，添加你需要的模块：

```python
PYTHON_ALLOWED_MODULES = {
    'numpy': ['*'],
    'your_module': ['function1', 'function2', 'Class1'],  # 添加自定义模块
    # '*' 表示允许所有函数，可指定具体函数列表以提高安全性
}
```

### 安全文档

详细的安全特性和防护机制请参阅：
- `docs/SECURITY.md` - 安全设计和多层防御架构
- `scripts/test_executor_security.py` - Python 执行器安全测试脚本
- `scripts/test_sandbox_security.py` - 沙箱安全测试脚本

---

## 📁 项目结构

```
ReAct-Agent/
├── app/
│   ├── routes/              # API 路由蓝图
│   │   ├── knowledge_base.py   # 知识库管理
│   │   ├── documents.py        # 文档上传与处理
│   │   ├── rag.py              # Lite RAG 接口（简化顺序执行）
│   │   └── rag_v2.py           # V2 RAG 接口（增量式迭代）
│   ├── services/            # 核心服务层
│   │   ├── v2_agent.py            # V2 Agent 核心实现
│   │   ├── lite_dispatcher.py     # Lite 调度器
│   │   ├── tools.py               # 工具注册与管理
│   │   ├── python_executor.py     # Python 执行器（默认）
│   │   ├── python_executor_v2.py  # Python 执行器（HSL）
│   │   ├── executor_factory.py    # 执行器工厂
│   │   ├── executor_monitor.py    # 执行监控与审计
│   │   ├── security_checker.py    # LLM 安全审查
│   │   ├── api_clients.py         # API 客户端（统一接口）
│   │   ├── api_clients_with_logging.py  # API 客户端（带日志）
│   │   ├── io_logger.py           # IO 日志系统
│   │   ├── document_processor.py  # 文档解析与分块
│   │   └── document_queue.py      # 文档处理队列
│   ├── models/              # 数据模型
│   │   ├── database.py         # SQLite 数据库管理
│   │   └── vector_store.py     # Faiss 向量存储
│   ├── templates/           # 前端 HTML 模板
│   │   └── index.html          # 主界面
│   └── static/              # 静态资源
│       ├── css/style.css       # 样式
│       └── js/app.js           # 前端逻辑
├── docs/                    # 完整文档集合
│   ├── V2_ARCHITECTURE.md              # V2 架构详细文档
│   ├── README.md                       # 文档索引
│   ├── API_REFERENCE.md                # API 参考文档
│   ├── SECURITY.md                     # 安全设计文档
│   ├── DEPLOYMENT.md                   # 部署指南
│   └── DEVELOPMENT.md                  # 开发指南
├── scripts/                 # 实用脚本工具
│   ├── analyze_io_log.py          # IO 日志分析
│   ├── format_io_logs.py          # IO 日志格式化
│   ├── trace_v2_agent_io.py       # V2 Agent 调试追踪
│   ├── run_complex_trace.py       # 复杂场景追踪
│   ├── run_with_io_logging.py     # 带日志运行
│   ├── test_executor_security.py  # 执行器安全测试
│   ├── test_sandbox_security.py   # 沙箱安全测试
│   ├── test_request_logging.py    # 请求日志测试
│   ├── render_mermaid_diagrams.py # Mermaid 图表渲染
│   ├── render_mermaid_local.py    # 本地图表渲染
│   ├── start_debug.sh             # 调试启动脚本
│   └── README_format_logs.md      # 日志格式化说明
├── data/                    # 数据存储（运行时创建）
│   ├── knowledge_base.db       # SQLite 数据库
│   └── vectors/                # Faiss 向量索引
│       └── kb_<id>/            # 各知识库向量
│           ├── faiss.index     # 向量索引文件
│           └── metadata.json   # 元数据
├── logs/                    # 日志文件（运行时创建）
│   └── api_io_*.jsonl          # API 和 LLM 调用日志
├── uploads/                 # 上传临时文件（队列处理后删除）
├── .env.example             # 环境变量模板（复制为.env后填入密钥）
├── .gitignore               # Git 忽略规则
├── LICENSE                  # MIT 许可证
├── app.py                   # Flask 应用入口（端口 5004）
├── config.py                # 配置管理
│                            # - 模型配置（Embed/Chat/Rerank/Search）
│                            # - 提示词模板（PromptTemplates类，第284-1503行）
│                            # - 执行器配置
│                            # - 安全配置
├── requirements.txt         # Python 依赖清单
├── README.md                # 本文档
└── venv/                    # 虚拟环境（需自行创建）
```

### 重点目录说明

**docs/** - 完整的项目文档，包括：
- 架构设计文档
- 功能特性说明
- 安全测试报告
- 修复与改进记录

**scripts/** - 开发和运维工具：
- 日志分析与格式化
- 调试追踪工具
- 安全测试脚本
- 数据库迁移工具

**app/services/** - 核心业务逻辑：
- Agent 实现（V1/V2）
- 工具系统
- 执行器体系
- API 客户端

---

## 🛠️ 脚本工具使用

项目提供了丰富的脚本工具，位于 `scripts/` 目录：

### 日志分析工具

```bash
# 分析 IO 日志
python scripts/analyze_io_log.py logs/api_io_20251012_*.jsonl

# 格式化 IO 日志
python scripts/format_io_logs.py logs/api_io_20251012_*.jsonl

# 查看格式化说明
cat scripts/README_format_logs.md
```

### 调试追踪工具

```bash
# V2 Agent 调试追踪
python scripts/trace_v2_agent_io.py

# 复杂场景追踪
python scripts/run_complex_trace.py

# 带 IO 日志运行
python scripts/run_with_io_logging.py
```

### 安全测试工具

```bash
# 执行器安全测试
python scripts/test_executor_security.py

# 沙箱安全测试
python scripts/test_sandbox_security.py

# 请求日志测试
python scripts/test_request_logging.py
```

### 图表渲染工具

```bash
# 渲染 Mermaid 图表（需要 mermaid-cli）
python scripts/render_mermaid_diagrams.py

# 本地渲染
python scripts/render_mermaid_local.py
```

---

## 📚 文档导航

完整的项目文档位于 `docs/` 目录，推荐阅读顺序：

### 快速入门
1. `README.md`（本文档）- 项目概览
2. `docs/V2_ARCHITECTURE.md` - V2 架构详细说明
3. `docs/API_REFERENCE.md` - API 参考文档

### 安全与部署
- `docs/SECURITY.md` - 安全设计和防护机制
- `docs/DEPLOYMENT.md` - 生产环境部署指南

### 开发指南
- `docs/DEVELOPMENT.md` - 开发环境配置和贡献指南

### 功能特性
- `docs/V2_ARCHITECTURE.md` - V2 架构详细说明，包含对话历史、工具调用、任务分解等功能
- `docs/API_REFERENCE.md` - 完整的 API 接口文档和使用示例

### 安全特性
- `docs/SECURITY.md` - 多层安全防御、Python 执行器、沙箱隔离等安全机制

---

## 🎯 使用场景与最佳实践

### 场景 1：企业知识库问答

**适用**：内部文档检索、规章制度查询、技术文档查找

**推荐配置**：
- 使用 V2 架构（增量式迭代）
- 启用对话历史（多轮问答）
- 启用置信度评估（质量保障）

**示例**：
```bash
# 上传文档到知识库
curl -X POST http://localhost:5004/api/docs/batch-upload/5 \
  -F "files=@安全制度.pdf" \
  -F "files=@操作规程.pdf"

# V2 问答
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "高空作业的安全要求有哪些？",
    "kb_ids": [5],
    "stream": true
  }'
```

### 场景 2：数学计算与数据分析

**适用**：科学计算、统计分析、数据处理

**推荐配置**：
- 使用 HSL 执行器（安全性高）
- 预装 NumPy、Pandas、SymPy 等库
- 启用执行监控和审计

**示例**：
```bash
# V2 问答 + Python 代码执行
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "计算1到100的平方和，并求平均值",
    "stream": false
  }'
```

### 场景 3：实时信息查询

**适用**：天气查询、新闻检索、股价查询

**推荐配置**：
- 启用网络搜索工具
- 限制搜索次数（避免滥用）
- 结合知识库和实时搜索

**示例**：
```bash
# 实时信息查询
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "今天北京的天气怎么样？明天会下雨吗？",
    "stream": true
  }'
```

### 场景 4：复杂多任务处理

**适用**：多步骤查询、多角度分析、跨领域问题

**推荐配置**：
- 使用 V2 架构（自动任务分解）
- 启用完整性检查
- 合理设置工具调用上限

**示例**：
```bash
# 多任务查询
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "计算100的阶乘，查询今天广州的天气，并告诉我高空作业的注意事项",
    "kb_ids": [5],
    "stream": true
  }'
```

---

## 🔍 常见问题与解决方案

### Q1: 如何切换执行器类型？

**A**: 在启动前设置环境变量
```bash
# 使用 HSL 执行器（推荐）
export PYTHON_EXECUTOR_TYPE=process_isolated
python app.py

# 使用默认执行器
export PYTHON_EXECUTOR_TYPE=default
python app.py
```

### Q2: 如何查看 IO 日志？

**A**: 日志文件位于 `logs/api_io_*.jsonl`
```bash
# 查看原始日志
cat logs/api_io_20251012_*.jsonl | jq .

# 分析日志
python scripts/analyze_io_log.py logs/api_io_20251012_*.jsonl

# 查看日志统计
curl http://localhost:5004/api/io-logs
```

### Q3: 如何禁用 IO 日志？

**A**: 设置环境变量
```bash
export ENABLE_IO_LOGGING=false
python app.py
```

### Q4: 向量检索效果不佳怎么办？

**A**: 
1. 检查文档分块大小（`CHUNK_SIZE`）
2. 调整检索数量（`INITIAL_RETRIEVAL_TOP_K`）
3. 优化查询关键词
4. 使用重排模型（默认已启用）

### Q5: 如何添加自定义工具？

**A**: 参考 `app/services/tools.py`
```python
@tool_registry.register(
    name="custom_tool",
    description="自定义工具描述",
    required_params=["query"]
)
def custom_tool(query: str, **kwargs):
    # 工具实现
    result = do_something(query)
    return {
        'summary': '结果摘要',
        'data': result
    }
```

### Q6: API Key 安全管理？

**A**: 
1. 不要在代码中硬编码 API Key
2. 使用环境变量：复制 `.env.example` 并创建 `.env` 文件
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```
3. `.env` 文件已在 `.gitignore` 中，不会被提交到 Git 仓库
4. 系统会自动从 `.env` 文件加载环境变量

### Q7: 如何调试 V2 Agent？

**A**: 使用调试追踪工具
```bash
# 启用详细日志
export DISPATCHER_LOG_LEVEL=DEBUG
python app.py

# 使用追踪脚本
python scripts/trace_v2_agent_io.py
```

---

## 🚧 已知限制与改进计划

### 当前限制

1. **文件大小限制**：单文件最大 16MB（可在 `config.py` 中修改 `MAX_FILE_SIZE`）
2. **工具调用次数限制**：
   - 知识库检索最多 10 次
   - 网络搜索最多 3 次
   - Python 代码执行最多 10 次
3. **执行器内存**：HSL 执行器默认限制 256MB（可配置 `PYTHON_EXECUTOR_MAX_MEMORY_MB`）
4. **执行超时**：Python 代码执行默认 10 秒超时（可配置）

### 改进计划

- [ ] 支持跨知识库联合检索
- [ ] 支持图片和表格识别（多模态）
- [ ] 支持自定义 Rerank 模型训练
- [ ] 支持分布式向量存储（Milvus）
- [ ] 支持更多执行语言（JavaScript、R等）
- [ ] 支持 Agent 工具插件系统
- [ ] 支持用户权限与审计日志

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 提交 Issue

- 使用清晰的标题
- 提供复现步骤
- 附上日志和截图
- 说明预期行为和实际行为

### 提交 Pull Request

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

### 代码规范

**Python 编码规范**：
- 遵循 PEP 8 编码风格，使用 4 空格缩进
- 类名使用 `CamelCase`，函数名使用 `snake_case`
- 函数和类都要有文档字符串（Docstring）
- 注释长度不超过 79 字符

**项目特定规范**：
- 新增功能必须添加到对应的服务类中
- API 路由必须添加 try-except 异常处理
- 配置参数统一放在 `config.py` 中
- 日志使用标准输出或 `io_logger` 系统

**提交要求**：
- 编写清晰的 commit message，格式：`feat/fix/docs: 简要描述`
- 每个 commit 只关注一个功能或修复
- 编写单元测试（覆盖率不低于 80%）
- 提交前运行 `pip install flake8` 检查代码质量
- 更新相关文档和 README

### 文档贡献

- 修正错误
- 完善示例
- 翻译文档
- 添加最佳实践

---

## 📄 许可证与维护

- **许可证**：MIT License
- **项目名称**：ReAct-Agent
- **版本**：v1.0 (当前)
- **最后更新**：2025年11月2日

### 联系方式

- 提交 Issue：[GitHub Issues](https://github.com/CaiZhexi/Open_ReAct_Agent/issues)
- 项目主页：[GitHub Repository](https://github.com/CaiZhexi/Open_ReAct_Agent)

---

## 🌟 致谢

感谢以下开源项目和服务提供商：

- **框架与库**：Flask, Faiss, NumPy, Pandas, SymPy, Matplotlib, Plotly
- **模型服务**：阿里云百炼、SiliconFlow、Metaso
- **开发工具**：Python, Git, VS Code, Cursor

特别感谢所有贡献者和使用者的支持！

---

**Happy Coding! 🎉**
