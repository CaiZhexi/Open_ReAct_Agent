# 开发指南

> Agentic-RAG 开发者完整指南

本文档为开发者提供项目结构、开发流程、测试方法和最佳实践。

---

## 📋 目录

- [开发环境设置](#开发环境设置)
- [项目结构](#项目结构)
- [代码规范](#代码规范)
- [开发流程](#开发流程)
- [测试指南](#测试指南)
- [调试技巧](#调试技巧)
- [性能分析](#性能分析)
- [常见开发任务](#常见开发任务)
- [贡献指南](#贡献指南)

---

## 开发环境设置

### 1. 前置要求

- Python 3.10+
- Git
- 代码编辑器（推荐 VS Code / PyCharm / Cursor）

### 2. 克隆项目

```bash
git clone https://github.com/CaiZhexi/Open_ReAct_Agent.git
cd Open_ReAct_Agent
```

### 3. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 4. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest pytest-cov black flake8 mypy
```

### 5. 配置环境变量

创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env

# 编辑配置，填入你的 API 密钥
nano .env
```

```.env
# API Keys
CHAT_API_KEY=your-test-key
EMBED_API_KEY=your-test-key
RERANK_API_KEY=your-test-key
SEARCH_API_KEY=your-test-key

# 开发配置
FLASK_DEBUG=true
PYTHON_EXECUTOR_TYPE=default
ENABLE_IO_LOGGING=true
DISPATCHER_LOG_LEVEL=DEBUG
```

### 6. 初始化数据目录

```bash
mkdir -p data/vectors logs
```

### 7. 运行开发服务器

```bash
python app.py
```

访问：`http://localhost:5004`

---

## 项目结构

### 目录结构

```
Open_ReAct_Agent/
├── app/                        # 应用主目录
│   ├── __init__.py
│   ├── routes/                 # API 路由
│   │   ├── __init__.py
│   │   ├── knowledge_base.py  # 知识库管理
│   │   ├── documents.py       # 文档管理
│   │   ├── rag.py             # V1 RAG 接口
│   │   └── rag_v2.py          # V2 RAG 接口
│   ├── services/              # 核心服务
│   │   ├── v2_agent.py        # V2 Agent
│   │   ├── dispatcher.py      # V1 调度器
│   │   ├── agentic_rag.py     # RAG 服务
│   │   ├── tools.py           # 工具系统
│   │   ├── python_executor.py # 默认执行器
│   │   ├── python_executor_v2.py # HSL 执行器
│   │   ├── executor_factory.py   # 执行器工厂
│   │   ├── executor_monitor.py   # 执行监控
│   │   ├── security_checker.py   # 安全检查
│   │   ├── api_clients.py        # API 客户端
│   │   ├── io_logger.py          # IO 日志
│   │   ├── document_processor.py # 文档处理
│   │   └── document_queue.py     # 文档队列
│   ├── models/                # 数据模型
│   │   ├── database.py        # 数据库管理
│   │   └── vector_store.py    # 向量存储
│   ├── templates/             # HTML 模板
│   │   └── index.html
│   └── static/                # 静态文件
│       ├── css/style.css
│       └── js/app.js
├── scripts/                   # 实用脚本
│   ├── analyze_io_log.py
│   ├── test_executor_security.py
│   └── ...
├── docs/                      # 文档
│   ├── README.md
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   ├── DEVELOPMENT.md (本文档)
│   ├── SECURITY.md
│   └── V2_ARCHITECTURE.md
├── data/                      # 数据存储
│   ├── knowledge_base.db
│   └── vectors/
├── logs/                      # 日志文件
├── app.py                     # 应用入口
├── config.py                  # 配置文件
├── requirements.txt           # 依赖清单
└── README.md                  # 项目说明
```

### 核心模块说明

#### routes/ - 路由层

负责HTTP请求处理和响应：
- 参数验证
- 调用服务层
- 返回 JSON 响应

#### services/ - 服务层

核心业务逻辑：
- **v2_agent.py**: V2 增量式迭代 Agent
- **dispatcher.py**: V1 调度器
- **tools.py**: 工具注册和管理
- **python_executor*.py**: Python 代码执行

#### models/ - 数据层

数据持久化和管理：
- **database.py**: SQLite 数据库操作
- **vector_store.py**: Faiss 向量存储

---

## 代码规范

### Python 代码风格

遵循 PEP 8 规范：

```bash
# 使用 black 格式化代码
black app/ scripts/

# 使用 flake8 检查代码
flake8 app/ scripts/ --max-line-length=100

# 使用 mypy 检查类型
mypy app/ --ignore-missing-imports
```

### 命名规范

```python
# 文件名：小写+下划线
# file_name.py

# 类名：大驼峰
class AgentContext:
    pass

# 函数/变量：小写+下划线
def process_document(doc_id: int):
    user_query = "..."

# 常量：大写+下划线
MAX_RETRY_ATTEMPTS = 3

# 私有属性/方法：前缀下划线
def _internal_method():
    pass
```

### 文档字符串

```python
def function_name(param1: str, param2: int) -> Dict[str, Any]:
    """
    简要描述函数功能
    
    详细说明（如果需要）
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
    
    Returns:
        返回值说明
    
    Raises:
        Exception: 异常说明
    
    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
    """
    pass
```

### 类型注解

```python
from typing import List, Dict, Optional, Any

def get_documents(
    kb_id: int, 
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """使用类型注解"""
    pass
```

---

## 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/new-feature
```

### 2. 开发新功能

#### 添加新的工具

```python
# app/services/tools.py

from app.services.tools import tool_registry

@tool_registry.register(
    name="new_tool",
    description="新工具描述",
    required_params=["query"],
    optional_params=["param2"]
)
def new_tool(query: str, param2: str = "default", **kwargs):
    """
    新工具实现
    
    Args:
        query: 查询参数
        param2: 可选参数
    
    Returns:
        {
            'summary': '结果摘要',
            'data': 详细数据
        }
    """
    # 实现工具逻辑
    result = do_something(query, param2)
    
    return {
        'summary': f'处理完成: {query}',
        'data': result
    }
```

#### 添加新的 API 端点

```python
# app/routes/custom.py

from flask import Blueprint, request, jsonify

custom_bp = Blueprint('custom', __name__, url_prefix='/api/custom')

@custom_bp.route('/endpoint', methods=['POST'])
def custom_endpoint():
    """自定义端点"""
    try:
        data = request.get_json()
        
        # 参数验证
        if not data or 'param' not in data:
            return jsonify({
                'success': False,
                'message': '参数错误'
            }), 400
        
        # 调用服务层
        result = service.do_something(data['param'])
        
        return jsonify({
            'success': True,
            'data': result,
            'message': '操作成功'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'错误: {str(e)}'
        }), 500

# 在 app.py 中注册蓝图
from app.routes.custom import custom_bp
app.register_blueprint(custom_bp)
```

### 3. 编写测试

```python
# tests/test_new_feature.py

import pytest
from app.services.tools import new_tool

def test_new_tool():
    """测试新工具"""
    result = new_tool("test query")
    
    assert result is not None
    assert 'summary' in result
    assert 'data' in result
    assert '处理完成' in result['summary']

def test_new_tool_error():
    """测试错误处理"""
    with pytest.raises(ValueError):
        new_tool("")  # 空查询应该抛出异常
```

### 4. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_new_feature.py

# 带覆盖率报告
pytest --cov=app tests/
```

### 5. 提交代码

```bash
# 添加更改
git add .

# 提交
git commit -m "feat: add new feature

- Add new_tool to tools registry
- Add custom API endpoint
- Add tests for new feature"

# 推送到远程
git push origin feature/new-feature
```

### 6. 创建 Pull Request

在 GitHub 上创建 PR，等待代码审查。

---

## 测试指南

### 测试结构

```
tests/
├── __init__.py
├── conftest.py          # 测试配置和 fixtures
├── test_routes/         # 路由测试
│   ├── test_kb.py
│   └── test_rag.py
├── test_services/       # 服务测试
│   ├── test_tools.py
│   └── test_executor.py
└── test_models/         # 模型测试
    └── test_database.py
```

### 单元测试

```python
# tests/test_services/test_tools.py

import pytest
from app.services.tools import tool_registry, search_tool

def test_tool_registry():
    """测试工具注册"""
    tools = tool_registry.get_all_tools()
    assert len(tools) > 0
    assert 'search' in [t['name'] for t in tools]

def test_search_tool(mock_vector_store):
    """测试检索工具"""
    result = search_tool(
        query="测试查询",
        kb_ids=[1],
        top_k=5
    )
    
    assert result is not None
    assert 'summary' in result
    assert 'data' in result
```

### 集成测试

```python
# tests/test_routes/test_rag.py

import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_v2_chat_endpoint(client):
    """测试 V2 问答端点"""
    response = client.post('/api/v2/chat', json={
        'query': '测试问题',
        'stream': False
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == True
    assert 'answer' in data['data']
```

### 运行特定测试

```bash
# 运行特定文件
pytest tests/test_services/test_tools.py

# 运行特定测试函数
pytest tests/test_services/test_tools.py::test_search_tool

# 运行标记的测试
pytest -m slow  # 运行标记为 slow 的测试

# 详细输出
pytest -v

# 停在第一个失败
pytest -x

# 并行运行（需要 pytest-xdist）
pytest -n auto
```

---

## 调试技巧

### 1. 使用 Python Debugger

```python
# 在代码中插入断点
import pdb; pdb.set_trace()

# 或使用 breakpoint() (Python 3.7+)
breakpoint()
```

### 2. 日志调试

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 使用日志
logger.debug(f"变量值: {variable}")
logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
```

### 3. VS Code 调试配置

创建 `.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "app.py",
                "FLASK_DEBUG": "1"
            },
            "args": [
                "run",
                "--no-debugger",
                "--no-reload",
                "--port", "5004"
            ],
            "jinja": true
        }
    ]
}
```

### 4. 查看 IO 日志

```bash
# 实时查看 IO 日志
tail -f logs/api_io_*.jsonl | jq .

# 分析特定请求
cat logs/api_io_*.jsonl | jq 'select(.type == "api_request")'

# 查看 LLM 调用
cat logs/api_io_*.jsonl | jq 'select(.type == "llm_call")'
```

### 5. 调试脚本

```bash
# 使用调试追踪脚本
python scripts/trace_v2_agent_io.py

# 分析复杂场景
python scripts/run_complex_trace.py
```

---

## 性能分析

### 1. 使用 cProfile

```python
import cProfile
import pstats

# 分析函数性能
cProfile.run('function_to_profile()', 'output.prof')

# 查看结果
p = pstats.Stats('output.prof')
p.sort_stats('cumulative')
p.print_stats(20)  # 显示前20个
```

### 2. 使用 line_profiler

```bash
# 安装
pip install line_profiler

# 在代码中标记要分析的函数
@profile
def slow_function():
    # 代码
    pass

# 运行
kernprof -l -v script.py
```

### 3. 内存分析

```bash
# 安装
pip install memory_profiler

# 使用
python -m memory_profiler script.py
```

### 4. 分析 IO 日志性能

```bash
# 使用分析脚本
python scripts/analyze_io_log.py logs/api_io_*.jsonl

# 查看性能统计
curl http://localhost:5004/api/io-logs
```

---

## 常见开发任务

### 添加新的 Embedding 模型

```python
# config.py

# 修改 Embedding 配置
EMBED_API_KEY = 'new-api-key'
EMBED_API_URL = 'https://api.provider.com/v1/embeddings'
EMBED_MODEL = 'new-model-name'
EMBED_DIMENSIONS = 768  # 根据模型调整

# app/services/api_clients.py 中可能需要调整 API 调用格式
```

### 添加新的提示词模板

```python
# config.py - PromptTemplates 类

@staticmethod
def get_new_prompt_template(param1: str, param2: str) -> str:
    """新提示词模板"""
    return f"""你是一个...

【参数1】
{param1}

【参数2】
{param2}

请...
"""
```

### 修改工具调用上限

```python
# config.py

# V2 Agent 工具调用上限（在 V2Agent 初始化时设置）
# app/services/v2_agent.py

self.context.tool_call_limits = {
    'search': 15,      # 修改知识库检索上限
    'web_search': 5,   # 修改网络搜索上限
    'python_code': 20  # 修改代码执行上限
}
```

### 添加新的文档格式支持

```python
# app/services/document_processor.py

def parse_new_format(file_path: str) -> str:
    """解析新格式文档"""
    # 实现解析逻辑
    pass

# 在 parse_document 中添加格式判断
if filename.endswith('.new_ext'):
    text = parse_new_format(file_path)

# config.py - 添加到允许的扩展名
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'xlsx', 'md', 'new_ext'}
```

---

## 贡献指南

### 代码贡献流程

1. **Fork 项目**
2. **创建功能分支**: `git checkout -b feature/amazing-feature`
3. **编写代码和测试**
4. **提交更改**: `git commit -m 'feat: add amazing feature'`
5. **推送分支**: `git push origin feature/amazing-feature`
6. **创建 Pull Request**

### Commit 消息规范

使用语义化提交消息：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**:
```
feat(agent): add task decomposition support

- Add decompose_tasks action to V2 Agent
- Update plan prompt to include task decomposition
- Add tests for multi-task scenarios

Closes #123
```

### Pull Request 检查清单

- [ ] 代码符合项目风格规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交消息清晰明确
- [ ] 没有合并冲突

### 代码审查标准

审查者会检查：
1. **功能正确性** - 代码是否实现了预期功能
2. **代码质量** - 是否清晰、可维护
3. **测试覆盖** - 是否有充分的测试
4. **性能影响** - 是否影响系统性能
5. **安全性** - 是否引入安全风险
6. **文档完整性** - 是否更新了文档

---

## 开发资源

### 文档链接

- [API 参考文档](./API_REFERENCE.md)
- [部署指南](./DEPLOYMENT.md)
- [安全指南](./SECURITY.md)
- [V2 架构文档](./V2_ARCHITECTURE.md)

### 有用的工具

- **代码格式化**: black, autopep8
- **代码检查**: flake8, pylint
- **类型检查**: mypy
- **测试工具**: pytest, pytest-cov
- **性能分析**: cProfile, line_profiler, memory_profiler
- **文档生成**: Sphinx
- **API 测试**: Postman, HTTPie, curl

### 学习资源

- [Flask 文档](https://flask.palletsprojects.com/)
- [Faiss 文档](https://github.com/facebookresearch/faiss)
- [Python 最佳实践](https://docs.python-guide.org/)
- [测试驱动开发](https://testdriven.io/)

---

## 常见问题

### Q: 如何添加新的依赖？

A: 
```bash
# 安装依赖
pip install new-package

# 更新 requirements.txt
pip freeze > requirements.txt

# 或手动添加到 requirements.txt
echo "new-package==1.0.0" >> requirements.txt
```

### Q: 如何重置数据库？

A:
```bash
# 删除数据库
rm data/knowledge_base.db

# 重启应用（会自动创建新数据库）
python app.py
```

### Q: 如何清理向量索引？

A:
```bash
# 删除所有向量索引
rm -rf data/vectors/*

# 或删除特定知识库
rm -rf data/vectors/kb_5/
```

### Q: 如何查看详细的错误信息？

A:
```python
# config.py
# 设置为 DEBUG 模式
DEBUG = True
DISPATCHER_LOG_LEVEL = 'DEBUG'

# 或使用环境变量
export FLASK_DEBUG=true
export DISPATCHER_LOG_LEVEL=DEBUG
```

---

## 总结

本文档提供了 Agentic-RAG 项目的完整开发指南。遵循这些规范和最佳实践，可以确保代码质量和项目的可维护性。

**关键要点**：

1. ✅ 遵循代码规范和命名约定
2. ✅ 编写充分的测试
3. ✅ 使用类型注解和文档字符串
4. ✅ 提交清晰的 commit 消息
5. ✅ 积极进行代码审查

欢迎贡献！🎉

---

**文档版本**：v1.0  
**最后更新**：2025年10月12日  
**维护者**：Agentic-RAG Team

