# Open_ReAct_Agent 文档中心

> 完整的项目文档和开发指南

欢迎来到 Open_ReAct_Agent 文档中心！这里提供项目的完整文档，帮助你快速上手和深入了解系统。

---

## 📚 文档导航

### 快速开始

| 文档 | 说明 | 阅读时间 |
|------|------|----------|
| [项目说明](../README.md) | 项目概览、功能特性、快速开始 | 15分钟 |
| [API 参考](./API_REFERENCE.md) | REST API 完整参考文档 | 20分钟 |
| [部署指南](./DEPLOYMENT.md) | 生产环境部署完整指南 | 30分钟 |

### 开发指南

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [开发指南](./DEVELOPMENT.md) | 开发环境设置、代码规范、测试 | 开发者 |
| [安全指南](./SECURITY.md) | 安全机制、配置和最佳实践 | 所有人 |
| [V2 架构](./V2_ARCHITECTURE.md) | V2 增量式迭代架构详解 | 架构师、开发者 |

---

## 🎯 我想...

### 🚀 快速开始使用

**阅读**: [项目说明](../README.md) → [快速开始](../README.md#-快速开始) 部分

```bash
# 克隆项目
git clone https://github.com/CaiZhexi/Open_ReAct_Agent.git
cd Open_ReAct_Agent

# 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 运行服务
python app.py
```

访问：`http://localhost:5004`

---

### 📖 了解 API 接口

**阅读**: [API 参考文档](./API_REFERENCE.md)

**核心接口**：
- 知识库管理：`/api/kb/*`
- 文档管理：`/api/docs/*`
- V1 问答：`/api/rag/chat`, `/api/rag/agentic-chat`
- V2 问答：`/api/v2/chat`
- 工具管理：`/api/rag/tools`

**示例**：
```bash
# V2 问答（流式）
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "高空作业的安全要求有哪些？",
    "kb_ids": [5],
    "stream": true
  }'
```

---

### 🔐 配置安全功能

**阅读**: [安全指南](./SECURITY.md)

**快速配置（生产环境）**：

```python
# config.py

# 使用 HSL 执行器（高安全级别）
PYTHON_EXECUTOR_TYPE = 'process_isolated'

# 启用所有安全特性
PYTHON_EXECUTOR_ENABLE_MONITORING = True
PYTHON_EXECUTOR_ENABLE_AUDIT = True
PYTHON_EXECUTOR_ENABLE_RATE_LIMIT = True

# 严格的沙箱配置
PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN = False
PYTHON_EXECUTOR_SANDBOX_ALLOW_WRITE = False
PYTHON_EXECUTOR_SANITIZE_ENV = True
```

**安全特性**：
- ✅ 六层安全防御（LLM审查→AST审计→白名单→进程隔离→沙箱→监控）
- ✅ 资源限额（内存256MB、CPU 10秒、文件10MB）
- ✅ 速率限制（20次/分钟、100次/小时）
- ✅ 审计日志（所有执行记录）

---

### 🚢 部署到生产环境

**阅读**: [部署指南](./DEPLOYMENT.md)

**推荐方案**：

1. **使用 Docker**（推荐）
```bash
docker-compose up -d
```

2. **使用 Systemd + Nginx**
```bash
# 配置 Gunicorn
gunicorn -c gunicorn_config.py app:app

# 配置 Nginx 反向代理
sudo systemctl start nginx

# 配置 Systemd 服务
sudo systemctl enable agentic-rag
sudo systemctl start agentic-rag
```

---

### 💻 参与开发

**阅读**: [开发指南](./DEVELOPMENT.md)

**开发流程**：

1. **设置开发环境**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **创建功能分支**
```bash
git checkout -b feature/new-feature
```

3. **编写代码和测试**
```bash
# 运行测试
pytest

# 代码格式化
black app/ scripts/

# 代码检查
flake8 app/ scripts/
```

4. **提交代码**
```bash
git commit -m "feat: add new feature"
git push origin feature/new-feature
```

---

### 🏗️ 了解 V2 架构

**阅读**: [V2 架构文档](./V2_ARCHITECTURE.md)

**核心特点**：
- **单一上下文对象**：所有信息在 `AgentContext` 中累积
- **增量式迭代**：基于完整历史上下文进行决策
- **多任务分解**：自动识别并拆解复杂查询
- **工具调用限制**：智能管理调用次数（search: 10次、web_search: 3次、python_code: 10次）
- **流式输出**：支持 Markdown 和 LaTeX 实时渲染

**工作流程**：
```
初始化 → Plan → Tool Using → Evaluate → 
(循环迭代) → Streaming Output → Finish
```

---

## 📂 文档目录

### 核心文档

| 文档 | 描述 | 更新日期 |
|------|------|----------|
| [README.md](../README.md) | 项目说明、快速开始、使用指南 | 2025-10-12 |
| [API_REFERENCE.md](./API_REFERENCE.md) | REST API 完整参考 | 2025-10-12 |
| [SECURITY.md](./SECURITY.md) | 安全机制和最佳实践 | 2025-10-12 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 部署指南（开发、生产、Docker） | 2025-10-12 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 开发指南（代码规范、测试、贡献） | 2025-10-12 |
| [V2_ARCHITECTURE.md](./V2_ARCHITECTURE.md) | V2 架构详细设计文档 | 2025-10-06 |

---

## 🔍 按主题浏览

### 入门教程

1. [安装和配置](../README.md#-快速开始)
2. [创建知识库](../README.md#-web-界面使用指南)
3. [上传文档](./API_REFERENCE.md#上传文档)
4. [开始问答](./API_REFERENCE.md#v2-增量式问答)

### API 使用

- [知识库管理 API](./API_REFERENCE.md#知识库管理-api)
- [文档管理 API](./API_REFERENCE.md#文档管理-api)
- [RAG 问答 API](./API_REFERENCE.md#rag-问答-api)
- [V2 Agent API](./API_REFERENCE.md#v2-agent-api)
- [工具管理 API](./API_REFERENCE.md#工具管理-api)

### 架构与设计

- [系统架构概览](../README.md#-系统架构概览)
- [V2 架构详解](./V2_ARCHITECTURE.md)
- [工具系统](./V2_ARCHITECTURE.md#工具系统)
- [提示词工程](./V2_ARCHITECTURE.md#提示词工程)

### 安全

- [多层安全防御](./SECURITY.md#多层安全防御)
- [Python 执行器安全](./SECURITY.md#python-执行器安全)
- [API 安全](./SECURITY.md#api-安全)
- [数据安全](./SECURITY.md#数据安全)
- [安全配置](./SECURITY.md#安全配置)
- [安全测试](./SECURITY.md#安全测试)

### 部署与运维

- [开发环境部署](./DEPLOYMENT.md#开发环境部署)
- [生产环境部署](./DEPLOYMENT.md#生产环境部署)
- [Docker 部署](./DEPLOYMENT.md#docker-部署)
- [性能优化](./DEPLOYMENT.md#性能优化)
- [监控与运维](./DEPLOYMENT.md#监控与运维)
- [故障排查](./DEPLOYMENT.md#故障排查)

### 开发

- [开发环境设置](./DEVELOPMENT.md#开发环境设置)
- [项目结构](./DEVELOPMENT.md#项目结构)
- [代码规范](./DEVELOPMENT.md#代码规范)
- [测试指南](./DEVELOPMENT.md#测试指南)
- [调试技巧](./DEVELOPMENT.md#调试技巧)
- [贡献指南](./DEVELOPMENT.md#贡献指南)

---

## 💡 使用场景

### 场景 1：企业知识库问答

**适用**：内部文档检索、规章制度查询、技术文档查找

**相关文档**：
- [快速开始](../README.md#-快速开始)
- [知识库管理 API](./API_REFERENCE.md#知识库管理-api)
- [文档管理 API](./API_REFERENCE.md#文档管理-api)

**示例**：
```bash
# 1. 创建知识库
curl -X POST http://localhost:5004/api/kb/create \
  -H "Content-Type: application/json" \
  -d '{"name": "安全生产知识库"}'

# 2. 上传文档
curl -X POST http://localhost:5004/api/docs/batch-upload/5 \
  -F "files=@安全制度.pdf" \
  -F "files=@操作规程.pdf"

# 3. 问答
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "高空作业的安全要求有哪些？",
    "kb_ids": [5]
  }'
```

---

### 场景 2：数学计算与数据分析

**适用**：科学计算、统计分析、数据处理

**相关文档**：
- [Python 代码执行器](../README.md#-python-代码执行器)
- [安全配置](./SECURITY.md#python-执行器安全)
- [V2 Agent API](./API_REFERENCE.md#v2-agent-api)

**示例**：
```bash
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "计算1到100的平方和，并求平均值",
    "stream": false
  }'
```

---

### 场景 3：复杂多任务处理

**适用**：多步骤查询、多角度分析、跨领域问题

**相关文档**：
- [V2 架构文档](./V2_ARCHITECTURE.md)
- [多任务分解流程](./V2_ARCHITECTURE.md#多任务分解流程)

**示例**：
```bash
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "计算100的阶乘，查询今天广州的天气，并告诉我高空作业的注意事项",
    "kb_ids": [5],
    "stream": true
  }'
```

---

## 🛠️ 实用工具

### 脚本工具

| 脚本 | 功能 | 使用方法 |
|------|------|----------|
| `scripts/analyze_io_log.py` | IO 日志分析 | `python scripts/analyze_io_log.py logs/*.jsonl` |
| `scripts/test_executor_security.py` | 执行器安全测试 | `python scripts/test_executor_security.py` |
| `scripts/trace_v2_agent_io.py` | V2 Agent 调试追踪 | `python scripts/trace_v2_agent_io.py` |

详见：[脚本工具使用](../README.md#️-脚本工具使用)

---

## ❓ 常见问题

### Q: 如何切换执行器类型？

**A**: 在 `config.py` 中设置或使用环境变量：
```bash
export PYTHON_EXECUTOR_TYPE=process_isolated  # HSL执行器（推荐）
export PYTHON_EXECUTOR_TYPE=default           # 默认执行器
```

详见：[安全配置](./SECURITY.md#切换执行器)

---

### Q: 如何查看 API 日志？

**A**: 日志位于 `logs/` 目录：
```bash
# 查看 IO 日志
tail -f logs/api_io_*.jsonl | jq .

# 分析日志
python scripts/analyze_io_log.py logs/api_io_*.jsonl

# 查看审计日志
tail -f logs/executor_audit.log
```

详见：[监控与运维](./DEPLOYMENT.md#监控与运维)

---

### Q: 如何部署到生产环境？

**A**: 推荐使用 Docker 或 Gunicorn + Nginx：

**Docker 方式**：
```bash
docker-compose up -d
```

**Gunicorn + Nginx 方式**：
```bash
# 使用 Gunicorn
gunicorn -c gunicorn_config.py app:app

# 配置 Nginx 反向代理
sudo systemctl start nginx
```

详见：[部署指南](./DEPLOYMENT.md)

---

### Q: 如何贡献代码？

**A**: 遵循开发流程：
1. Fork 项目
2. 创建功能分支
3. 编写代码和测试
4. 提交 Pull Request

详见：[贡献指南](./DEVELOPMENT.md#贡献指南)

---

## 📞 获取帮助

### 文档反馈

如果文档有错误或需要改进：
- 提交 Issue
- 提交 Pull Request
- 联系维护者

### 技术支持

- **GitHub Issues**: 报告 Bug 或提出功能建议
- **项目主页**: [GitHub Repository](https://github.com/CaiZhexi/Open_ReAct_Agent)

---

## 🔄 文档更新

| 日期 | 更新内容 |
|------|----------|
| 2025-11-02 | 开源准备：更新项目名称、修正文档引用、配置环境变量管理 |
| 2025-10-12 | 重构文档结构，新增 API_REFERENCE、DEPLOYMENT、DEVELOPMENT、SECURITY |
| 2025-10-06 | 新增 V2_ARCHITECTURE 架构文档 |

---

## 📊 文档统计

- **文档总数**: 6 个核心文档
- **总字数**: 约 50,000 字
- **代码示例**: 100+ 个
- **最后更新**: 2025-11-02

---

**欢迎使用 Open_ReAct_Agent！** 

如有任何问题或建议，欢迎提交 Issue 或 Pull Request。

---

**文档版本**：v2.0  
**最后更新**：2025年11月2日  
**维护者**：Open_ReAct_Agent Team
