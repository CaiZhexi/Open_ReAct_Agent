"""
运行一个复杂的多任务查询追踪
"""
from trace_v2_agent_io import trace_v2_agent
from datetime import datetime

# 复杂查询：包含多个子任务
complex_query = "100的阶乘是多少？今天佛山天气怎么样？"

print(f"\n{'='*80}")
print(f"运行复杂查询追踪")
print(f"查询: {complex_query}")
print(f"{'='*80}\n")

# 运行追踪
tracer, context = trace_v2_agent(complex_query)

# 生成时间戳
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# 保存追踪日志
json_filepath = f"logs/v2_trace_complex_{timestamp}.json"
md_filepath = f"logs/v2_trace_complex_{timestamp}.md"

tracer.save_to_file(json_filepath)
tracer.save_to_markdown(md_filepath)

print(f"\n✅ 复杂查询追踪完成！")
print(f"   - JSON: {json_filepath}")
print(f"   - Markdown: {md_filepath}")

# 打印关键统计
print(f"\n📊 统计摘要:")
print(f"   - 总迭代: {len(tracer.trace_log['iterations'])} 次")
print(f"   - LLM 调用: {tracer.llm_call_count} 次")
print(f"   - 工具调用: {tracer.tool_call_count} 次")
print(f"   - 总耗时: {tracer.trace_log['total_duration']:.2f}s")

