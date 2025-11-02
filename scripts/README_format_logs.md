# API日志格式化工具使用说明

## 功能介绍

`format_io_logs.py` 是一个将JSONL格式的API调用日志转换为易读Markdown格式的工具。

### 核心特性

**✨ 按请求分组展示** - 每次用户请求的所有调用独立呈现，一目了然

### 解决的问题

原始的JSONL日志存在以下问题：
- ❌ 每行一个巨大的JSON对象，完全无法直接阅读
- ❌ 多个用户请求混在一起，无法区分
- ❌ 大量转义字符和嵌套结构
- ❌ Prompt和Response混在一起
- ❌ 没有分阶段展示

转换后的Markdown格式：
- ✅ **按用户请求分组**，每个请求独立展示
- ✅ 提供请求目录，快速跳转到特定请求
- ✅ 每个请求内按阶段（Plan/CodeGen/Evaluate/Answer等）分组
- ✅ Prompt和Response分开，清晰易读
- ✅ 包含性能统计信息（token消耗、耗时等）
- ✅ 支持在IDE/浏览器中直接查看

## 使用方法

### 1. 格式化指定日志文件

```bash
# 基础用法
python scripts/format_io_logs.py logs/api_io_20251006_160550.jsonl

# 指定输出文件名
python scripts/format_io_logs.py logs/api_io_20251006_160550.jsonl -o my_analysis.md
```

### 2. 自动格式化最新日志

```bash
# 自动找到最新的日志文件并格式化
python scripts/format_io_logs.py --latest

# 格式化后自动在浏览器中打开（推荐）
python scripts/format_io_logs.py --latest --view
```

### 3. 查看帮助

```bash
python scripts/format_io_logs.py --help
```

## 输出格式说明

生成的Markdown文件采用**按请求分组**的结构：

### 1. 总体统计

```markdown
## 📊 总体统计
- 用户请求数: 5 次
- LLM调用总数: 40 次
- 其他API调用: 10 次
```

### 2. 请求目录（可点击跳转）

```markdown
## 📑 请求目录

1. [req_1_1728123456](#req_1_1728123456) - `100的阶乘是多少？`
2. [req_2_1728123460](#req_2_1728123460) - `50!+100!=？【原神】向着太空出发什么时候播出？`
3. [req_3_1728123465](#req_3_1728123465) - `佛山今天天气如何？`
```

### 3. 每个请求的详细信息

```markdown
## 🔖 请求 #1: req_1_1728123456

**📝 用户查询**: 100的阶乘是多少？

**⏰ 开始时间**: 2025-10-06T16:06:45.123456
**⏰ 结束时间**: 2025-10-06T16:06:52.987654

**📊 本次请求统计**:
- LLM调用: 8 次
- API调用: 2 次

### 🔍 LLM调用详情

#### 阶段: Plan (3 次)

**📞 LLM调用 #1**
- ⏰ 时间: 2025-10-06T16:06:47.113236
- ⏱️  耗时: 2.057s (2057ms)
- 🤖 模型: qwen-flash

**📝 Prompt:**
[完整的prompt内容]

**📤 响应:**
[LLM的响应内容]

**📊 性能统计:**
- 输入token: 960
- 输出token: 107
- 总token: 1067
```

### 4. 阶段类型

- **Plan**: 规划下一步行动
- **CodeGen**: 生成Python代码
- **Evaluate**: 评估信息充分性
- **Answer**: 生成最终答案
- **FinalEvaluate**: 最终质量评估

### 5. 核心优势

- **隔离清晰**: 每个用户请求的调用链路完全独立
- **快速定位**: 通过请求目录快速跳转到特定请求
- **完整追踪**: 从请求开始到结束的完整时间线
- **性能分析**: 每个请求的token消耗和耗时一目了然

## 典型工作流

### 调试LLM Prompt

1. 运行RAG查询（会自动记录日志到 `logs/api_io_*.jsonl`）
2. 格式化最新日志：`python scripts/format_io_logs.py --latest`
3. 在VSCode/IDE中打开生成的 `.md` 文件
4. 按阶段查看每次LLM调用的Prompt和Response
5. 分析问题并调整Prompt模板

### 性能分析

1. 格式化日志后，查看 **📊 统计摘要** 部分
2. 查看每个阶段的耗时
3. 检查token消耗是否合理
4. 识别性能瓶颈

### 问题排查

当RAG回答不准确时：

1. 查看 **Plan** 阶段：Agent的决策是否正确？
2. 查看 **工具调用** 结果：检索/搜索的结果是否相关？
3. 查看 **Evaluate** 阶段：是否正确判断了信息充分性？
4. 查看 **Answer** 阶段：最终生成的Prompt是否包含了所有证据？

## 高级功能

### 自定义输出格式

如需自定义输出格式，可以修改 `IOLogFormatter` 类中的以下方法：

- `_format_llm_call()`: 修改LLM调用的显示格式
- `_format_other_call()`: 修改其他API调用的显示格式
- `format_to_markdown()`: 修改整体结构

### 集成到工作流

在 `app.py` 或测试脚本中启用日志记录：

```python
from app.services.io_logger import enable_io_logging, disable_io_logging

# 启用日志记录
enable_io_logging()

# 运行RAG查询
result = v2_agent.run(query="你的问题", kb_ids=[5])

# 禁用日志记录
disable_io_logging()

# 自动格式化最新日志
import subprocess
subprocess.run([
    "python", "scripts/format_io_logs.py", "--latest"
])
```

## 注意事项

1. **日志文件大小**: 每次查询可能产生几百KB到几MB的日志，注意磁盘空间
2. **敏感信息**: 日志包含完整的Prompt和Response，注意保护敏感数据
3. **性能影响**: 启用日志记录会有轻微的性能开销（通常<5%）

## 故障排查

### 问题：找不到日志文件

```bash
❌ 未找到任何API日志文件（api_io_*.jsonl）
```

**解决方法**:
- 确保在项目根目录运行命令
- 检查 `logs/` 目录是否存在
- 确认日志记录功能已启用（环境变量 `ENABLE_IO_LOGGING=true`）

### 问题：JSON解析错误

```bash
⚠️  跳过无效JSON行: ...
```

**解决方法**:
- 日志文件可能损坏或不完整
- 检查磁盘空间是否充足
- 尝试重新生成日志

## 示例输出

查看示例输出文件：`logs/api_io_20251006_160550.md`

完整的调用链路清晰可见：
1. 用户提问 → Plan决策
2. Plan → 调用工具（search/web_search/python_code）
3. 工具结果 → Evaluate评估
4. Evaluate → Answer生成
5. Answer → FinalEvaluate质量评估

每一步的Prompt、响应、耗时、token消耗都一目了然。

