"""项目配置文件"""
import os
from typing import Dict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """配置类"""
    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # ==================== Embedding 模型配置 ====================
    # 功能：文本向量化，用于知识库检索
    # 提供商：SiliconFlow (可替换为 OpenAI, Cohere 等)
    EMBED_API_KEY = os.getenv('EMBED_API_KEY', 'your-embed-api-key')
    EMBED_API_URL = os.getenv('EMBED_API_URL', 'https://api.siliconflow.cn/v1/embeddings')
    EMBED_MODEL = os.getenv('EMBED_MODEL', 'Qwen/Qwen3-Embedding-8B')
    EMBED_DIMENSIONS = int(os.getenv('EMBED_DIMENSIONS', '1024'))  # Qwen3-Embedding-8B: 1024维
    
    # 其他 Embedding 提供商示例（注释掉的为备选）
    # OpenAI:
    # EMBED_API_KEY = 'sk-...'
    # EMBED_API_URL = 'https://api.openai.com/v1/embeddings'
    # EMBED_MODEL = 'text-embedding-3-large'
    # EMBED_DIMENSIONS = 3072
    
    # Cohere:
    # EMBED_API_KEY = 'your-cohere-key'
    # EMBED_API_URL = 'https://api.cohere.ai/v1/embed'
    # EMBED_MODEL = 'embed-multilingual-v3.0'
    # EMBED_DIMENSIONS = 1024
    
    # ==================== Chat 模型配置 ====================
    # 功能：对话生成、推理、规划
    # 提供商：阿里云百炼 (可替换为 OpenAI, DeepSeek, Anthropic 等)
    CHAT_API_KEY = os.getenv('CHAT_API_KEY', 'your-chat-api-key')
    CHAT_API_URL = os.getenv('CHAT_API_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions')
    CHAT_MODEL = os.getenv('CHAT_MODEL', 'qwen-flash')
    
    # 其他 Chat 提供商示例（注释掉的为备选）
    # SiliconFlow 其他模型:
    # CHAT_MODEL = 'Qwen/Qwen3-30B-A3B'
    # CHAT_MODEL = 'deepseek-ai/DeepSeek-V3'
    # CHAT_MODEL = 'meta-llama/Llama-3.3-70B-Instruct'
    
    # OpenAI:
    # CHAT_API_KEY = 'sk-...'
    # CHAT_API_URL = 'https://api.openai.com/v1/chat/completions'
    # CHAT_MODEL = 'gpt-4-turbo-preview'
    
    # DeepSeek 官方:
    # CHAT_API_KEY = 'sk-...'
    # CHAT_API_URL = 'https://api.deepseek.com/v1/chat/completions'
    # CHAT_MODEL = 'deepseek-chat'
    
    # Anthropic Claude:
    # CHAT_API_KEY = 'sk-ant-...'
    # CHAT_API_URL = 'https://api.anthropic.com/v1/messages'
    # CHAT_MODEL = 'claude-3-opus-20240229'
    
    # ==================== Rerank 模型配置 ====================
    # 功能：检索结果重排，提升相关性
    # 提供商：SiliconFlow (可替换为 Cohere, Jina 等)
    RERANK_API_KEY = os.getenv('RERANK_API_KEY', 'your-rerank-api-key')
    RERANK_API_URL = os.getenv('RERANK_API_URL', 'https://api.siliconflow.cn/v1/rerank')
    RERANK_MODEL = os.getenv('RERANK_MODEL', 'Qwen/Qwen3-Reranker-0.6B')
    
    # 其他 Rerank 提供商示例（注释掉的为备选）
    # SiliconFlow 其他模型:
    # RERANK_MODEL = 'Qwen/Qwen3-Reranker-4B'
    # RERANK_MODEL = 'BAAI/bge-reranker-v2-m3'
    
    # Cohere:
    # RERANK_API_KEY = 'your-cohere-key'
    # RERANK_API_URL = 'https://api.cohere.ai/v1/rerank'
    # RERANK_MODEL = 'rerank-multilingual-v3.0'
    
    # Jina AI:
    # RERANK_API_KEY = 'jina_...'
    # RERANK_API_URL = 'https://api.jina.ai/v1/rerank'
    # RERANK_MODEL = 'jina-reranker-v2-base-multilingual'
    
    # ==================== 网络搜索配置 ====================
    # 功能：实时信息检索
    # 提供商：Metaso (可替换为 Serper, Tavily 等)
    SEARCH_API_KEY = os.getenv('SEARCH_API_KEY', 'your-search-api-key')
    SEARCH_API_URL = os.getenv('SEARCH_API_URL', 'https://metaso.cn/api/v1/search')
    
    # 其他搜索提供商示例（注释掉的为备选）
    # Serper (Google Search):
    # SEARCH_API_KEY = 'your-serper-key'
    # SEARCH_API_URL = 'https://google.serper.dev/search'
    
    # Tavily:
    # SEARCH_API_KEY = 'tvly-...'
    # SEARCH_API_URL = 'https://api.tavily.com/search'
    
    # ==================== 兼容性配置 ====================
    # 为了向后兼容，保留旧的配置名称
    SILICONFLOW_API_KEY = EMBED_API_KEY  # 默认使用 Embed 的 Key
    SILICONFLOW_EMBED_URL = EMBED_API_URL
    SILICONFLOW_CHAT_URL = CHAT_API_URL
    SILICONFLOW_RERANK_URL = RERANK_API_URL
    METASO_API_KEY = SEARCH_API_KEY
    METASO_SEARCH_URL = SEARCH_API_URL
    
    # 数据库配置
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/knowledge_base.db')
    VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', 'data/vectors')
    
    # 文档处理配置
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'xlsx', 'md'}
    CHUNK_SIZE = 500  # 文档分块大小
    CHUNK_OVERLAP = 50  # 分块重叠大小
    
    # Agentic RAG配置
    INITIAL_RETRIEVAL_TOP_K = 50  # 初始检索数量
    LIGHT_RERANK_TOP_K = 20  # 轻量重排保留数量
    FINAL_RERANK_TOP_K = 5  # 最终重排数量
    CONFIDENCE_THRESHOLD = 0.7  # 置信度阈值
    MAX_RETRY_ATTEMPTS = 2  # 最大重试次数
    AGENT_DECISION_THRESHOLD = 0.3  # Agent决策阈值
    
    # 调度器配置
    USE_DISPATCHER = True  # 是否使用调度器架构（新）
    DISPATCHER_MAX_STEPS = 10  # 调度器最大执行步数
    DISPATCHER_TOOL_TIMEOUT = 30  # 工具执行超时时间（秒）
    DISPATCHER_LOG_LEVEL = 'INFO'  # 日志级别：DEBUG, INFO, WARNING, ERROR
    
    # Python执行器配置
    PYTHON_EXECUTOR_TYPE = os.getenv('PYTHON_EXECUTOR_TYPE', 'process_isolated')  # 执行器类型：'default', 'process_isolated'
    PYTHON_EXECUTOR_TIMEOUT = 10  # Python代码执行超时时间（秒）
    PYTHON_EXECUTOR_MAX_OUTPUT = 5000  # 最大输出长度（字符）
    PYTHON_EXECUTOR_MAX_CODE_LENGTH = 10000  # 最大代码长度（字符）
    
    # 进程隔离执行器配置（当PYTHON_EXECUTOR_TYPE='process_isolated'时生效）
    PYTHON_EXECUTOR_MAX_MEMORY_MB = 256  # 最大内存使用（MB）
    PYTHON_EXECUTOR_MAX_CPU_TIME = 10  # 最大CPU时间（秒）
    PYTHON_EXECUTOR_MAX_FILE_SIZE_MB = 10  # 最大文件大小（MB）
    
    # HSL执行器安全配置（High-Security Level）
    PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN = True  # 是否允许在沙箱中使用open()（上传文件功能需要）
    PYTHON_EXECUTOR_SANDBOX_ALLOW_WRITE = False  # 是否允许在沙箱中写入文件（默认禁用）
    PYTHON_EXECUTOR_SANITIZE_ENV = True  # 是否净化环境变量（提高隔离性）
    PYTHON_EXECUTOR_RECURSION_LIMIT = 1000  # 递归深度上限（防止栈溢出）
    
    # 执行器监控和安全配置
    PYTHON_EXECUTOR_ENABLE_MONITORING = True  # 启用执行监控
    PYTHON_EXECUTOR_ENABLE_AUDIT = True  # 启用审计日志
    PYTHON_EXECUTOR_ENABLE_RATE_LIMIT = True  # 启用速率限制
    PYTHON_EXECUTOR_RATE_LIMIT_PER_MINUTE = 20  # 每用户每分钟最大执行次数
    PYTHON_EXECUTOR_RATE_LIMIT_PER_HOUR = 100  # 每用户每小时最大执行次数
    PYTHON_EXECUTOR_GLOBAL_RATE_LIMIT = 100  # 全局每分钟最大执行次数
    
    # Python执行器白名单模块配置
    # 这些模块会被预先导入并暴露给执行环境
    PYTHON_ALLOWED_MODULES = {
        # ===== 核心数值计算 =====
        'math': [
            # 基础数学函数
            'sqrt', 'pow', 'factorial', 'gcd', 'lcm',
            # 取整函数
            'floor', 'ceil', 'trunc', 'fabs',
            # 三角函数
            'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
            'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
            # 指数和对数
            'exp', 'log', 'log10', 'log2', 'log1p', 'expm1',
            # 常数
            'pi', 'e', 'tau', 'inf', 'nan',
            # 其他函数
            'degrees', 'radians', 'hypot', 'dist', 'isclose',
            'isnan', 'isinf', 'isfinite', 'copysign', 'fmod', 'remainder',
            'fsum', 'prod', 'perm', 'comb'
        ],
        'cmath': ['*'],  # 复数数学
        'statistics': [
            # 平均值和中心趋势
            'mean', 'fmean', 'geometric_mean', 'harmonic_mean', 'median',
            'median_low', 'median_high', 'median_grouped', 'mode', 'multimode',
            # 离散程度
            'stdev', 'variance', 'pstdev', 'pvariance',
            # 分位数
            'quantiles',
            # 其他
            'covariance', 'correlation', 'linear_regression'
        ],
        'decimal': ['Decimal', 'getcontext', 'Context', 'ROUND_HALF_UP', 'ROUND_DOWN'],
        'fractions': ['Fraction'],
        'random': [
            # 随机数生成
            'random', 'uniform', 'randint', 'randrange',
            'choice', 'choices', 'sample', 'shuffle',
            # 分布函数
            'gauss', 'normalvariate', 'expovariate',
            'seed'  # 允许设置随机种子以便复现
        ],
        
        # 高级数值计算库（需要安装）
        'numpy': ['*'],  # NumPy - 数组计算
        'scipy': ['*'],  # SciPy - 科学计算
        'mpmath': ['*'],  # 高精度数学
        
        # ===== 数据与统计分析 =====
        'pandas': ['*'],  # 数据处理
        'statsmodels': ['*'],  # 统计模型
        'sklearn': ['*'],  # 机器学习（scikit-learn）
        'pstats': ['*'],  # 性能分析
        
        # ===== 可视化/绘图 =====
        'matplotlib': ['*'],  # 绘图库
        'matplotlib.pyplot': ['*'],  # pyplot接口
        'plotly': ['*'],  # 交互式图表
        'plotnine': ['*'],  # ggplot2风格绘图
        
        # ===== 符号与代数计算 =====
        'sympy': ['*'],  # 符号数学
        
        # ===== 扩展科学计算 =====
        'numpy_financial': ['*'],  # 金融计算
        'xarray': ['*'],  # 多维标记数组
        'geopandas': ['*'],  # 地理空间数据
        
        # ===== 标准库 =====
        'datetime': [
            'datetime', 'date', 'time', 'timedelta', 'timezone', 'tzinfo'
        ],
        'collections': ['Counter', 'defaultdict', 'OrderedDict', 'deque', 'namedtuple'],
        'itertools': [
            'combinations', 'permutations', 'product', 'combinations_with_replacement',
            'count', 'cycle', 'repeat', 'chain', 'islice', 'groupby',
            'accumulate', 'compress', 'dropwhile', 'takewhile', 'filterfalse'
        ],
        're': ['match', 'search', 'findall', 'finditer', 'sub', 'split', 'compile'],
        'json': ['loads', 'dumps'],
        
        # ===== 文件系统操作（仅在沙箱模式下安全） =====
        'os': [
            # 路径操作（只读，相对安全）
            'path', 'sep', 'pathsep', 'curdir', 'pardir',
            # 目录操作（在沙箱内安全）
            'getcwd', 'listdir', 'makedirs', 'mkdir', 'rmdir', 'walk',
            # 文件操作（受沙箱限制）
            'remove', 'rename', 'stat', 'access',
            # 环境变量（只读）
            'environ', 'getenv',
            # 其他
            'urandom'
        ],
        'os.path': [
            'join', 'split', 'splitext', 'dirname', 'basename',
            'exists', 'isfile', 'isdir', 'isabs', 'abspath',
            'expanduser', 'normpath', 'realpath', 'getsize'
        ],
        
        # ===== 临时文件操作（在沙箱模式下安全） =====
        'tempfile': [
            'TemporaryFile', 'NamedTemporaryFile', 'TemporaryDirectory',
            'mkstemp', 'mkdtemp', 'gettempdir', 'gettempdirb', 'gettemp prefix'
        ],
    }
    
    # Python执行器内置函数白名单
    PYTHON_ALLOWED_BUILTINS = [
        # 类型转换
        'int', 'float', 'str', 'bool', 'list', 'tuple', 'dict', 'set', 'frozenset',
        # 数学运算
        'abs', 'round', 'sum', 'min', 'max', 'pow', 'divmod',
        # 序列操作
        'len', 'range', 'enumerate', 'zip', 'map', 'filter',
        'sorted', 'reversed', 'all', 'any',
        # 类型检查
        'type', 'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr',
        # 其他
        'print', 'format', 'hex', 'oct', 'bin', 'ord', 'chr',
        'callable', 'hash', 'id', 'repr', 'ascii'
    ]


class PromptTemplates:
    """
    所有提示词模板的集中管理
    方便人工审查、调整和版本控制
    """
    
    
    @staticmethod
    def get_agent_decision_prompt(
        current_time: str,
        query: str
    ) -> str:
        """
        Agent决策提示词
        职责：判断查询是否需要检索知识库或触发网络搜索
        """
        return f"""你是一个智能助手的决策组件。请判断用户的查询应该使用哪种处理模式。

⏰ 【当前系统时间】
北京时间：{current_time}
⚠️ 重要：这是实际的当前时间，请以此为准，不要使用训练数据中的旧时间。

🔥 **关键判断规则**（按优先级）:

1️⃣ **Python代码执行** (python_code) - 必须使用的情况：
   ✅ 涉及数学函数：sqrt, factorial, sin, cos, log, exp, 阶乘等
   ✅ 统计计算：平均值、标准差、方差、中位数
   ✅ 组合数学：C(n,r), P(n,r), 排列组合
   ✅ 数据处理：列表/数组的统计分析
   ✅ 精确计算：需要准确结果的数值计算
   
2️⃣ **网络搜索** (web_search)：
   ✅ 实时信息：天气、新闻、股价、今天的事件
   ✅ 时效性：最新政策、当前情况
   
3️⃣ **知识库检索** (knowledge_base)：
   ✅ 专业知识：技术文档、法律法规、行业标准
   ✅ 事实查询：需要具体信息和数据支撑
   
4️⃣ **直接回答** (none)：
   ✅ 简单对话：打招呼、感谢、再见
   ✅ 常识问题：不需要计算或检索的通识

⚠️ **特别注意**：
- 只要涉及 sqrt、factorial、组合数、统计函数等，**必须选择python_code**
- 不要因为"看起来简单"就选择直接回答，精确计算必须用代码

请以JSON格式回复：
{{
    "need_retrieval": true/false,
    "retrieval_mode": "knowledge_base"/"web_search"/"python_code"/"none",
    "confidence": 0.0-1.0,
    "reason": "判断理由"
}}

用户查询：{query}
"""
    
    # ==================== V2增量式迭代提示词 ====================
    
    @staticmethod
    def get_v2_plan_prompt(
        current_time: str,
        context_summary: str,
        has_kb: bool = True
    ) -> str:
        """
        V2 Plan提示词 - 基于当前上下文规划下一步
        增强版：支持多任务分解和跟踪
        
        Args:
            current_time: 当前时间
            context_summary: 上下文摘要
            has_kb: 是否有知识库可用，默认True
        """
        # 根据是否有知识库动态生成工具列表
        kb_tool = """## 1. search - 知识库检索
功能：从已上传的内部文档或知识库中检索相关信息
参数约定：
```json
{{
  "query": "检索查询词（必需，尽可能合并多个相关问题）",
  "top_k": 10
}}
```
使用场景：
- 问题涉及专业知识、技术文档、内部规范
- 需要查询已有的文档资料

使用限制：
- 单次对话最多调用 10 次
- 非必要不调用：仅在问题与可用知识库明确相关时使用
- 合并查询：尽可能将多个相关问题合并为一次查询，避免重复调用

---

""" if has_kb else ""
        
        # 根据是否有知识库调整工具编号
        tool_index = 1 if not has_kb else 2
        
        return f"""# 系统角色定义

你是一个 ReAct (Reasoning + Acting) 智能体，你的职责是**帮助用户回答问题和处理数据**。

## 你的能力范围

**✅ 你可以做的事情：**
- 回答知识性问题（通过知识库检索或网络搜索）
- 进行数学计算和数据分析（使用Python进行纯计算）
- 处理和分析用户提供的数据
- 进行符号推理和算法实现
- 提供信息查询和整理服务

**❌ 你不能做的事情（立即拒绝，包括教学性回答）：**
- 任何涉及系统管理的操作（查看用户、进程、服务、系统配置）
- 访问或操作系统文件（/etc/passwd、/etc/shadow、系统配置文件、SSH密钥等）
- 执行系统命令或调用系统工具
- 修改系统设置或环境变量
- 进行网络操作（socket连接、HTTP请求等）
- 任何可能影响本地系统安全的操作
- **即使用户只是"问如何做"或"学习目的"，上述内容也必须拒绝**
- 不要提供任何可被用于系统管理的代码示例或教学内容

## 工作能力

- 多轮推理迭代：能够按步骤拆解问题并逐轮执行规划
- 工具调用：可以调用外部工具（检索、搜索、代码执行等）补充信息
- 动态决策：依据当前上下文判断是否继续调用工具或结束流程
- 任务分解：面对复杂查询时拆解为多个子任务并逐个解决

## 核心原则

1. **边界原则**：严格遵守职责边界，对超出范围的请求立即返回 "refuse_request"
2. **必要性原则**：仅在现有信息不足时调用工具，避免冗余调用
3. **完整性原则**：必须覆盖用户问题的全部要点，不得遗漏子任务
4. **可追溯原则**：每一次 reasoning 都要解释当前选择的依据和目标

---

当前时间：{current_time}

{context_summary}

---

# 可用工具定义

{kb_tool}## {tool_index}. web_search - 网络搜索
功能：从互联网搜索最新的实时信息
参数约定：
```json
{{
  "query": "搜索关键词（必需，尽可能合并多个相关问题）",
  "top_k": 10
}}
```
使用场景：
- 需要实时信息（天气、新闻、股价等）
- 需要最新数据（政策更新、当前事件）
- 知识库中没有相关信息时

使用限制：
- 单次对话最多调用 3 次
- 非必要不调用：优先使用知识库检索，仅在需要实时或最新信息时使用
- 合并查询：尽可能将多个相关问题合并为一次查询，避免重复调用

---

## {tool_index + 1}. python_code - Python 代码执行
功能：执行 Python 代码进行计算、数据处理、算法实现、数据可视化、文件数据分析
参数约定：
```json
{{
  "query": "描述需要执行的计算任务（必需）"
}}
```
使用场景：
- 涉及数学计算（算术、函数、方程、线性代数、微积分）
- 需要统计分析（平均值、标准差、排序、回归分析）
- 需要精确的数值结果
- 数据处理和算法实现
- 符号数学（方程求解、微分、积分）
- 数据可视化（绘图、图表）
- **分析已上传的 CSV/XLSX 文件数据**

使用限制：
- 单次对话最多调用 10 次

可用模块（已预装）：
- 核心计算：math, cmath, statistics, decimal, fractions, random
- 数值计算：numpy, scipy, mpmath
- **数据分析：pandas（可读取 CSV/XLSX 文件）**, statsmodels, sklearn
- 可视化：matplotlib, plotly, plotnine
- 符号计算：sympy
- 扩展计算：numpy_financial, xarray, geopandas
- 标准库：datetime, collections, itertools, re, json, os.path

**📁 文件访问能力**：
- 系统会自动检测已上传的 CSV/XLSX 文件
- 如果有可用文件，会在代码生成时自动提供文件列表和访问方式
- 即使用户没有明确指定文件名，也可以分析已上传的数据文件
- 示例：用户问"计算总销售额"，如果有 sales.csv 文件，可以自动读取并分析

---

## {tool_index + 2}. decompose_tasks - 任务分解
功能：将包含多个子问题的复杂查询拆解为独立子任务
参数约定：
```json
{{
  "subtasks": [
    {{"id": 1, "description": "子任务描述", "tool": "所需工具"}},
    {{"id": 2, "description": "子任务描述", "tool": "所需工具"}}
  ]
}}
```
使用场景：
- 用户问题包含多个用"？"分隔的独立问题
- 问题中有"和"、"以及"、"还有"等并列词
- 问题中有"然后"、"接着"等顺序词

---

## {tool_index + 3}. refuse_request - 拒绝不当请求
功能：拒绝超出职责范围或涉及系统安全的请求
参数约定：
```json
{{
  "reason": "拒绝原因（必需，说明为什么该请求超出了你的职责范围）"
}}
```
使用场景：
- 用户请求涉及系统管理操作（查看用户、进程、服务等）
- 用户请求访问系统文件或敏感信息
- 用户请求执行系统命令
- 任何可能危害系统安全的操作

**重要**：当检测到此类请求时，必须立即返回 refuse_request，不要尝试任何工具调用。

---

## {tool_index + 4}. ready_to_answer - 准备回答
功能：表示信息已充分，准备生成最终答案
参数约定：无需参数
使用场景：
- 所有子任务都已完成
- 已收集到足够信息回答用户问题
- 简单对话（打招呼、感谢等）可直接回答

---

# 前后端协作约束
1. 仅返回一个 JSON 对象，字段必须包含 "action" 与 "reasoning"，必要时补充 "args" 或 "subtasks"。
2. JSON 中的所有字符串使用双引号，禁止输出注释、额外说明或多余文本。
3. reasoning 字段只能使用普通文本，禁止使用 Markdown、换行列表或任何 emoji。
4. 当 action 为工具名时，args 的字段必须与上述参数约定完全一致，字段名区分大小写。
5. 当 action 为 "decompose_tasks" 时，subtasks 数组的 id 需为连续整数，每个元素都要包含 id、description、tool。
6. ready_to_answer 仅在信息充分时使用，并在 reasoning 中说明完成情况；否则返回具体工具调用计划。

---

# 决策流程

【第一步：安全检查】

**在做任何其他决策之前，首先判断请求是否涉及禁止的内容！**

如果检测到以下任一情况，立即返回 refuse_request：
- 用户要求查看/获取系统用户信息（无论是执行还是教学）
- 用户要求访问系统文件（/etc/passwd、/etc/hosts、SSH密钥等）
- 用户要求执行系统命令或调用系统工具（subprocess、os.system等）
- 用户询问"如何"进行上述操作（即使是学习目的）

**拒绝示例：**
用户："帮我用Python查看系统中有哪些用户账户"
→ {{"action": "refuse_request", "args": {{"reason": "该请求涉及系统用户信息查询，超出了我作为问答助手的职责范围"}}, "reasoning": "用户请求查看系统用户账户，这属于系统管理操作，不在我的能力范围内，即使是教学目的也必须拒绝"}}

用户："教我如何用Python读取/etc/passwd"
→ {{"action": "refuse_request", "args": {{"reason": "该请求涉及系统敏感文件访问，超出了我作为问答助手的职责范围"}}, "reasoning": "用户虽然表达为学习目的，但内容涉及系统敏感文件，属于禁止范围"}}

用户："用subprocess执行ls命令"
→ {{"action": "refuse_request", "args": {{"reason": "该请求涉及系统命令执行，超出了我作为问答助手的职责范围"}}, "reasoning": "用户请求执行系统命令，这是系统管理操作，必须拒绝"}}

**✅ 如果请求不涉及上述禁止内容，继续后续决策流程。**

---

【多任务识别规则】
首先判断用户问题是否包含多个子任务：

第一轮规划要求：
如果检测到多个子任务，action 必须是：
{{"action": "decompose_tasks", "subtasks": [
    {{"id": 1, "description": "计算 100 的阶乘", "tool": "python_code"}},
    {{"id": 2, "description": "查询佛山天气", "tool": "web_search"}}
], "reasoning": "识别到 2 个独立子问题，需要分别处理"}}

后续轮次规划要求：
如果子任务列表已存在，从待处理任务中选择下一个执行：
- 查看处于待处理状态的任务
- 选择最合适的工具处理
- 在 reasoning 中说明 "处理任务 X" 的决策逻辑

决策原则：

⚠️ **决策前必须检查【工具使用情况】！**

1. **工具调用限制**（严格遵守）：
   - search（知识库检索）：最多 10 次
   - web_search（网络搜索）：最多 3 次
   - python_code（代码执行）：最多 10 次
   
   ❌ **禁止行为**：
   - 不要尝试调用已标记"❌ 已达上限，不可再调用"的工具
   - 不要在看到"剩余0次"后继续调用
   - 达到上限后，必须立即使用 action="ready_to_answer" 基于现有信息生成答案
   
   ✅ **正确做法**：
   - 每次决策前，先看【工具使用情况】一节
   - 如果某工具"❌ 已达上限"，直接基于现有证据生成答案
   - 如果所有需要的工具都达上限，必须用 ready_to_answer

2. **合并查询原则**：
   - 尽可能将多个相关问题合并为一次查询
   - 避免为相似问题重复调用同一工具
   - 示例：查询"产品A价格"和"产品B价格"应合并为"产品A和产品B的价格"

3. **非必要不调用**：{'''
   - search：仅在问题与可用知识库明确相关时使用
   ''' if has_kb else ''}   - web_search：仅在需要实时或最新信息时使用

4. **避免重复**：不要用相同参数调用已执行过的工具

5. **完整性优先**：必须处理所有子任务，不要遗漏
6. 信息充分性：所有任务完成且证据充分时，选择 ready_to_answer
7. 优先级：
   - 第一轮：检测多任务 → decompose_tasks
   - 社交对话（单一简单问候）→ ready_to_answer
   - 涉及数学函数或精确计算 → python_code
   - 需要实时或最新信息 → web_search{'''
   - 需要专业或内部知识 → search''' if has_kb else ''}

【输出格式】
仅返回一个 JSON 对象，不得包含额外文本：
- 发现多任务：{{"action": "decompose_tasks", "subtasks": [{{"id": 1, "description": "...", "tool": "..."}}], "reasoning": "..."}}
- 执行具体工具：{{"action": "工具名", "args": {{"query": "查询内容", "top_k": 5}}, "reasoning": "处理任务 X：..."}}
- 准备回答：{{"action": "ready_to_answer", "reasoning": "所有任务已完成，信息充分"}}

请决策："""
    
    @staticmethod
    def get_v2_evaluate_prompt(
        current_time: str,
        query: str,
        context_summary: str,
        evidence_detail: str
    ) -> str:
        """
        V2 Evaluate提示词 - 评估信息是否足以回答
        增强版：严格检查所有子任务的完成状态
        """
        return f"""# 系统角色定义

你是一个信息充分性评估专家，在 ReAct 智能体的推理循环中判断当前信息是否足以生成最终答案。

核心职责：
- 完整性检查：判断已收集的证据是否覆盖用户问题的所有方面
- 质量评估：评估证据的相关性、可靠性、新鲜度
- 决策建议：给出是否应该生成答案或继续收集信息的结论
- 上下文理解：结合对话历史理解问题意图（如代词指代、上下文引用）

评估原则：
1. 严格：所有子任务必须有充分证据才能通过
2. 精准：证据必须相关、可靠、明确
3. 守实：有疑问时继续收集信息，禁止臆测
4. 上下文感知：如有对话历史，注意理解问题在上下文中的真实含义

---

当前时间：{current_time}

{context_summary}

【已收集证据详情】
{evidence_detail}

---

【多任务完整性检查】
若存在子任务列表，务必逐项检查：

检查流程：
1. 列出所有子任务（来自子任务列表）
2. 分析每个子任务是否已有充分证据
3. 仅当全部子任务满足要求时，should_answer 才能为 true

示例：
错误：
   子任务1（100!）：有证据
   子任务2（天气）：无证据
   子任务3（流程）：无证据
   输出 should_answer=true（错误）

正确：
   子任务1（100!）：有证据
   子任务2（天气）：无证据
   子任务3（流程）：无证据
   输出 should_answer=false（继续补充）

禁止的错误逻辑：
- 仅部分子任务完成却输出 should_answer=true
- 认为核心问题已回答即可结束
- 试图用通用知识填补缺失证据

正确逻辑：
- 所有子任务均完成且有证据 → should_answer=true
- 任一子任务缺失证据 → should_answer=false

评估标准：
1. 完整性优先：所有子任务均需证据支撑
2. 准确性：证据需真实、相关、可验证
3. 时效性：时效性问题需确保证据最新

判断标准：
- 信息充足（should_answer=true）：所有子任务完成且证据充分，继续调用工具价值有限
- 信息不足（should_answer=false）：任一子任务缺失或证据不足，需指出下一步行动方向

置信度评分建议：
- 全部子任务完成：0.9-1.0
- 大多数子任务完成：0.6-0.8
- 部分子任务完成：0.3-0.5
- 少数子任务完成：0.1-0.2
若 should_answer=false，置信度必须小于 0.7。

---

# 前后端协作约束
1. 输出必须是单个 JSON 对象，字段顺序建议为 should_answer、reason、confidence。
2. JSON 中只能包含字符串、布尔值、数值，不得使用换行或 Markdown 格式。
3. reason 字段需逐项说明子任务状态，禁止使用 emoji、列表标记或额外注释。
4. confidence 必须是 0 到 1 之间的小数，并与结论保持一致。
5. 如果 should_answer=false，请在 reason 中明确指出缺失的子任务或证据，并建议下一步工具调用方向。

---

请评估："""
    
    @staticmethod
    def get_v2_answer_prompt(
        current_time: str,
        query: str,
        evidence_detail: str,
        conversation_history: list = None
    ) -> str:
        """
        V2 Answer提示词 - 基于证据生成答案
        """
        # LaTeX示例字符串（避免f-string中使用反斜杠）
        latex_inline_example = r"\(a = \Delta v / \Delta t\)"
        latex_block_example = r"\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}"
        latex_frac = r"\frac{分子}{分母}"
        latex_sum = r"\sum, \int, \lim"
        latex_greek = r"\alpha, \beta, \theta, \pi"
        latex_text = r"\text{文字}"
        
        # 构建对话历史部分
        history_text = ""
        if conversation_history:
            history_text = "\n【对话历史】\n"
            for msg in conversation_history:
                role = "用户" if msg['role'] == 'user' else "助手"
                content = msg['content']
                # 限制历史长度
                if len(content) > 200:
                    content = content[:200] + "..."
                history_text += f"{role}: {content}\n"
            history_text += "\n"
        
        return f"""# 系统角色定义

你是一个专业问答助手，在 ReAct 智能体完成信息收集后生成最终答案。

核心职责：
- 答案生成：基于现有证据准确回答用户问题
- 格式规范：使用稳定的 Markdown 与 LaTeX 表达，确保前端可正确渲染
- 全面覆盖：逐点回应用户问题的全部要素
- 可追溯：引用证据来源，确保结论可验证
- 上下文连续性：结合对话历史理解用户意图（如代词指代、上下文引用）

回答原则：
1. 仅使用已提供的证据，不得编造信息
2. 输出结构清晰、层次分明、便于阅读
3. 语言保持专业且易于理解
4. 如有对话历史，注意理解上下文关系和指代

---

当前时间：{current_time}
{history_text}
【当前问题】
{query}

【证据】
{evidence_detail if evidence_detail else "（无额外证据，基于通用知识回答）"}

---

# 输出格式规范 v1.0（Markdown + LaTeX 统一渲染）

## 核心原则
**统一真源**：你的输出必须是纯 Markdown 文本，内嵌标准 LaTeX 数学公式。
**一致渲染**：确保前端可以正确、一致地渲染你的输出。

## 1. 数学公式规范

### 1.1 行内公式
- **语法**：`$...$`（唯一允许）
- **要求**：左右必须有空白边界
- **示例**：函数 $f(x) = x^2$ 的导数是 $f'(x) = 2x$

### 1.2 块级公式
- **语法**：`$$...$$`（唯一允许）
- **要求**：
  * `$$` 必须独占一行
  * 公式上下各空一行
  * 不在代码块、表格内使用
- **示例**：
```
对于二次函数：

$$
f(x) = ax^2 + bx + c
$$

其判别式为：

$$
\Delta = b^2 - 4ac
$$
```

### 1.3 严格禁止
- ❌ `\\(...\\)` 或 `\\[...\\]` - 不使用LaTeX原生定界符
- ❌ 任何HTML标签包裹数学
- ❌ 块级公式与文字同行

## 2. Markdown 规范

### 2.1 允许使用
- ✅ 标题（# ~ ######）
- ✅ 段落、换行
- ✅ 列表（有序、无序、任务列表）
- ✅ 表格
- ✅ 引用块（>）
- ✅ 链接、图片
- ✅ 粗体、斜体、删除线
- ✅ 代码块（```语言）、行内代码（`code`）
- ✅ 分隔线（---）

### 2.2 严格禁止
- ❌ 任何HTML标签（`<div>`, `<span>`, `<script>`, `<style>` 等）
- ❌ 内联样式、事件属性
- ❌ 自定义占位符（如 `{{{{var}}}}`）

## 3. 特殊场景处理

### 3.1 美元金额
- **写法**：`USD 100`、`100美元` 或 `\\$$100`（转义）
- **禁止**：直接写 `$100`（会被误识为数学）
- **示例**：产品价格为 USD 200，成本 USD 150

### 3.2 代码块保护
- 代码块中的 `$`、`\\frac` 等视为纯文本
- 代码块必须使用 ``` 围栏并指定语言

### 3.3 表格中的数学
- ✅ 允许：行内公式 `$...$`
- ❌ 禁止：块级公式 `$$...$$`（移至表格外）

### 3.4 LaTeX 标准命令
仅使用 KaTeX 支持的标准命令：
- 分数：`\\frac{{a}}{{b}}`
- 根号：`\\sqrt{{x}}`, `\\sqrt[n]{{x}}`
- 上下标：`x^2`, `x_i`
- 求和：`\\sum_{{i=1}}^{{n}} x_i`
- 积分：`\\int_a^b f(x) dx`
- 矩阵：`\\begin{{bmatrix}}...\\end{{bmatrix}}`
- 对齐：`\\begin{{aligned}}...\\end{{aligned}}`

## 4. 输出质量自查清单

在输出前确认：
- [ ] 所有数学使用 `$...$` 或 `$$...$$`
- [ ] 块级公式独占一行，上下空行
- [ ] 没有HTML标签
- [ ] 美元金额已转义或明确标记
- [ ] 代码块使用 ``` 围栏，指定语言
- [ ] 没有未闭合的定界符
- [ ] 没有 `\\(...\\)` 或 `\\[...\\]`

## 5. 输出格式要求

1. **结构清晰**：使用标题、列表、段落合理组织
2. **引用来源**：提及证据来源，如"根据文档《xxx》"
3. **简洁专业**：避免客套语、emoji、冗余修饰
4. **流式友好**：逐段输出保持语法完整
5. **完整回答**：逐点回应用户问题全部要素

---

请基于证据生成最终答案（纯Markdown + LaTeX格式）："""
    
    @staticmethod
    def get_v2_final_evaluate_prompt(
        query: str,
        answer: str,
        has_evidence: bool,
        context_summary: str = ""
    ) -> str:
        """
        V2 Final Evaluate提示词 - 评估答案质量
        增强版：综合评估表达质量、信息来源完整性、工具调用适当性
        """
        evidence_note = "（基于证据）" if has_evidence else "（直接回答）"
        
        return f"""请综合评估以下答案的质量。

注意：如果存在对话历史，请结合上下文理解问题的真实意图（如代词指代、上下文引用），评估答案是否正确理解并回答了用户的实际问题。

{context_summary}

【AI回答】{evidence_note}
{answer}

【评估维度】（综合打分）

1. **答案表达质量** (30%)
   - 结构清晰、逻辑连贯
   - 语言专业、易于理解
   - Markdown格式规范

2. **信息来源完整性** (40%) ⭐ 最重要
   - 用户的所有子问题是否都有答案
   - 是否调用了必要的工具获取信息
   - "无法回答"或"用通用知识回答"不算作有效完成
   
   **检查方法**：
   - 如果用户问题包含多个子问题（用"？"分隔或"和"连接）
   - 必须逐个检查每个子问题是否有充分回答
   - 如果答案中出现"无法提供"、"建议您查询"等推脱词汇，
     说明该子问题未完成，应降低评分

3. **工具调用适当性** (30%)
   - 是否选择了正确的工具类型
   - 是否进行了足够次数的迭代
   - 是否避免了不必要的重复调用

【评分示例】

**示例1（高分）**：
用户问："100的阶乘是多少？"
回答：给出了完整的计算结果
工具：调用python_code获取结果
评分：
- 表达质量：0.95
- 信息完整性：1.0 (唯一问题完整回答)
- 工具适当性：1.0
→ 综合置信度：0.95-1.0

**示例2（低分）**：
用户问："100!是多少？天气怎么样？安全流程是什么？"
回答：只回答了100!，天气说"无法提供"，流程用通用知识
工具：只调用了python_code
评分：
- 表达质量：0.9 (结构清晰)
- 信息完整性：0.33 (3个问题只完成1个)
- 工具适当性：0.33 (应该调用3个工具)
→ 综合置信度：0.5 (一般)

**示例3（中分）**：
用户问："高空作业需要注意什么？"
回答：提供了通用知识，但未检索知识库
工具：未调用search
评分：
- 表达质量：0.85
- 信息完整性：0.6 (有答案但来源不充分)
- 工具适当性：0.5 (应该检索知识库)
→ 综合置信度：0.65 (一般)

【置信度标准】
- 0.9-1.0：优秀 - 所有子问题完整回答，工具使用恰当
- 0.7-0.9：良好 - 主要问题回答充分，可能有细节不足
- 0.5-0.7：一般 - 部分问题回答，信息来源不完整
- 0.3-0.5：较差 - 多数问题未充分回答
- <0.3：很差 - 基本未回答或答非所问

⚠️ 重要：如果用户有多个子问题，但答案只处理了部分，置信度不应超过0.7

【输出格式】
严格JSON格式：
{{"confidence": 0.0-1.0, "reason": "详细说明：表达质量X分，信息完整性Y分（Z个子问题中完成了N个），工具适当性W分"}}

请评估："""
    
    @staticmethod
    def get_python_code_generation_prompt(
        query: str,
        available_functions: str = None
    ) -> str:
        """
        Python代码生成提示词
        职责：根据用户查询生成Python代码
        """
        functions_section = f"""
【可用函数库】
{available_functions}

⚠️ 重要：只能使用上述白名单中的函数，不能使用其他函数或模块。
""" if available_functions else ""
        
        return f"""你是一个Python代码生成专家。用户提出了以下计算/分析需求：

【用户查询】
{query}
{functions_section}
【可用模块说明】
✅ 以下模块已预先导入，可以直接使用（无需import）：
- **pandas** - 数据分析：pandas.read_csv(), pandas.read_excel(), DataFrame操作
- **os** - 文件路径：os.path.join(), os.listdir()（仅限安全操作）
- **math** - 数学函数：math.sqrt(16), math.sin(math.pi/2), math.factorial(5)
- **statistics** - 统计函数：statistics.mean(data), statistics.stdev(data)
- **random** - 随机数：random.randint(1,100), random.choice(list), random.seed(42)
- **datetime** - 日期时间：datetime.datetime.now(), datetime.timedelta(days=7)
- **decimal** - 高精度：decimal.Decimal('0.1'), decimal.getcontext()
- **fractions** - 分数：fractions.Fraction(1, 3)
- **collections** - 数据结构：collections.Counter(list), collections.defaultdict(int)
- **itertools** - 迭代工具：itertools.combinations(items, 2), itertools.permutations(items)
- **re** - 正则表达式：re.search(pattern, text), re.findall(pattern, text)
- **json** - JSON处理：json.loads(str), json.dumps(obj)

💡 **使用方式**：
方式1（推荐）：使用模块前缀 → `result = math.sqrt(16)`
方式2（简洁）：直接调用函数 → `result = sqrt(16)`

📊 **处理CSV/Excel文件的标准流程**：
1. **读取文件**：
   ```python
   # 读取CSV文件
   df = pandas.read_csv(os.path.join(upload_dir, 'filename.csv'))
   # 或简写
   df = pandas.read_csv(upload_dir + '/filename.csv')
   
   # 读取Excel文件
   df = pandas.read_excel(os.path.join(upload_dir, 'filename.xlsx'))
   ```

2. **探索数据结构**（首次处理文件时必做）：
   ```python
   print("数据形状:", df.shape)  # 行数和列数
   print("\\n列名:", df.columns.tolist())  # 所有列名
   print("\\n数据类型:\\n", df.dtypes)  # 每列的数据类型
   print("\\n前5行数据:\\n", df.head())  # 查看前几行
   print("\\n基本统计:\\n", df.describe())  # 数值列的统计信息
   ```

3. **数据分析示例**：
   ```python
   # 计算总和
   total_value = df['column_name'].sum()
   print(f"总计: {{total_value}}")
   
   # 计算平均值
   avg_value = df['column_name'].mean()
   print(f"平均值: {{avg_value}}")
   
   # 分组统计
   grouped = df.groupby('category')['value'].sum()
   print("分组统计:\\n", grouped)
   
   # 筛选数据
   filtered_df = df[df['column'] > 100]
   print(f"筛选后行数: {{len(filtered_df)}}")
   ```

4. **重要提示**：
   - upload_dir 变量已预先定义，指向上传文件目录
   - 使用 pandas（不是 pd）来调用pandas函数
   - 列名可能包含中文或特殊字符，请使用 df.columns 查看准确列名
   - 处理大文件时，先用 df.head() 查看数据结构再进行分析
   - 如果不确定列名，先打印 df.columns.tolist() 查看所有列

❌ **禁止操作**：
- 禁止使用 import 或 from 语句（模块已预先导入）
- 禁止使用 eval(), exec() 等危险函数
- 禁止直接使用 open() 读写文件（使用 pandas.read_csv/read_excel 代替）

【代码要求】
1. **功能正确**：代码能正确完成用户的需求
2. **简洁高效**：使用最直接的方法，避免复杂逻辑
3. **结果输出**：使用print()输出最终结果（格式化输出更好）
4. **安全可靠**：不使用危险操作（文件IO、网络等）

【输出格式】
只输出纯Python代码，不要有任何解释或markdown标记。
代码应该可以直接执行。

【示例1】基础计算
用户查询：计算1到100的和
输出代码：
result = sum(range(1, 101))
print(f"1到100的和是: {{result}}")

【示例2】使用math模块
用户查询：计算圆的面积，半径为5
输出代码：
radius = 5
area = math.pi * radius ** 2
print(f"半径为{{radius}}的圆面积是: {{area:.2f}}")

【示例3】统计分析
用户查询：计算列表的平均值和标准差
输出代码：
data = [85, 92, 78, 90, 88, 95, 82, 89]
avg = statistics.mean(data)
std = statistics.stdev(data)
print(f"平均值: {{avg:.2f}}, 标准差: {{std:.2f}}")

现在请生成代码："""
    
    # ==================== 通用辅助提示词 ====================
    
    @staticmethod
    def get_security_review_prompt(query: str, history: list = None, selected_files: list = None) -> str:
        """
        安全审查提示词
        职责：在处理用户请求前进行安全审查，识别潜在的恶意请求
        
        Args:
            query: 用户当前查询
            history: 对话历史 [{"role": "user"/"assistant", "content": "..."}]
            selected_files: 用户选中的文件列表
        """
        # 构建对话历史部分
        history_text = ""
        if history:
            history_text = "\n## 对话历史\n\n"
            for msg in history:
                role = "用户" if msg['role'] == 'user' else "助手"
                content = msg['content']
                # 限制历史长度，避免过长
                if len(content) > 300:
                    content = content[:300] + "..."
                history_text += f"**{role}**: {content}\n\n"
            history_text += "---\n\n"
        
        # 构建文件上下文部分
        files_context = ""
        if selected_files:
            files_context = f"\n## 用户选中的文件\n用户已选中 {len(selected_files)} 个文件用于分析：\n"
            for fname in selected_files:
                files_context += f"- {fname}\n"
            files_context += "\n关键点：用户已明确提供文件，对这些文件的分析请求应视为数据处理而非系统访问。\n---\n\n"
        
        return f"""# 安全审查专家

你是一个安全审查专家，负责在处理用户请求前识别潜在的安全风险。

⚠️ **重要**：在审查时，请结合对话历史理解用户的真实意图。有些问题在上下文中是合理的，不要仅凭单句判断。
{history_text}{files_context}## 审查规则

请判断以下用户请求是否安全，重点检查：

### 🔴 禁止类别（必须拒绝）

1. **系统访问与管理**
   - 查看/修改系统用户信息（/etc/passwd、/etc/shadow等）
   - 查看/修改系统配置文件（hosts、sudoers等）
   - 访问SSH密钥或其他认证凭据
   - 查看/管理系统进程、服务
   - 修改系统环境变量

2. **文件系统操作**
   - 访问系统目录（/etc、/sys、/proc等）
   - 路径遍历攻击（../../../等）
   - 访问敏感文件或目录
   - 文件删除、修改敏感配置

3. **命令执行**
   - 执行系统命令（subprocess、os.system等）
   - Shell注入尝试
   - 调用系统工具或脚本

4. **网络操作**
   - 建立网络连接（socket、HTTP请求库）
   - 端口扫描
   - 网络攻击工具使用

5. **恶意代码**
   - 代码混淆或加密
   - 反向Shell
   - 权限提升尝试
   - 病毒、木马、后门

6. **隐蔽攻击**
   - 绕过安全机制的尝试
   - 使用编码/加密隐藏意图
   - 社会工程学攻击
   - 教学性质的系统管理操作说明

### 🟢 允许类别

1. **知识查询**
   - 一般性问题回答
   - 专业知识咨询
   - 技术概念解释（理论层面）

2. **数据计算与分析**
   - 数学计算
   - 统计分析
   - 数据处理（用户提供的数据）
   - 算法实现（纯计算）

3. **信息检索**
   - 知识库检索
   - 网络搜索
   - 文档查询

4. **正常对话**
   - 打招呼、感谢
   - 功能咨询
   - 使用帮助

## 判断原则

1. **意图识别**：理解用户真实意图，不仅看字面
2. **严格标准**：涉及系统安全的一律拒绝，包括教学性质
3. **上下文理解**：考虑整体语境
4. **保守判断**：有疑问时选择拒绝
5. **信任用户数据**：对于明确引用用户提供的文件的请求，视为数据处理请求而非系统访问
   - 如果用户已上传文件并要求分析，默认信任该请求
   - "分析这个文件"、"这个CSV分析一下"等在有文件上下文时为安全请求
   - 只有在完全无文件上下文且请求模糊时才视为高风险

## 用户请求

{query}

## 输出格式

严格按照JSON格式输出：
{{
    "is_safe": true/false,
    "risk_level": "safe"/"low"/"medium"/"high"/"critical",
    "reason": "判断理由（如果不安全，说明触发了哪条规则）",
    "category": "请求类别（如：知识查询、数据计算、系统访问等）"
}}

**判断标准：**
- is_safe=true: 请求安全，可以处理
- is_safe=false: 请求不安全，应拒绝

**风险等级：**
- safe: 完全安全的正常请求
- low: 轻微可疑但可能无害
- medium: 中等风险，建议拒绝
- high: 高风险，明确违反规则
- critical: 严重安全威胁，必须拒绝

请进行安全审查："""
    
    # ==================== Lite 提示词 ====================
    
    @staticmethod
    def get_lite_plan_prompt(
        current_time: str,
        query: str,
        has_kb: bool,
        kb_names: Dict[int, str],
        max_web_search: int = 2,
        max_python_code: int = 2,
        max_search: int = 1
    ) -> str:
        """
        V1 Lite Plan 提示词 - 规划工具调用
        
        让模型分析问题并决定需要调用哪些工具
        """
        kb_info = ""
        if has_kb and kb_names:
            kb_info = "\n【可用知识库】\n"
            for kb_id, kb_name in kb_names.items():
                kb_info += f"- [{kb_id}] {kb_name}\n"
        
        kb_tool = ""
        if has_kb:
            kb_tool = f"""
## 1. vector_search - 知识库检索
功能：从知识库中检索相关文档
参数：
- query: 检索查询（必需）
- top_k: 返回结果数量（可选，默认10）
限制：最多调用 {max_search} 次
"""
        
        return f"""# 系统角色

你是一个智能助手，负责分析用户问题并规划工具调用。

## 当前时间
{current_time}

## 用户问题
{query}
{kb_info}
## 可用工具
{kb_tool}
## 2. web_search - 网络搜索
功能：搜索互联网获取最新信息
参数：
- query: 搜索查询（必需）
- top_k: 返回结果数量（可选，默认5）
限制：最多调用 {max_web_search} 次

## 3. python_code - Python 代码执行
功能：执行 Python 代码进行数学计算和逻辑处理
参数：
- query: Python代码（必需，必须使用print()输出结果）
限制：最多调用 {max_python_code} 次
注意：
- 代码必须使用 print() 输出结果，单纯的表达式不会有输出
- ⚠️ Lite模式不支持文件读取和数据分析（无upload_dir上下文）

## 工具调用限制
- 总共最多 5 个工具调用
- web_search 最多 {max_web_search} 次
- python_code 最多 {max_python_code} 次
- vector_search 最多 {max_search} 次

## 任务
分析用户问题，决定需要调用哪些工具。

**重要**：如果用户问题包含多个子问题（例如："A是多少？B是什么时候？"），你需要为每个子问题规划相应的工具调用。

## 决策原则

⚠️ **关键原则**：以下情况**必须**调用python_code，不得直接回答：
- 任何涉及阶乘计算（如：65!、100!等）
- 任何涉及数学函数（sqrt、log、sin、cos、exp等）
- 任何需要精确数值结果的计算
- 任何涉及组合数、排列数的计算（如：C(n,r)、P(n,r)）
- 任何统计分析（平均值、标准差、方差等）

⚠️ **Lite模式限制**：不支持文件读取和数据分析，涉及CSV/Excel等文件处理的任务请提示用户使用Agent完整模式

1. **问题分解**：识别用户问题中的所有子问题，为每个子问题规划工具
2. **必要性**：只调用真正需要的工具
3. **优先级**（按严格顺序判断）：
   - **涉及数学计算** → python_code（必须，不可省略）
   - 需要实时信息 → web_search
   - 需要专业知识 → vector_search
4. **简洁性**：能用 1 个工具解决就不用 2 个
5. **无需工具**：仅限简单问候、常识性陈述（不涉及计算）

## 示例

**示例1 - 数学计算（必须调用工具）**

用户问题：65的阶乘有多少位？

分析：
- 涉及阶乘计算 → **必须**调用 python_code
- 不能用斯特林公式估算直接回答

规划：
```json
[
    {{
        "tool": "python_code",
        "args": {{
            "query": "import math\\nresult = len(str(math.factorial(65)))\\nprint(result)"
        }},
        "reasoning": "涉及阶乘计算，必须使用代码执行获得精确结果"
    }}
]
```

**示例2 - 多个子问题**

用户问题：10的阶乘加20的阶乘等于多少？原神2025生日会播出时间？

分析：
- 子问题1：数学计算（10! + 20!）→ 需要 python_code
- 子问题2：实时信息查询（原神生日会时间）→ 需要 web_search

规划：
```json
[
    {{
        "tool": "python_code",
        "args": {{
            "query": "import math\\nresult = math.factorial(10) + math.factorial(20)\\nprint(result)"
        }},
        "reasoning": "需要计算阶乘和求和"
    }},
    {{
        "tool": "web_search",
        "args": {{
            "query": "原神2025生日会播出时间",
            "top_k": 5
        }},
        "reasoning": "需要查询最新的活动时间信息"
    }}
]
```

**示例3 - 纯计算问题**

用户问题：sqrt(16) * log(100) 等于多少？

分析：
- 涉及数学函数（开方、对数）→ **必须**调用 python_code

规划：
```json
[
    {{
        "tool": "python_code",
        "args": {{
            "query": "import math\\nresult = math.sqrt(16) * math.log(100)\\nprint(result)"
        }},
        "reasoning": "涉及数学函数计算，必须使用代码执行"
    }}
]
```

**示例4 - 文件分析（Lite模式不支持）**

用户问题：分析一下team-usage.csv，统计总token用量

分析：
- 涉及文件读取和数据分析 → Lite模式不支持
- 应提示用户切换到Agent完整模式

规划：
```json
[]
```

注：直接回答时应告知用户："Lite模式不支持文件读取和数据分析，请切换到Agent完整模式来处理CSV文件。"

## 输出格式
返回 JSON 数组，每个元素是一个工具调用：

```json
[
    {{
        "tool": "工具名称",
        "args": {{
            "query": "具体查询内容",
            "top_k": 5
        }},
        "reasoning": "为什么调用这个工具"
    }}
]
```

如果不需要调用任何工具，返回空数组：`[]`

现在请分析用户问题并规划工具调用："""
    
    @staticmethod
    def get_lite_answer_prompt(
        current_time: str,
        query: str,
        tools_summary: str
    ) -> str:
        """
        V1 Lite Answer 提示词 - 生成最终答案
        
        基于工具执行结果回答用户问题
        """
        return f"""# 系统角色

你是一个专业的问答助手，负责基于工具执行结果回答用户问题。

## 当前时间
{current_time}

## 用户问题
{query}

## 工具执行结果
{tools_summary}

## 任务
基于上述工具执行结果，回答用户问题。

**重要**：如果用户问题包含多个子问题，请分别回答每个子问题，并清晰地组织答案结构。

## 回答原则
1. **准确性**：基于工具结果，不要编造信息
2. **完整性**：覆盖用户问题的所有方面，如果有多个子问题，逐一回答
3. **清晰性**：结构清晰，易于理解，多个子问题时使用分节或编号
4. **引用性**：提及信息来源（如"根据检索结果"、"根据计算"）
5. **综合性**：整合多个工具的结果，形成连贯的回答

## 格式要求
- 使用 Markdown 格式
- 数学公式使用 LaTeX：行内 `$...$`，块级 `$$...$$`
- 代码使用代码块：```语言
- 列表、表格等合理使用

## 特殊情况处理
- 如果所有工具都失败：基于通用知识回答，并说明"由于工具执行失败，以下是基于通用知识的回答"
- 如果部分工具失败：基于成功的工具结果回答，忽略失败的部分
- 如果无工具调用且问题涉及文件分析：明确告知"Lite模式不支持文件读取和数据分析，请切换到Agent完整模式来处理CSV/Excel文件"
- 如果无工具调用且问题不涉及文件：直接基于通用知识回答

现在请回答用户问题："""
