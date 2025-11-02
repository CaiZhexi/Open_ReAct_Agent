# API 参考文档

> Agentic-RAG REST API 完整参考

本文档提供所有 REST API 端点的详细说明、参数、返回格式和使用示例。

---

## 📋 目录

- [基础信息](#基础信息)
- [认证与授权](#认证与授权)
- [通用响应格式](#通用响应格式)
- [知识库管理 API](#知识库管理-api)
- [文档管理 API](#文档管理-api)
- [RAG 问答 API](#rag-问答-api)
- [V2 Agent API](#v2-agent-api)
- [工具管理 API](#工具管理-api)
- [系统管理 API](#系统管理-api)
- [错误码说明](#错误码说明)

---

## 基础信息

### Base URL

```
http://localhost:5004/api
```

### 内容类型

所有请求和响应均使用 JSON 格式：

```
Content-Type: application/json
```

### 字符编码

```
UTF-8
```

---

## 认证与授权

当前版本暂不需要认证。后续版本将支持 API Key 认证。

---

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "success": false,
  "message": "错误信息",
  "error": "详细错误"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 知识库管理 API

### 获取知识库列表

获取所有知识库及其统计信息。

**接口**：`GET /api/kb/list`

**请求参数**：无

**响应示例**：

```json
{
  "success": true,
  "data": [
    {
      "id": 5,
      "name": "安全生产知识库",
      "description": "企业安全生产相关文档",
      "created_at": "2025-10-01 10:00:00",
      "document_count": 150,
      "vector_stats": {
        "total_vectors": 5000,
        "dimensions": 1024,
        "unique_documents": 150
      },
      "status": "ready",
      "processing_progress": 1.0,
      "is_ready": true
    }
  ],
  "message": "获取知识库列表成功"
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 知识库ID |
| name | string | 知识库名称 |
| description | string | 知识库描述 |
| created_at | string | 创建时间 |
| document_count | integer | 文档数量 |
| vector_stats | object | 向量统计信息 |
| status | string | 状态：`ready`/`processing` |
| processing_progress | float | 处理进度（0.0-1.0） |
| is_ready | boolean | 是否就绪 |

---

### 创建知识库

创建新的知识库。

**接口**：`POST /api/kb/create`

**请求参数**：

```json
{
  "name": "知识库名称",
  "description": "知识库描述（可选）"
}
```

**请求示例**：

```bash
curl -X POST http://localhost:5004/api/kb/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术文档库",
    "description": "存储技术文档和API手册"
  }'
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "id": 6,
    "name": "技术文档库",
    "description": "存储技术文档和API手册",
    "created_at": "2025-10-12 14:30:00"
  },
  "message": "知识库创建成功"
}
```

---

### 获取知识库详情

获取指定知识库的详细信息。

**接口**：`GET /api/kb/{kb_id}`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | integer | 是 | 知识库ID |

**响应示例**：

```json
{
  "success": true,
  "data": {
    "id": 5,
    "name": "安全生产知识库",
    "description": "企业安全生产相关文档",
    "created_at": "2025-10-01 10:00:00",
    "document_count": 150,
    "vector_stats": {
      "total_vectors": 5000,
      "dimensions": 1024
    }
  },
  "message": "获取知识库详情成功"
}
```

---

### 重命名知识库

修改知识库名称和描述。

**接口**：`PUT /api/kb/{kb_id}/rename`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | integer | 是 | 知识库ID |

**请求参数**：

```json
{
  "name": "新名称",
  "description": "新描述（可选）"
}
```

**响应示例**：

```json
{
  "success": true,
  "message": "知识库重命名成功"
}
```

---

### 删除知识库

删除知识库及其所有文档和向量。

**接口**：`DELETE /api/kb/{kb_id}/delete`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | integer | 是 | 知识库ID |

**响应示例**：

```json
{
  "success": true,
  "message": "知识库删除成功"
}
```

**注意**：此操作不可逆，将永久删除所有相关数据。

---

## 文档管理 API

### 上传文档

上传单个文档到指定知识库。

**接口**：`POST /api/docs/upload/{kb_id}`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | integer | 是 | 知识库ID |

**请求格式**：`multipart/form-data`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | 文档文件 |

**支持格式**：txt, pdf, docx, xlsx, md

**文件大小限制**：16MB

**请求示例**：

```bash
curl -X POST http://localhost:5004/api/docs/upload/5 \
  -F "file=@document.pdf"
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "doc_id": 123,
    "filename": "document.pdf",
    "status": "queued"
  },
  "message": "文档上传成功，已加入处理队列"
}
```

---

### 批量上传文档

批量上传多个文档到指定知识库。

**接口**：`POST /api/docs/batch-upload/{kb_id}`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | integer | 是 | 知识库ID |

**请求格式**：`multipart/form-data`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| files | file[] | 是 | 文档文件列表 |

**请求示例**：

```bash
curl -X POST http://localhost:5004/api/docs/batch-upload/5 \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.docx"
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "uploaded": 3,
    "failed": 0,
    "details": [
      {"filename": "doc1.pdf", "status": "queued", "doc_id": 124},
      {"filename": "doc2.pdf", "status": "queued", "doc_id": 125},
      {"filename": "doc3.docx", "status": "queued", "doc_id": 126}
    ]
  },
  "message": "批量上传完成：3个成功，0个失败"
}
```

---

### 获取文档列表

获取指定知识库的所有文档。

**接口**：`GET /api/docs/list/{kb_id}`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | integer | 是 | 知识库ID |

**响应示例**：

```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "filename": "document.pdf",
      "upload_time": "2025-10-12 10:00:00",
      "status": "completed",
      "chunk_count": 50
    }
  ],
  "message": "获取文档列表成功"
}
```

---

### 删除文档

删除指定文档及其分块和向量。

**接口**：`DELETE /api/docs/delete/{doc_id}`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| doc_id | integer | 是 | 文档ID |

**响应示例**：

```json
{
  "success": true,
  "message": "文档删除成功"
}
```

---

### 获取处理状态

获取文档处理队列状态。

**接口**：`GET /api/docs/queue-status/{kb_id}`

**路径参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kb_id | integer | 是 | 知识库ID |

**响应示例**：

```json
{
  "success": true,
  "data": {
    "kb_status": {
      "status": "processing",
      "total_pending_docs": 10,
      "processed_docs": 5,
      "processing_progress": 0.5
    },
    "queue_stats": {
      "pending": 10,
      "processing": 1,
      "completed": 5,
      "failed": 0
    }
  },
  "message": "获取队列状态成功"
}
```

---

## RAG 问答 API

### V1 简单问答

传统 RAG 问答接口。

**接口**：`POST /api/rag/chat`

**请求参数**：

```json
{
  "query": "用户问题",
  "kb_ids": [5],
  "top_k": 5
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | 是 | - | 用户问题 |
| kb_ids | integer[] | 否 | [] | 知识库ID列表 |
| top_k | integer | 否 | 5 | 检索数量 |

**响应示例**：

```json
{
  "success": true,
  "data": {
    "answer": "根据文档，高空作业需要...",
    "sources": [
      {
        "doc_id": 123,
        "filename": "safety_guide.pdf",
        "chunk_id": 456,
        "content": "相关内容片段...",
        "score": 0.95
      }
    ],
    "confidence": 0.85
  },
  "message": "回答生成成功"
}
```

---

### V1 Agentic 问答

调度器驱动的智能问答接口，支持流式输出。

**接口**：`POST /api/rag/agentic-chat`

**请求参数**：

```json
{
  "query": "用户问题",
  "kb_ids": [5],
  "stream": true,
  "max_steps": 10
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | 是 | - | 用户问题 |
| kb_ids | integer[] | 否 | [] | 知识库ID列表 |
| stream | boolean | 否 | false | 是否流式输出 |
| max_steps | integer | 否 | 10 | 最大执行步数 |

**响应格式**：

#### 非流式响应

```json
{
  "success": true,
  "data": {
    "answer": "完整答案...",
    "steps": [
      {
        "step": 1,
        "action": "search",
        "result": "检索到相关文档...",
        "timestamp": "2025-10-12 14:30:00"
      }
    ],
    "sources": [...],
    "confidence": 0.90
  },
  "message": "回答生成成功"
}
```

#### 流式响应（Server-Sent Events）

```
data: {"event": "step", "data": {"step": 1, "action": "search", "status": "start"}}

data: {"event": "step", "data": {"step": 1, "action": "search", "status": "complete", "result": "..."}}

data: {"event": "answer_chunk", "data": {"chunk": "答案片段"}}

data: {"event": "done", "data": {"confidence": 0.90}}
```

---

## V2 Agent API

### V2 增量式问答

V2 增量式上下文迭代架构，支持多任务分解和流式输出。

**接口**：`POST /api/v2/chat`

**请求参数**：

```json
{
  "query": "用户问题",
  "kb_ids": [5],
  "conversation_history": [],
  "stream": true
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | 是 | - | 用户问题 |
| kb_ids | integer[] | 否 | [] | 知识库ID列表 |
| conversation_history | array | 否 | [] | 对话历史 |
| stream | boolean | 否 | true | 是否流式输出 |

**对话历史格式**：

```json
[
  {"role": "user", "content": "之前的问题"},
  {"role": "assistant", "content": "之前的回答"}
]
```

**响应格式**：

#### 非流式响应

```json
{
  "success": true,
  "data": {
    "answer": "完整答案...",
    "context": {
      "user_query": "用户问题",
      "subtasks": [
        {"id": 1, "description": "子任务1", "status": "completed"},
        {"id": 2, "description": "子任务2", "status": "completed"}
      ],
      "tools_log": [
        {
          "tool": "python_code",
          "query": "计算100!",
          "result_summary": "计算完成",
          "execution_time": 0.5
        }
      ],
      "iteration_count": 3
    },
    "confidence": 0.95,
    "process_log": {...}
  },
  "message": "回答生成成功"
}
```

#### 流式响应（Server-Sent Events）

```
data: {"event": "start", "data": {}}

data: {"event": "plan_start", "data": {}}

data: {"event": "plan_complete", "data": {"plan": {"action": "python_code", "args": {...}}}}

data: {"event": "tool_start", "data": {"tool": "python_code", "args": {...}}}

data: {"event": "tool_end", "data": {"tool": "python_code", "result_summary": "...", "execution_time": 0.5}}

data: {"event": "evaluate", "data": {"should_answer": false, "reason": "..."}}

data: {"event": "answer_start", "data": {}}

data: {"event": "answer_chunk", "data": {"chunk": "答案片段"}}

data: {"event": "answer", "data": {"answer": "完整答案"}}

data: {"event": "evaluate", "data": {"confidence": 0.95, "reason": "..."}}

data: {"event": "done", "data": {"sources": [...], "process_log": {...}}}
```

**事件类型说明**：

| 事件 | 说明 |
|------|------|
| start | 开始处理 |
| plan_start | 规划开始 |
| plan_complete | 规划完成 |
| tool_start | 工具开始执行 |
| tool_end | 工具执行完成 |
| evaluate | 评估信息是否充分 |
| answer_start | 答案生成开始 |
| answer_chunk | 答案片段（流式） |
| answer | 完整答案 |
| done | 处理完成 |

---

### V2 架构信息

获取 V2 架构的配置和状态信息。

**接口**：`GET /api/v2/info`

**响应示例**：

```json
{
  "success": true,
  "data": {
    "version": "v2.0",
    "architecture": "incremental_context_iteration",
    "features": [
      "task_decomposition",
      "tool_call_limits",
      "streaming_output",
      "conversation_history"
    ],
    "tool_limits": {
      "search": 10,
      "web_search": 3,
      "python_code": 10
    },
    "config": {
      "max_iterations": 15,
      "confidence_threshold": 0.7
    }
  },
  "message": "V2架构信息"
}
```

---

## 工具管理 API

### 获取工具列表

获取所有已注册的工具信息。

**接口**：`GET /api/rag/tools`

**响应示例**：

```json
{
  "success": true,
  "data": [
    {
      "name": "search",
      "description": "知识库检索",
      "required_params": ["query"],
      "optional_params": ["top_k"],
      "status": "active"
    },
    {
      "name": "web_search",
      "description": "网络搜索",
      "required_params": ["query"],
      "optional_params": ["top_k"],
      "status": "active"
    },
    {
      "name": "python_code",
      "description": "Python代码执行",
      "required_params": ["query"],
      "optional_params": [],
      "status": "active"
    }
  ],
  "message": "获取工具列表成功"
}
```

---

### 获取工具统计

获取工具调用统计信息。

**接口**：`GET /api/rag/tools/stats`

**响应示例**：

```json
{
  "success": true,
  "data": {
    "search": {
      "total_calls": 1500,
      "success_count": 1480,
      "failure_count": 20,
      "avg_execution_time": 0.8,
      "success_rate": 0.987
    },
    "web_search": {
      "total_calls": 500,
      "success_count": 490,
      "failure_count": 10,
      "avg_execution_time": 1.2,
      "success_rate": 0.980
    },
    "python_code": {
      "total_calls": 800,
      "success_count": 750,
      "failure_count": 50,
      "avg_execution_time": 0.5,
      "success_rate": 0.937
    }
  },
  "message": "获取工具统计成功"
}
```

---

## 系统管理 API

### 健康检查

检查系统健康状态和配置信息。

**接口**：`GET /api/health`

**响应示例**：

```json
{
  "status": "ok",
  "message": "RAG知识库系统运行正常",
  "config": {
    "embed_model": "Qwen/Qwen3-Embedding-8B",
    "chat_model": "qwen-flash",
    "embed_dimensions": 1024,
    "max_file_size": "16MB",
    "allowed_extensions": ["txt", "pdf", "docx", "xlsx", "md"]
  }
}
```

---

### IO 日志信息

获取 IO 日志统计信息。

**接口**：`GET /api/io-logs`

**响应示例**：

```json
{
  "enabled": true,
  "log_file": "logs/api_io_20251012_143000.jsonl",
  "statistics": {
    "total_requests": 1500,
    "total_llm_calls": 3000,
    "avg_request_duration": 2.5,
    "avg_llm_duration": 1.2
  }
}
```

---

## 错误码说明

### 通用错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求参数格式和内容 |
| 404 | 资源不存在 | 确认资源ID是否正确 |
| 500 | 服务器内部错误 | 查看服务器日志，联系管理员 |

### 业务错误码

| 错误信息 | 原因 | 处理建议 |
|----------|------|----------|
| 知识库名称已存在 | 创建知识库时名称重复 | 使用不同的名称 |
| 知识库不存在 | 指定的知识库ID不存在 | 确认知识库ID |
| 文件格式不支持 | 上传的文件格式不在允许列表中 | 使用支持的格式 |
| 文件大小超限 | 文件大小超过16MB | 压缩或拆分文件 |
| 工具调用次数达到上限 | V2 Agent 工具调用超限 | 稍后重试或简化问题 |
| 代码执行超时 | Python代码执行时间超过限制 | 优化代码或增加超时时间 |

---

## 使用示例

### Python 示例

```python
import requests

# 基础URL
BASE_URL = "http://localhost:5004/api"

# 创建知识库
def create_kb():
    response = requests.post(
        f"{BASE_URL}/kb/create",
        json={
            "name": "技术文档库",
            "description": "存储技术文档"
        }
    )
    return response.json()

# 上传文档
def upload_document(kb_id, file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/docs/upload/{kb_id}",
            files={"file": f}
        )
    return response.json()

# V2 问答（非流式）
def v2_chat(query, kb_ids):
    response = requests.post(
        f"{BASE_URL}/v2/chat",
        json={
            "query": query,
            "kb_ids": kb_ids,
            "stream": False
        }
    )
    return response.json()

# V2 问答（流式）
def v2_chat_stream(query, kb_ids):
    response = requests.post(
        f"{BASE_URL}/v2/chat",
        json={
            "query": query,
            "kb_ids": kb_ids,
            "stream": True
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            # 解析 SSE 格式
            if line.startswith(b'data: '):
                import json
                data = json.loads(line[6:])
                print(data)
```

### JavaScript 示例

```javascript
// 基础URL
const BASE_URL = "http://localhost:5004/api";

// 创建知识库
async function createKB() {
  const response = await fetch(`${BASE_URL}/kb/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: '技术文档库',
      description: '存储技术文档'
    })
  });
  return await response.json();
}

// V2 问答（流式）
async function v2ChatStream(query, kbIds) {
  const response = await fetch(`${BASE_URL}/v2/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: query,
      kb_ids: kbIds,
      stream: true
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6));
        console.log(event);
        
        // 处理不同事件
        if (event.event === 'answer_chunk') {
          // 显示答案片段
          console.log(event.data.chunk);
        }
      }
    }
  }
}
```

### cURL 示例

```bash
# 创建知识库
curl -X POST http://localhost:5004/api/kb/create \
  -H "Content-Type: application/json" \
  -d '{"name": "技术文档库", "description": "存储技术文档"}'

# 上传文档
curl -X POST http://localhost:5004/api/docs/upload/5 \
  -F "file=@document.pdf"

# V2 问答（非流式）
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "高空作业的安全要求有哪些？",
    "kb_ids": [5],
    "stream": false
  }'

# V2 问答（流式）
curl -X POST http://localhost:5004/api/v2/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "计算100的阶乘",
    "stream": true
  }' \
  --no-buffer
```

---

## 最佳实践

### 1. 错误处理

始终检查 `success` 字段，处理错误情况：

```python
response = requests.post(url, json=data)
result = response.json()

if not result['success']:
    print(f"错误：{result['message']}")
    return

# 处理成功情况
data = result['data']
```

### 2. 流式响应处理

流式响应需要特殊处理：

```python
response = requests.post(url, json=data, stream=True)

for line in response.iter_lines():
    if line and line.startswith(b'data: '):
        event = json.loads(line[6:])
        handle_event(event)
```

### 3. 超时设置

设置合理的超时时间：

```python
# 非流式请求
response = requests.post(url, json=data, timeout=30)

# 流式请求（connect timeout, read timeout）
response = requests.post(url, json=data, stream=True, timeout=(5, 300))
```

### 4. 重试机制

实现简单的重试逻辑：

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_api(url, data):
    response = requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    return response.json()
```

---

## 更新历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2025-10-12 | 初始版本 |

---

**文档版本**：v1.0  
**最后更新**：2025年10月12日  
**维护者**：Agentic-RAG Team

