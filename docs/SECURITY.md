# 安全指南

> Open_ReAct_Agent 系统安全架构与最佳实践

本文档介绍 Open_ReAct_Agent 系统的安全机制、配置和最佳实践。

---

## 📋 目录

- [安全概述](#安全概述)
- [多层安全防御](#多层安全防御)
- [Python 执行器安全](#python-执行器安全)
- [API 安全](#api-安全)
- [数据安全](#数据安全)
- [安全配置](#安全配置)
- [安全测试](#安全测试)
- [最佳实践](#最佳实践)

---

## 安全概述

Open_ReAct_Agent 采用**多层安全防御**架构，从请求审查到代码执行全程保护系统安全。

### 安全目标

1. **防止恶意代码执行** - 阻止危险的系统调用和文件操作
2. **资源隔离** - 限制内存、CPU、文件等资源使用
3. **请求审查** - 检测并拒绝恶意请求
4. **数据保护** - 保护敏感数据和 API 密钥
5. **审计追踪** - 记录所有关键操作

### 安全等级

| 等级 | 适用场景 | 执行器类型 | 安全特性 |
|------|----------|-----------|---------|
| **高** | 生产环境、公开服务 | `process_isolated` | 全部启用 |
| **中** | 内部服务、受信环境 | `process_isolated` | 部分启用 |
| **低** | 开发测试环境 | `default` | 基础白名单 |

---

## 多层安全防御

### 第一层：LLM 安全审查

在处理用户请求前，使用 LLM 进行安全审查。

**检测内容**：
- 系统管理操作（查看用户、进程、服务等）
- 敏感文件访问（/etc/passwd、SSH 密钥等）
- 系统命令执行（subprocess、os.system等）
- 网络操作（socket、HTTP 请求等）
- 社会工程学攻击

**实现**：
```python
# app/services/security_checker.py
def check_security(query: str) -> Dict[str, Any]:
    """LLM 安全审查"""
    # 使用 LLM 分析请求意图
    # 识别潜在的安全风险
    # 返回安全评估结果
```

**配置**：
```python
# config.py
# 在 PromptTemplates 类中配置审查提示词
```

### 第二层：AST 静态审计

在代码执行前进行语法树分析。

**检测内容**：
- 危险函数调用（`eval`, `exec`, `compile`, `__import__`等）
- 私有属性访问（`__xxx__`）
- 模块导入绕过
- 文件操作（`open`, `file`等）

**实现**：
```python
# app/services/python_executor_v2.py
def audit_code_ast(code: str) -> List[str]:
    """AST 静态审计"""
    tree = ast.parse(code)
    # 检查危险节点
    # 返回违规列表
```

### 第三层：白名单机制

只允许预定义的安全模块和函数。

**允许的模块**：
- **数学计算**: `math`, `cmath`, `statistics`, `decimal`, `fractions`, `random`
- **科学计算**: `numpy`, `scipy`, `mpmath`, `sympy`
- **数据分析**: `pandas`, `statsmodels`, `sklearn`
- **可视化**: `matplotlib`, `plotly`, `plotnine`
- **标准库**: `datetime`, `collections`, `itertools`, `re`, `json`

**允许的内置函数**：
- 类型转换: `int`, `float`, `str`, `bool`, `list`, `dict`, `set`
- 数学运算: `abs`, `round`, `sum`, `min`, `max`, `pow`
- 序列操作: `len`, `range`, `enumerate`, `zip`, `map`, `filter`
- 其他: `print`, `format`, `type`, `isinstance`

**配置**：
```python
# config.py
PYTHON_ALLOWED_MODULES = {
    'math': ['sqrt', 'sin', 'cos', 'factorial', ...],
    'numpy': ['*'],
    # ...
}

PYTHON_ALLOWED_BUILTINS = [
    'int', 'float', 'str', 'print', ...
]
```

### 第四层：进程隔离 + 资源限额

使用独立进程执行代码，严格限制资源使用。

**资源限制**：
- **内存**: 256MB（默认）
- **CPU 时间**: 10秒（默认）
- **执行超时**: 10秒（默认）
- **文件大小**: 10MB（默认）
- **递归深度**: 1000（默认）

**实现**：
```python
# app/services/python_executor_v2.py
class PythonExecutorV2:
    def execute(self, code: str) -> Dict:
        # 创建独立进程
        # 设置资源限制
        # 执行代码
        # 捕获输出
        # 终止进程
```

**配置**：
```python
# config.py
PYTHON_EXECUTOR_TYPE = 'process_isolated'
PYTHON_EXECUTOR_MAX_MEMORY_MB = 256
PYTHON_EXECUTOR_MAX_CPU_TIME = 10
PYTHON_EXECUTOR_TIMEOUT = 10
```

### 第五层：沙箱文件系统

隔离文件操作，保护主机文件系统。

**特性**：
- 临时目录隔离
- 默认禁止文件 IO
- 可选只读模式
- 可选写入模式（仅临时目录）
- 环境变量净化

**配置**：
```python
# config.py
PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN = False  # 是否允许 open()
PYTHON_EXECUTOR_SANDBOX_ALLOW_WRITE = False # 是否允许写入
PYTHON_EXECUTOR_SANITIZE_ENV = True         # 净化环境变量
```

### 第六层：执行监控

实时监控执行状态，记录审计日志，限制调用频率。

**监控功能**：
- 执行历史记录
- 成功率统计
- 平均耗时分析
- 异常检测（超时、内存超限）

**速率限制**：
- 每用户每分钟: 20次（默认）
- 每用户每小时: 100次（默认）
- 全局每分钟: 100次（默认）

**审计日志**：
```
logs/executor_audit.log       # 审计日志
logs/executor_failures.log    # 失败代码日志
```

**配置**：
```python
# config.py
PYTHON_EXECUTOR_ENABLE_MONITORING = True
PYTHON_EXECUTOR_ENABLE_AUDIT = True
PYTHON_EXECUTOR_ENABLE_RATE_LIMIT = True
PYTHON_EXECUTOR_RATE_LIMIT_PER_MINUTE = 20
PYTHON_EXECUTOR_RATE_LIMIT_PER_HOUR = 100
```

---

## Python 执行器安全

### 执行器类型

#### 1. 默认执行器 (`default`)

**特性**：
- 基础白名单机制
- 受限内置函数
- 无进程隔离
- 低开销

**适用场景**：
- 开发测试环境
- 受信用户
- 性能优先

#### 2. HSL 执行器 (`process_isolated`)

**特性**：
- AST 静态审计
- 进程隔离执行
- 资源限额
- 沙箱文件系统
- 完整监控

**适用场景**：
- 生产环境（推荐）
- 公开服务
- 安全优先

### 切换执行器

```bash
# 环境变量方式
export PYTHON_EXECUTOR_TYPE=process_isolated
python app.py

# 或在 config.py 中配置
PYTHON_EXECUTOR_TYPE = 'process_isolated'
```

### 安全配置示例

#### 生产环境（高安全）

```python
# config.py

# 执行器类型
PYTHON_EXECUTOR_TYPE = 'process_isolated'

# 资源限制
PYTHON_EXECUTOR_TIMEOUT = 10
PYTHON_EXECUTOR_MAX_MEMORY_MB = 256
PYTHON_EXECUTOR_MAX_CPU_TIME = 10
PYTHON_EXECUTOR_MAX_CODE_LENGTH = 10000
PYTHON_EXECUTOR_MAX_FILE_SIZE_MB = 10

# 沙箱配置（最严格）
PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN = False
PYTHON_EXECUTOR_SANDBOX_ALLOW_WRITE = False
PYTHON_EXECUTOR_SANITIZE_ENV = True
PYTHON_EXECUTOR_RECURSION_LIMIT = 1000

# 监控与审计（全部启用）
PYTHON_EXECUTOR_ENABLE_MONITORING = True
PYTHON_EXECUTOR_ENABLE_AUDIT = True
PYTHON_EXECUTOR_ENABLE_RATE_LIMIT = True
PYTHON_EXECUTOR_RATE_LIMIT_PER_MINUTE = 20
PYTHON_EXECUTOR_RATE_LIMIT_PER_HOUR = 100
PYTHON_EXECUTOR_GLOBAL_RATE_LIMIT = 100
```

#### 开发环境（低安全）

```python
# config.py

# 使用默认执行器（更快）
PYTHON_EXECUTOR_TYPE = 'default'

# 较宽松的限制
PYTHON_EXECUTOR_TIMEOUT = 30
PYTHON_EXECUTOR_MAX_CODE_LENGTH = 50000

# 禁用额外功能（减少开销）
PYTHON_EXECUTOR_ENABLE_MONITORING = False
PYTHON_EXECUTOR_ENABLE_AUDIT = False
PYTHON_EXECUTOR_ENABLE_RATE_LIMIT = False
```

---

## API 安全

### API 密钥管理

**最佳实践**：

1. **不要硬编码** - 永远不要在代码中硬编码 API 密钥

2. **使用环境变量** - 创建 `.env` 文件：
```bash
# .env
CHAT_API_KEY=your-chat-api-key
EMBED_API_KEY=your-embed-api-key
RERANK_API_KEY=your-rerank-api-key
SEARCH_API_KEY=your-search-api-key
```

3. **在 config.py 中读取**：
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

CHAT_API_KEY = os.getenv('CHAT_API_KEY')
EMBED_API_KEY = os.getenv('EMBED_API_KEY')
```

4. **添加到 .gitignore**：
```bash
echo ".env" >> .gitignore
```

### CORS 配置

```python
# app.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 启用 CORS（开发环境）

# 生产环境应限制来源
# CORS(app, origins=['https://your-domain.com'])
```

### 请求限流

使用执行器监控的速率限制功能：
- 每用户每分钟限制
- 每用户每小时限制
- 全局限制

---

## 数据安全

### 数据库安全

**SQLite 数据库**：
```
data/knowledge_base.db
```

**最佳实践**：
1. 设置适当的文件权限
2. 定期备份数据库
3. 不要提交数据库文件到 Git

### 向量存储安全

**向量索引**：
```
data/vectors/kb_<id>/
  - faiss.index
  - metadata.json
```

**最佳实践**：
1. 保护向量数据不被未授权访问
2. 定期备份向量索引
3. 验证元数据完整性

### 日志安全

**日志文件**：
```
logs/api_io_*.jsonl       # API 和 LLM 调用日志
logs/executor_audit.log   # 执行器审计日志
logs/executor_failures.log # 失败代码日志
```

**注意事项**：
- 日志可能包含敏感信息
- 设置日志文件权限
- 定期清理旧日志
- 不要提交日志到 Git

---

## 安全配置

### 完整的生产环境配置

```python
# config.py

# ==================== 执行器安全配置 ====================
# 执行器类型（生产环境必须使用 process_isolated）
PYTHON_EXECUTOR_TYPE = 'process_isolated'

# 基础限制
PYTHON_EXECUTOR_TIMEOUT = 10
PYTHON_EXECUTOR_MAX_OUTPUT = 5000
PYTHON_EXECUTOR_MAX_CODE_LENGTH = 10000

# 资源限制（HSL 执行器）
PYTHON_EXECUTOR_MAX_MEMORY_MB = 256
PYTHON_EXECUTOR_MAX_CPU_TIME = 10
PYTHON_EXECUTOR_MAX_FILE_SIZE_MB = 10

# 沙箱配置（最严格）
PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN = False
PYTHON_EXECUTOR_SANDBOX_ALLOW_WRITE = False
PYTHON_EXECUTOR_SANITIZE_ENV = True
PYTHON_EXECUTOR_RECURSION_LIMIT = 1000

# 监控与审计（全部启用）
PYTHON_EXECUTOR_ENABLE_MONITORING = True
PYTHON_EXECUTOR_ENABLE_AUDIT = True
PYTHON_EXECUTOR_ENABLE_RATE_LIMIT = True
PYTHON_EXECUTOR_RATE_LIMIT_PER_MINUTE = 20
PYTHON_EXECUTOR_RATE_LIMIT_PER_HOUR = 100
PYTHON_EXECUTOR_GLOBAL_RATE_LIMIT = 100

# ==================== 文件上传限制 ====================
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'xlsx', 'md'}

# ==================== API 调用限制 ====================
# 工具调用次数限制
INITIAL_RETRIEVAL_TOP_K = 50
LIGHT_RERANK_TOP_K = 20
FINAL_RERANK_TOP_K = 5

# V2 Agent 工具调用上限
# search: 10次, web_search: 3次, python_code: 10次
```

---

## 安全测试

### 测试脚本

项目提供了完整的安全测试套件：

```bash
# 执行器安全测试
python scripts/test_executor_security.py

# HSL 执行器测试
python scripts/test_hsl_executor.py

# 沙箱安全测试
python scripts/test_sandbox_security.py
```

### 测试内容

1. **正常代码执行** - 验证合法代码可以正常运行
2. **危险代码拦截** - 验证危险代码被阻止
3. **资源限制** - 验证内存、CPU 限制生效
4. **超时控制** - 验证超时后进程被终止
5. **速率限制** - 验证调用频率限制生效
6. **并发执行** - 验证多线程安全性
7. **沙箱隔离** - 验证文件系统隔离

### 运行所有测试

```bash
# 运行所有安全测试
cd /Users/caizhexi/Desktop/个人项目/Open_ReAct_Agent
python scripts/test_executor_security.py
python scripts/test_hsl_executor.py
python scripts/test_sandbox_security.py
```

---

## 最佳实践

### 开发阶段

1. **使用默认执行器** - 开发时使用 `default` 执行器提高效率
2. **禁用速率限制** - 避免频繁测试时触发限制
3. **启用详细日志** - 设置 `DEBUG` 日志级别
4. **定期运行测试** - 确保代码变更不影响安全性

### 部署阶段

1. **切换到 HSL 执行器** - 设置 `PYTHON_EXECUTOR_TYPE='process_isolated'`
2. **启用所有安全特性** - 监控、审计、速率限制全部启用
3. **配置适当的资源限制** - 根据服务器配置调整
4. **保护敏感文件** - API 密钥、数据库、日志等

### 运维阶段

1. **监控日志** - 定期检查审计日志和失败日志
2. **分析统计** - 查看执行器统计信息，识别异常
3. **定期更新** - 及时更新依赖库和安全补丁
4. **备份数据** - 定期备份数据库和向量索引
5. **清理日志** - 定期清理旧日志文件

### 应急响应

**发现安全事件时**：

1. **立即停止服务** - 阻止进一步损害
2. **查看日志** - 分析攻击方式和影响范围
3. **修复漏洞** - 更新配置或代码
4. **恢复服务** - 验证安全后恢复
5. **事后分析** - 总结经验，改进安全措施

---

## 安全检查清单

### 部署前检查

- [ ] API 密钥已配置且不在代码中
- [ ] 执行器类型设置为 `process_isolated`
- [ ] 所有安全特性已启用
- [ ] 资源限制已配置
- [ ] 文件权限正确设置
- [ ] `.env` 文件已添加到 `.gitignore`
- [ ] 所有安全测试通过
- [ ] CORS 配置正确
- [ ] 日志目录权限正确

### 定期检查

- [ ] 查看审计日志，识别异常
- [ ] 检查执行器统计，分析趋势
- [ ] 更新依赖库
- [ ] 备份数据库和向量索引
- [ ] 清理旧日志
- [ ] 测试灾难恢复流程

---

## 安全联系

如发现安全漏洞或有安全建议，请：

1. **不要公开披露** - 避免被恶意利用
2. **私下报告** - 通过安全邮件或私密 Issue
3. **提供详细信息** - 复现步骤、影响范围、修复建议
4. **等待响应** - 给团队时间修复漏洞

---

## 总结

Open_ReAct_Agent 采用六层安全防御机制，从 LLM 安全审查到执行监控，全面保护系统安全。

**关键要点**：

1. ✅ **生产环境必须使用 HSL 执行器**
2. ✅ **启用所有安全特性**（监控、审计、速率限制）
3. ✅ **保护敏感信息**（API 密钥、数据库、日志）
4. ✅ **定期运行安全测试**
5. ✅ **监控和分析日志**

遵循本文档的安全最佳实践，确保 Open_ReAct_Agent 系统安全可靠运行。

---

**文档版本**：v2.0  
**最后更新**：2025年11月2日  
**维护者**：Open_ReAct_Agent Team

