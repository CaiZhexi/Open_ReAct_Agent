# V2 Agentic RAG 架构详解

> V2 增量式上下文迭代架构 - 完整设计文档

---

## 📋 目录

1. [架构概述](#架构概述)
2. [核心设计理念](#核心设计理念)
3. [系统流程图](#系统流程图)
4. [核心组件](#核心组件)
5. [工作流详解](#工作流详解)
6. [数据结构](#数据结构)
7. [工具系统](#工具系统)
8. [提示词工程](#提示词工程)
9. [流式输出](#流式输出)
10. [错误处理与容错](#错误处理与容错)

---

## 架构概述

V2 Agentic RAG 采用 **增量式上下文迭代** 架构，核心理念是在单一上下文对象中累积所有信息，确保 Agent 在统一的认知空间中进行推理和决策。

### 核心特点

- **单一上下文对象**：所有信息（思维链、工具调用、证据）在一个 `AgentContext` 中累积
- **增量式迭代**：每次迭代都基于完整的历史上下文，避免信息孤岛
- **多任务分解**：自动识别并拆解复杂查询为多个子任务
- **工具调用限制**：智能管理工具调用次数，避免过度调用
- **完整性检查**：严格验证所有子任务完成状态
- **流式输出**：支持 Markdown 和 LaTeX 实时渲染

### 架构对比

| 特性 | V1 架构 | V2 架构 |
|------|---------|---------|
| 上下文管理 | 分散在多个组件 | 单一 AgentContext 对象 |
| 任务处理 | 单任务顺序处理 | 多任务并行跟踪 |
| 工具限制 | 全局迭代次数限制 | 按工具类型独立限制 |
| 完整性检查 | 简单评估 | 严格逐项检查 |
| 流式输出 | 不支持 | 完整支持 |
| 状态追踪 | 基本 | 详细（子任务、证据、评估） |

---

## 核心设计理念

### 1. 增量式上下文迭代

```
初始上下文
    ↓
Plan 1 → Tool 1 → Evidence 1
    ↓
Plan 2 → Tool 2 → Evidence 1 + Evidence 2
    ↓
Plan 3 → Tool 3 → Evidence 1 + Evidence 2 + Evidence 3
    ↓
Evaluate（信息充分？）
    ↓
Generate Answer（基于所有证据）
```

### 2. 工具平等原则

所有工具（search, web_search, python_code）在同一层级，由 Agent 根据任务需求动态选择：

- **search**：知识库检索（内部文档）
- **web_search**：网络搜索（实时信息）
- **python_code**：代码执行（计算分析）

### 3. 任务完整性保证

多任务场景下，系统确保：
- 识别所有子任务
- 跟踪每个子任务状态
- 验证所有任务完成
- 汇总所有任务结果

---

## 系统流程图

### 总体流程

```
用户查询 → 初始化上下文 → Plan → Execute Tool → Update Evidence → Evaluate → Answer
          ↑_____________↓ (迭代循环，直到信息充分)
```

### 详细迭代流程

**序列图展示了 V2 Agent 在单次迭代中的完整交互过程**：

1. 用户提交查询 → Agent 初始化上下文
2. 迭代循环开始
   - Agent 请求 LLM 规划 (Plan)
   - LLM 返回决策 JSON
   - 根据决策执行工具或分解任务
   - 检查工具调用次数限制
   - 执行工具并更新上下文
   - Agent 请求 LLM 评估 (Evaluate)
   - 判断信息是否充分
3. 信息充分后生成答案
   - 流式输出答案给用户
   - 最终评估答案质量

### 多任务分解流程

```
复杂查询（如："计算100的阶乘，查询今天的天气，告诉我安全规程"）
    ↓
识别多个子任务
    ↓
子任务1: 数学计算 → python_code → 完成
子任务2: 实时信息 → web_search → 完成
子任务3: 知识检索 → search → 完成
    ↓
所有子任务完成 → 汇总结果 → 生成答案
```

---

## 核心组件

### 1. V2Agent

主控制器，协调整个推理流程。

```python
class V2Agent:
    """V2 Agentic RAG Agent"""
    
    def run(self, query: str, kb_ids: List[int] = None) -> Dict:
        """非流式运行"""
        
    def run_stream(self, query: str, kb_ids: List[int] = None) -> Generator:
        """流式运行，逐步输出事件"""
        
    def _plan(self, context: AgentContext) -> Dict:
        """规划下一步行动"""
        
    def _execute_tool(self, context: AgentContext, plan: Dict) -> Dict:
        """执行工具调用"""
        
    def _evaluate(self, context: AgentContext) -> Dict:
        """评估信息是否充分"""
        
    def _generate_answer_stream(self, context: AgentContext) -> Generator:
        """流式生成答案"""
        
    def _final_evaluate(self, context: AgentContext) -> Dict:
        """最终质量评估"""
```

### 2. AgentContext

增量式上下文对象，存储所有状态和历史。

```python
@dataclass
class AgentContext:
    """增量式上下文对象"""
    
    # 基础信息
    user_query: str                              # 用户查询
    kb_ids: List[int]                            # 知识库ID
    kb_names: Dict[int, str]                     # 知识库名称映射
    
    # 任务分解
    subtasks: List[SubTask]                      # 子任务列表
    current_subtask_id: Optional[int]            # 当前处理的任务
    
    # 规划
    plan: Optional[str]                          # 当前规划
    
    # 证据存储（分类）
    evidence: Dict[str, List[Any]]               # 按类型分类的证据
    # - kb_retrieval: 知识库检索结果
    # - web_search: 网络搜索结果
    # - python_execution: 代码执行结果
    
    # 工具调用
    tools_log: List[ToolCallLog]                 # 工具调用历史
    tool_call_counts: Dict[str, int]             # 调用次数统计
    tool_call_limits: Dict[str, int]             # 调用次数上限
    
    # 评估历史
    evaluations: List[Dict[str, Any]]            # 评估记录
    
    # 最终结果
    final_answer: Optional[str]                  # 最终答案
    final_evaluation: Optional[Dict]             # 最终评估
    
    # 元数据
    iteration_count: int                         # 迭代次数
    status: str                                  # running, done, error
```

### 3. SubTask

子任务对象，用于多任务场景。

```python
@dataclass
class SubTask:
    """子任务"""
    id: int                                      # 任务ID
    description: str                             # 任务描述
    required_tool: Optional[str]                 # 所需工具
    status: str                                  # pending, in_progress, completed, failed
    evidence_key: Optional[str]                  # 对应的证据key
```

### 4. ToolCallLog

工具调用日志，记录每次工具执行。

```python
@dataclass
class ToolCallLog:
    """工具调用日志"""
    tool: str                                    # 工具名称
    query: str                                   # 查询内容
    args: Dict[str, Any]                         # 参数
    result_summary: str                          # 结果摘要
    full_result: Any                             # 完整结果
    timestamp: float                             # 时间戳
    execution_time: float                        # 执行时间
    subtask_id: Optional[int]                    # 关联的子任务ID
```

---

## 工作流详解

### Phase 1: Plan（规划）

**目标**：分析当前上下文，决定下一步行动

**输入**：
- 当前时间
- 上下文摘要（用户查询、知识库信息、工具使用情况、子任务状态、历史记录）
- 是否有可用知识库

**输出**：
```json
{
  "action": "search | web_search | python_code | decompose_tasks | ready_to_answer",
  "args": {
    "query": "具体查询内容",
    "top_k": 5
  },
  "reasoning": "选择这个工具的理由"
}
```

**决策逻辑**：

1. **多任务检测**：
   - 第一轮规划时，检查是否包含多个子问题
   - 如果是，返回 `decompose_tasks`

2. **工具调用限制检查**：
   - 检查每个工具的调用次数
   - 标记已达上限的工具（不可再调用）

3. **工具选择优先级**：
   - 社交对话（打招呼） → `ready_to_answer`
   - 涉及数学/计算 → `python_code`
   - 需要实时信息 → `web_search`
   - 需要专业知识 → `search`（如果有知识库）
   - 信息充分 → `ready_to_answer`

### Phase 2: Tool Using（工具执行）

**目标**：执行选定的工具，获取信息

**工具类型**：

#### 2.1 search - 知识库检索

```python
{
    "action": "search",
    "args": {
        "query": "检索关键词",
        "top_k": 5
    }
}
```

**执行流程**：
1. 调用向量搜索工具
2. 返回相关文档片段
3. 存储到 `evidence['kb_retrieval']`

**限制**：最多 10 次调用

#### 2.2 web_search - 网络搜索

```python
{
    "action": "web_search",
    "args": {
        "query": "搜索关键词",
        "top_k": 5
    }
}
```

**执行流程**：
1. 调用 Metaso 搜索 API
2. 返回网页标题、内容、URL
3. 存储到 `evidence['web_search']`

**限制**：最多 3 次调用

#### 2.3 python_code - Python 代码执行

```python
{
    "action": "python_code",
    "args": {
        "query": "描述需要执行的计算任务"
    }
}
```

**执行流程**：
1. 生成 Python 代码
2. 在沙箱环境中执行
3. 返回输出结果
4. 存储到 `evidence['python_execution']`

**限制**：最多 10 次调用

#### 2.4 decompose_tasks - 任务分解

```python
{
    "action": "decompose_tasks",
    "subtasks": [
        {"id": 1, "description": "计算100的阶乘", "tool": "python_code"},
        {"id": 2, "description": "查询广州天气", "tool": "web_search"}
    ]
}
```

**执行流程**：
1. 创建子任务列表
2. 标记所有任务为 `pending`
3. 选择第一个任务开始处理

**子任务跟踪**：
- 每次工具调用时关联到对应子任务
- 成功执行后标记为 `completed`
- 失败则标记为 `failed`

### Phase 3: Evaluate（评估）

**目标**：判断当前信息是否足以生成答案

**输入**：
- 用户查询
- 上下文摘要
- 已收集证据详情

**输出**：
```json
{
  "should_answer": true/false,
  "reason": "评估理由",
  "confidence": 0.8
}
```

**评估标准**：

1. **完整性检查**：
   - 如果有子任务，检查是否全部完成
   - 每个子任务是否都有对应证据

2. **质量评估**：
   - 证据是否相关
   - 证据是否充分
   - 证据是否新鲜（实时性问题）

3. **决策**：
   - 所有子任务完成且证据充分 → `should_answer = true`
   - 任一子任务缺失或证据不足 → `should_answer = false`

**特殊情况**：
- 工具达到调用上限 → 强制 `should_answer = true`
- 评估出错 → 默认 `should_answer = true`

### Phase 4: Streaming Output（流式输出）

**目标**：生成最终答案并实时输出

**输入**：
- 用户查询
- 所有证据详情

**输出格式**：
- 纯 Markdown 文本
- 内嵌 LaTeX 数学公式
- 支持逐字流式传输

**格式规范**：

1. **数学公式**：
   - 行内：`$f(x) = x^2$`
   - 块级：
     ```
     $$
     \int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
     $$
     ```

2. **Markdown 元素**：
   - 标题（# ~ ######）
   - 列表（有序、无序）
   - 表格
   - 代码块（```语言）
   - 粗体、斜体

3. **禁止使用**：
   - HTML 标签
   - `\(...\)` 或 `\[...\]` LaTeX 定界符
   - 自定义占位符

### Phase 5: Finish（完成）

**目标**：评估答案质量，计算置信度

**输入**：
- 用户查询
- 生成的答案
- 上下文摘要（工具调用、子任务完成情况）

**输出**：
```json
{
  "confidence": 0.85,
  "reason": "详细评估理由"
}
```

**评估维度**：

1. **答案表达质量**（30%）：
   - 结构清晰、逻辑连贯
   - 语言专业、易于理解
   - Markdown 格式规范

2. **信息来源完整性**（40%）⭐ 最重要：
   - 所有子问题是否都有答案
   - 是否调用了必要的工具
   - 是否避免"无法回答"的推脱

3. **工具调用适当性**（30%）：
   - 是否选择了正确的工具类型
   - 是否进行了足够次数的迭代
   - 是否避免了不必要的重复调用

**置信度标准**：
- 0.9-1.0：优秀 - 所有子问题完整回答
- 0.7-0.9：良好 - 主要问题回答充分
- 0.5-0.7：一般 - 部分问题回答
- 0.3-0.5：较差 - 多数问题未充分回答
- <0.3：很差 - 基本未回答

---

## 数据结构

### 上下文状态转换

```
Initial State:
{
  iteration_count: 0,
  status: "running",
  subtasks: [],
  evidence: {},
  tools_log: [],
  tool_call_counts: {search: 0, web_search: 0, python_code: 0}
}

After Task Decompose:
{
  iteration_count: 0,
  status: "running",
  subtasks: [
    {id: 1, status: "pending", ...},
    {id: 2, status: "pending", ...}
  ],
  evidence: {},
  tools_log: [],
  tool_call_counts: {search: 0, web_search: 0, python_code: 0}
}

After First Tool Call:
{
  iteration_count: 1,
  status: "running",
  subtasks: [
    {id: 1, status: "completed", evidence_key: "python_execution"},
    {id: 2, status: "pending", ...}
  ],
  evidence: {
    "python_execution": [{code: "...", output: "..."}]
  },
  tools_log: [
    {tool: "python_code", query: "...", subtask_id: 1, ...}
  ],
  tool_call_counts: {search: 0, web_search: 0, python_code: 1}
}

After All Tasks Complete:
{
  iteration_count: 3,
  status: "done",
  subtasks: [
    {id: 1, status: "completed", evidence_key: "python_execution"},
    {id: 2, status: "completed", evidence_key: "web_search"}
  ],
  evidence: {
    "python_execution": [{...}],
    "web_search": [{...}]
  },
  tools_log: [{...}, {...}, {...}],
  tool_call_counts: {search: 0, web_search: 1, python_code: 1},
  final_answer: "完整答案...",
  final_evaluation: {confidence: 0.9, reason: "..."}
}
```

### 事件流格式

流式运行时，按顺序输出以下事件：

```python
# 1. 开始
{"event": "start", "data": {}}

# 2. 规划开始
{"event": "plan_start", "data": {}}

# 3. 规划完成
{"event": "plan_complete", "data": {
    "plan": {
        "action": "python_code",
        "args": {"query": "计算100!"},
        "reasoning": "需要精确计算"
    }
}}

# 4. 工具开始
{"event": "tool_start", "data": {
    "tool": "python_code",
    "reasoning": "需要精确计算",
    "args": {"query": "计算100!"}
}}

# 5. 工具结束
{"event": "tool_end", "data": {
    "tool": "python_code",
    "result_summary": "代码执行完成: 9332621544...",
    "execution_time": 0.234,
    "code": "...",
    "output": "..."
}}

# 6. 评估
{"event": "evaluate", "data": {
    "should_answer": false,
    "reason": "任务1已完成，任务2待处理",
    "timestamp": 1234567890.123
}}

# 7-11. 重复 2-6 直到信息充分

# 12. 答案开始
{"event": "answer_start", "data": {}}

# 13. 答案片段（多次）
{"event": "answer_chunk", "data": {"chunk": "计算"}}
{"event": "answer_chunk", "data": {"chunk": "100"}}
{"event": "answer_chunk", "data": {"chunk": "的阶乘"}}
...

# 14. 完整答案
{"event": "answer", "data": {"answer": "完整答案文本"}}

# 15. 最终评估
{"event": "evaluate", "data": {
    "confidence": 0.95,
    "reason": "所有任务完成，答案准确"
}}

# 16. 完成
{"event": "done", "data": {
    "sources": [...],
    "process_log": {...}
}}
```

---

## 工具系统

### 工具调用次数管理

```python
# 默认限制
tool_call_limits = {
    'search': 10,        # 知识库检索
    'web_search': 3,     # 网络搜索
    'python_code': 10    # 代码执行
}

# 实时统计
tool_call_counts = {
    'search': 2,         # 已调用2次
    'web_search': 3,     # 已达上限
    'python_code': 5     # 还可调用5次
}

# 使用情况摘要
"""
- search: 2/10次 ✅ 剩余8次
- web_search: 3/3次 ❌ 已达上限，不可再调用
- python_code: 5/10次 ✅ 剩余5次
"""
```

### 工具选择策略

```python
def select_tool(query, context):
    """根据查询和上下文选择合适的工具"""
    
    # 1. 检查是否达到上限
    if not context.can_call_tool(tool_name):
        return "ready_to_answer"  # 强制结束
    
    # 2. 多任务检测
    if is_multi_task(query) and not context.subtasks:
        return "decompose_tasks"
    
    # 3. 工具类型判断
    if needs_calculation(query):
        return "python_code"
    elif needs_realtime_info(query):
        return "web_search"
    elif needs_kb_knowledge(query) and context.kb_ids:
        return "search"
    else:
        return "ready_to_answer"
```

---

## 提示词工程

### Plan 提示词结构

```
# 系统角色定义
你是一个 ReAct 智能体...

⏰ 当前时间：2025年10月6日 14:30:00

【用户问题】
计算100的阶乘，并查询今天广州的天气

【可用知识库】
- [5] 安全生产知识库

【工具使用情况】
- search: 0/10次 ✅ 剩余10次
- web_search: 0/3次 ✅ 剩余3次
- python_code: 0/10次 ✅ 剩余10次

# 可用工具定义
## 1. search - 知识库检索
...

## 2. web_search - 网络搜索
...

## 3. python_code - Python 代码执行
...

## 4. decompose_tasks - 任务分解
...

## 5. ready_to_answer - 准备回答
...

# 决策流程
...

【输出格式】
仅返回一个 JSON 对象：
{"action": "工具名", "args": {...}, "reasoning": "..."}

请决策：
```

### Evaluate 提示词结构

```
# 系统角色定义
你是一个信息充分性评估专家...

⏰ 当前时间：2025年10月6日 14:30:00

【用户问题】
计算100的阶乘，并查询今天广州的天气

【工具使用情况】
- python_code: 1/10次 ✅ 剩余9次
- web_search: 0/3次 ✅ 剩余3次

【子任务列表】
✅ 任务1: 计算100的阶乘 [需要: python_code]
⏳ 任务2: 查询今天广州的天气 [需要: web_search]

【工具调用历史】
1. python_code(计算100的阶乘) [任务1] → 代码执行完成: 93326215443944152681...

【已收集证据】
- python_execution: 1 条

【已收集证据详情】
【python_execution】
1. {
  "code": "...",
  "output": "100! = 93326215443944152681..."
}

# 多任务完整性检查
...

【输出格式】
{"should_answer": true/false, "reason": "...", "confidence": 0.8}

请评估：
```

### Answer 提示词结构

```
# 系统角色定义
你是一个专业问答助手...

⏰ 当前时间：2025年10月6日 14:30:00

【用户问题】
计算100的阶乘，并查询今天广州的天气

【证据】
【python_execution】
1. {
  "code": "import math\nresult = math.factorial(100)\nprint(f'100! = {result}')",
  "output": "100! = 93326215443944152681..."
}

【web_search】
1. {
  "results": [
    {
      "title": "广州天气预报",
      "content": "今天广州多云，温度25-32℃...",
      "url": "..."
    }
  ]
}

# 输出格式规范 v1.0（Markdown + LaTeX 统一渲染）
...

请基于证据生成最终答案（纯Markdown + LaTeX格式）：
```

---

## 流式输出

### 前端渲染支持

V2 架构支持完整的流式输出，前端可以实时渲染：

1. **Markdown 渲染**：
   - 使用 `marked.js` 或类似库
   - 支持标题、列表、表格、代码块等

2. **LaTeX 渲染**：
   - 使用 `KaTeX` 或 `MathJax`
   - 支持行内公式 `$...$`
   - 支持块级公式 `$$...$$`

3. **代码高亮**：
   - 使用 `highlight.js` 或 `Prism.js`
   - 自动识别语言并高亮

### 流式事件处理示例

```javascript
const eventSource = fetch('/api/v2/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: '...', kb_ids: [5]})
});

const reader = eventSource.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const event = JSON.parse(line.slice(6));
            
            switch (event.event) {
                case 'plan_complete':
                    console.log('Plan:', event.data.plan);
                    break;
                    
                case 'tool_end':
                    console.log('Tool:', event.data.tool, event.data.result_summary);
                    break;
                    
                case 'answer_chunk':
                    // 逐字追加答案
                    answerDiv.textContent += event.data.chunk;
                    // 实时渲染 Markdown + LaTeX
                    renderMarkdown(answerDiv);
                    break;
                    
                case 'done':
                    console.log('Complete!', event.data);
                    break;
            }
        }
    }
}
```

---

## 错误处理与容错

### 1. LLM 响应解析失败

```python
def _parse_json_response(response: str) -> Dict:
    """稳健的 JSON 解析"""
    try:
        # 尝试直接解析
        return json.loads(response.strip())
    except:
        # 尝试提取 JSON（正则）
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        # 尝试栈匹配平衡大括号
        # ...
        
        # 兜底：返回默认决策
        return {
            'action': 'ready_to_answer',
            'args': {},
            'reasoning': '无法解析模型响应，默认直接回答'
        }
```

### 2. 工具执行失败

```python
try:
    result = execute_tool(tool_name, args)
    # 记录成功
    log_tool_call(tool_name, result, success=True)
except Exception as e:
    # 记录失败
    log_tool_call(tool_name, error=str(e), success=False)
    # 标记子任务为失败
    if context.current_subtask_id:
        task = context.get_subtask(context.current_subtask_id)
        task.status = "failed"
    # 继续迭代（不中断流程）
    return {'error': str(e), 'summary': '工具执行失败'}
```

### 3. 工具调用上限

```python
if not context.can_call_tool(tool_name):
    # 记录警告
    logger.warning(f"工具 {tool_name} 已达调用上限")
    
    # 强制结束迭代
    return {
        'summary': f"工具已达上限，基于现有信息生成答案",
        'reached_limit': True
    }
```

### 4. Evaluate 阶段异常

```python
try:
    evaluation = llm.evaluate(context)
    return evaluation
except Exception as e:
    logger.error(f"评估异常: {e}")
    # 默认可以回答（避免无限循环）
    return {
        'should_answer': True,
        'reason': f'评估出错，默认生成答案: {str(e)}',
        'timestamp': time.time()
    }
```

### 5. 答案生成失败

```python
try:
    answer = llm.generate_answer(context)
    return answer
except Exception as e:
    logger.error(f"答案生成错误: {e}")
    # 返回友好错误信息
    return f"抱歉，生成答案时出错：{str(e)}"
```

---

## 性能优化

### 1. 上下文摘要

不是每次都传递完整上下文，而是生成摘要：

```python
def get_context_summary(self) -> str:
    """生成紧凑的上下文摘要"""
    lines = []
    lines.append(f"【用户问题】{self.user_query}")
    
    # 工具使用情况（简洁）
    lines.append("【工具使用情况】")
    lines.append(self.get_tool_usage_summary())
    
    # 子任务状态（简洁）
    if self.subtasks:
        lines.append("【子任务列表】")
        lines.append(self.get_subtasks_summary())
    
    # 工具调用历史（摘要）
    if self.tools_log:
        lines.append("【工具调用历史】")
        for i, log in enumerate(self.tools_log, 1):
            lines.append(f"{i}. {log.tool}({log.query[:30]}...) → {log.result_summary[:50]}...")
    
    return "\n".join(lines)
```

### 2. 证据分类存储

按类型分类存储证据，便于检索和引用：

```python
evidence = {
    "kb_retrieval": [...],     # 知识库检索结果
    "web_search": [...],       # 网络搜索结果
    "python_execution": [...]  # 代码执行结果
}
```

### 3. 工具结果缓存

对于相同的查询参数，可以缓存工具结果：

```python
# TODO: 实现工具结果缓存
cache_key = f"{tool_name}:{json.dumps(args)}"
if cache_key in tool_cache:
    return tool_cache[cache_key]
```

---

## 扩展性设计

### 1. 新增工具

只需实现工具方法并注册：

```python
def _tool_new_feature(self, query: str, args: Dict) -> Dict:
    """新工具实现"""
    # 执行工具逻辑
    result = ...
    
    # 返回标准格式
    return {
        'summary': '结果摘要',
        'data': result
    }
```

在 Plan 提示词中添加工具说明：

```
## N. new_feature - 新功能
功能：...
参数：...
使用场景：...
```

### 2. 自定义评估策略

可以替换或扩展评估逻辑：

```python
def custom_evaluate(self, context: AgentContext) -> Dict:
    """自定义评估策略"""
    # 基础评估
    base_eval = self._evaluate(context)
    
    # 额外检查
    if custom_condition(context):
        base_eval['should_answer'] = False
        base_eval['reason'] += "; 额外条件未满足"
    
    return base_eval
```

### 3. 多模型支持

可以为不同阶段使用不同模型：

```python
class V2Agent:
    def __init__(self):
        self.plan_model = "qwen-max"        # 规划用强模型
        self.answer_model = "qwen-turbo"    # 生成用快模型
        self.eval_model = "qwen-plus"       # 评估用中等模型
```

---

## 最佳实践

### 1. 提示词设计

- **明确角色定义**：清楚说明 Agent 的职责
- **结构化输出**：严格要求 JSON 格式
- **包含示例**：提供正确和错误的示例
- **边界约束**：明确禁止的行为

### 2. 工具调用

- **合并查询**：尽可能将相关问题合并为一次查询
- **非必要不调用**：优先使用已有信息
- **上限保护**：严格遵守工具调用次数限制

### 3. 多任务处理

- **明确分解**：每个子任务都应该独立且明确
- **关联工具**：为每个子任务指定所需工具
- **状态跟踪**：实时更新任务状态和证据关联

### 4. 错误处理

- **优雅降级**：出错时不中断流程，提供备选方案
- **详细日志**：记录所有异常和警告
- **用户友好**：错误信息对用户友好

### 5. 性能监控

- **执行时间**：记录每个工具的执行时间
- **调用统计**：统计工具调用次数和成功率
- **置信度分析**：分析不同场景的置信度分布

---

## 总结

V2 Agentic RAG 架构通过 **增量式上下文迭代** 设计，实现了：

✅ **统一认知空间**：所有信息在单一上下文中累积，确保 Agent 决策的一致性

✅ **多任务并行跟踪**：自动识别并拆解复杂查询，独立跟踪每个子任务的状态

✅ **智能工具管理**：按工具类型独立限制调用次数，避免过度调用

✅ **完整性保证**：严格验证所有子任务完成状态，确保不遗漏任何问题

✅ **流式用户体验**：支持 Markdown 和 LaTeX 实时渲染，提升交互体验

✅ **稳健容错**：多层错误处理机制，确保系统在异常情况下也能正常运行

这套架构在保持灵活性的同时，提供了强大的任务处理能力和优秀的用户体验。

---

**文档版本**：v1.0  
**最后更新**：2025年10月6日  
**作者**：Agentic-RAG Team
