"""
V2 Agent IO 追踪器
追踪并记录 V2 Agent 运行过程中的所有 LLM 输入输出和工具调用
"""
import json
import time
from datetime import datetime
from typing import Dict, Any, List
from functools import wraps


class IOTracer:
    """IO 追踪器：记录所有 LLM 调用和工具执行"""
    
    def __init__(self):
        self.trace_log = {
            'query': '',
            'start_time': '',
            'end_time': '',
            'total_duration': 0.0,
            'iterations': [],
            'summary': {
                'total_iterations': 0,
                'llm_calls': 0,
                'tool_calls': 0,
                'total_llm_time': 0.0,
                'total_tool_time': 0.0
            }
        }
        self.current_iteration = None
        self.llm_call_count = 0
        self.tool_call_count = 0
        self.start_time = None
    
    def start_trace(self, query: str):
        """开始追踪"""
        self.start_time = time.time()
        self.trace_log['query'] = query
        self.trace_log['start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*80}")
        print(f"开始追踪查询: {query}")
        print(f"{'='*80}\n")
    
    def start_iteration(self, iteration_num: int):
        """开始新的迭代"""
        self.current_iteration = {
            'iteration': iteration_num,
            'phases': []
        }
        print(f"\n{'─'*80}")
        print(f"迭代 #{iteration_num}")
        print(f"{'─'*80}")
    
    def log_llm_call(self, phase: str, prompt: str, response: str, 
                     duration: float, temperature: float = 0.1):
        """记录 LLM 调用"""
        self.llm_call_count += 1
        
        llm_log = {
            'phase': phase,
            'type': 'llm_call',
            'call_id': self.llm_call_count,
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'duration': round(duration, 3),
            'temperature': temperature,
            'prompt': prompt,
            'prompt_length': len(prompt),
            'response': response,
            'response_length': len(response)
        }
        
        if self.current_iteration:
            self.current_iteration['phases'].append(llm_log)
        
        # 打印到控制台
        print(f"\n[{phase}] LLM 调用 #{self.llm_call_count}")
        print(f"耗时: {duration:.3f}s | Temperature: {temperature}")
        print(f"\n【提示词】({len(prompt)} 字符)")
        print("─" * 80)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("─" * 80)
        print(f"\n【响应】({len(response)} 字符)")
        print("─" * 80)
        print(response[:500] + "..." if len(response) > 500 else response)
        print("─" * 80)
    
    def log_tool_call(self, tool_name: str, query: str, args: Dict[str, Any],
                     result: Dict[str, Any], duration: float):
        """记录工具调用"""
        self.tool_call_count += 1
        
        tool_log = {
            'phase': 'tool_execution',
            'type': 'tool_call',
            'call_id': self.tool_call_count,
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'duration': round(duration, 3),
            'tool_name': tool_name,
            'query': query,
            'args': args,
            'result_summary': self._summarize_result(tool_name, result),
            'result': result
        }
        
        if self.current_iteration:
            self.current_iteration['phases'].append(tool_log)
        
        # 打印到控制台
        print(f"\n[工具执行] {tool_name} #{self.tool_call_count}")
        print(f"耗时: {duration:.3f}s")
        print(f"\n【查询】: {query}")
        print(f"【参数】: {json.dumps(args, ensure_ascii=False)}")
        print(f"【结果摘要】: {tool_log['result_summary']}")
        if tool_name == 'python_code':
            if 'code' in result:
                print(f"\n【生成的代码】:\n{result['code']}")
            if 'output' in result:
                print(f"【执行输出】:\n{result['output']}")
    
    def _summarize_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """总结工具调用结果"""
        if 'error' in result:
            return f"错误: {result['error']}"
        
        if tool_name == 'search':
            chunks = result.get('chunks', [])
            return f"检索到 {len(chunks)} 条文档"
        
        elif tool_name == 'web_search':
            results = result.get('results', [])
            return f"搜索到 {len(results)} 条网络信息"
        
        elif tool_name == 'python_code':
            if result.get('error'):
                return f"代码执行失败: {result.get('error')}"
            output = result.get('output', '')
            return f"代码执行成功，输出 {len(output)} 字符"
        
        return "执行完成"
    
    def end_iteration(self):
        """结束当前迭代"""
        if self.current_iteration:
            self.trace_log['iterations'].append(self.current_iteration)
            self.current_iteration = None
    
    def end_trace(self):
        """结束追踪"""
        if self.start_time:
            total_duration = time.time() - self.start_time
            self.trace_log['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.trace_log['total_duration'] = round(total_duration, 3)
        
        # 计算统计信息
        self.trace_log['summary']['total_iterations'] = len(self.trace_log['iterations'])
        self.trace_log['summary']['llm_calls'] = self.llm_call_count
        self.trace_log['summary']['tool_calls'] = self.tool_call_count
        
        # 计算总时间
        total_llm_time = 0.0
        total_tool_time = 0.0
        for iteration in self.trace_log['iterations']:
            for phase in iteration['phases']:
                if phase['type'] == 'llm_call':
                    total_llm_time += phase['duration']
                elif phase['type'] == 'tool_call':
                    total_tool_time += phase['duration']
        
        self.trace_log['summary']['total_llm_time'] = round(total_llm_time, 3)
        self.trace_log['summary']['total_tool_time'] = round(total_tool_time, 3)
        
        print(f"\n{'='*80}")
        print("追踪完成")
        print(f"{'='*80}")
        print(f"总耗时: {self.trace_log['total_duration']:.3f}s")
        print(f"总迭代: {self.trace_log['summary']['total_iterations']} 次")
        print(f"LLM 调用: {self.trace_log['summary']['llm_calls']} 次 "
              f"(耗时 {self.trace_log['summary']['total_llm_time']:.3f}s)")
        print(f"工具调用: {self.trace_log['summary']['tool_calls']} 次 "
              f"(耗时 {self.trace_log['summary']['total_tool_time']:.3f}s)")
        print(f"{'='*80}\n")
    
    def save_to_file(self, filepath: str):
        """保存追踪日志到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.trace_log, f, ensure_ascii=False, indent=2)
        print(f"追踪日志已保存到: {filepath}")
    
    def save_to_markdown(self, filepath: str):
        """保存为 Markdown 格式"""
        md_lines = []
        
        # 标题
        md_lines.append(f"# V2 Agent IO 追踪日志\n")
        md_lines.append(f"**查询**: {self.trace_log['query']}\n")
        md_lines.append(f"**开始时间**: {self.trace_log['start_time']}\n")
        md_lines.append(f"**结束时间**: {self.trace_log['end_time']}\n")
        md_lines.append(f"**总耗时**: {self.trace_log['total_duration']:.3f}s\n")
        
        # 摘要
        md_lines.append(f"\n## 执行摘要\n")
        summary = self.trace_log['summary']
        md_lines.append(f"- 总迭代次数: {summary['total_iterations']}\n")
        md_lines.append(f"- LLM 调用: {summary['llm_calls']} 次 "
                       f"(总耗时 {summary['total_llm_time']:.3f}s)\n")
        md_lines.append(f"- 工具调用: {summary['tool_calls']} 次 "
                       f"(总耗时 {summary['total_tool_time']:.3f}s)\n")
        
        # 详细迭代
        for iteration in self.trace_log['iterations']:
            md_lines.append(f"\n## 迭代 #{iteration['iteration']}\n")
            
            for phase in iteration['phases']:
                if phase['type'] == 'llm_call':
                    md_lines.append(f"\n### [{phase['phase']}] LLM 调用 #{phase['call_id']}\n")
                    md_lines.append(f"**耗时**: {phase['duration']:.3f}s | "
                                   f"**Temperature**: {phase['temperature']}\n")
                    md_lines.append(f"\n#### 提示词 ({phase['prompt_length']} 字符)\n")
                    md_lines.append(f"```\n{phase['prompt']}\n```\n")
                    md_lines.append(f"\n#### 响应 ({phase['response_length']} 字符)\n")
                    md_lines.append(f"```json\n{phase['response']}\n```\n")
                
                elif phase['type'] == 'tool_call':
                    md_lines.append(f"\n### [工具执行] {phase['tool_name']} #{phase['call_id']}\n")
                    md_lines.append(f"**耗时**: {phase['duration']:.3f}s\n")
                    md_lines.append(f"**查询**: {phase['query']}\n")
                    md_lines.append(f"**参数**: `{json.dumps(phase['args'], ensure_ascii=False)}`\n")
                    md_lines.append(f"**结果摘要**: {phase['result_summary']}\n")
                    
                    # 特殊处理 Python 代码
                    if phase['tool_name'] == 'python_code':
                        result = phase['result']
                        if 'code' in result:
                            md_lines.append(f"\n#### 生成的代码\n")
                            md_lines.append(f"```python\n{result['code']}\n```\n")
                        if 'output' in result:
                            md_lines.append(f"\n#### 执行输出\n")
                            md_lines.append(f"```\n{result['output']}\n```\n")
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(md_lines)
        print(f"Markdown 追踪日志已保存到: {filepath}")


# ============ 包装 V2 Agent 进行追踪 ============

def trace_v2_agent(query: str, kb_ids: List[int] = None, kb_names: Dict[int, str] = None):
    """追踪 V2 Agent 的完整执行过程"""
    from app.services.v2_agent import V2Agent
    from app.services.api_clients import chat_client
    import app.services.v2_agent as v2_module
    
    # 创建追踪器
    tracer = IOTracer()
    tracer.start_trace(query)
    
    # 保存原始的 chat 方法
    original_chat = chat_client.chat
    original_chat_stream_generator = chat_client.chat_stream_generator
    
    # 包装 chat 方法以追踪 LLM 调用
    def traced_chat(messages, stream=False, max_tokens=2000, temperature=0.7):
        """追踪版本的 chat 方法"""
        prompt = messages[0]['content'] if messages else ''
        
        # 推断当前阶段
        phase = 'unknown'
        if 'Plan' in prompt or '规划' in prompt or '决策' in prompt:
            phase = 'Plan'
        elif 'Evaluate' in prompt or '评估' in prompt:
            phase = 'Evaluate'
        elif '生成答案' in prompt or '回答' in prompt or '请基于证据' in prompt:
            phase = 'Answer'
        elif '最终评估' in prompt or '置信度' in prompt:
            phase = 'FinalEvaluate'
        elif '代码' in prompt or 'Python' in prompt:
            phase = 'CodeGen'
        
        start_time = time.time()
        response = original_chat(messages, stream=stream, max_tokens=max_tokens, temperature=temperature)
        duration = time.time() - start_time
        
        tracer.log_llm_call(phase, prompt, response, duration, temperature)
        
        return response
    
    # 替换 chat 方法
    chat_client.chat = traced_chat
    
    # 包装工具执行方法
    agent = V2Agent()
    original_execute_tool = agent._execute_tool
    
    def traced_execute_tool(context, plan_result):
        """追踪版本的工具执行方法"""
        tool_name = plan_result.get('action', 'unknown')
        args = plan_result.get('args', {})
        query = args.get('query', context.user_query)
        
        start_time = time.time()
        result = original_execute_tool(context, plan_result)
        duration = time.time() - start_time
        
        tracer.log_tool_call(tool_name, query, args, result, duration)
        
        return result
    
    agent._execute_tool = traced_execute_tool
    
    # 追踪主循环
    try:
        # 使用非流式方式运行以便完整追踪
        iteration_count = 0
        
        # 初始化上下文
        from app.services.v2_agent import AgentContext
        context = AgentContext(
            user_query=query,
            kb_ids=kb_ids or [],
            kb_names=kb_names or {}
        )
        
        # 主循环
        while context.can_continue():
            iteration_count += 1
            tracer.start_iteration(iteration_count)
            
            # 1. Plan
            plan_result = agent._plan(context)
            
            # 2. Tool Using
            if plan_result['action'] == 'ready_to_answer':
                tracer.end_iteration()
                break
            else:
                agent._execute_tool(context, plan_result)
            
            # 3. Evaluate
            eval_result = agent._evaluate(context)
            
            tracer.end_iteration()
            
            if eval_result.get('should_answer'):
                break
            
            # 安全检查：最多30次迭代
            if iteration_count >= 30:
                print("\n⚠️  达到最大迭代次数限制")
                break
        
        # 4. Generate Answer
        print(f"\n{'─'*80}")
        print("生成最终答案")
        print(f"{'─'*80}")
        tracer.start_iteration(iteration_count + 1)
        answer = agent._generate_answer(context)
        print(f"\n【最终答案】({len(answer)} 字符)")
        print("─" * 80)
        print(answer)
        print("─" * 80)
        context.final_answer = answer
        
        # 5. Final Evaluation
        final_eval = agent._final_evaluate(context)
        tracer.end_iteration()
        
        context.final_evaluation = final_eval
        context.status = "done"
        
    finally:
        # 恢复原始方法
        chat_client.chat = original_chat
        chat_client.chat_stream_generator = original_chat_stream_generator
    
    # 结束追踪
    tracer.end_trace()
    
    return tracer, context


if __name__ == '__main__':
    import sys
    
    # 测试查询
    test_queries = [
        "100的阶乘是多少？",
        "今天佛山天气怎么样？",
        "计算 sqrt(256) + log(100) 的值",
        "高空作业的安全规范有哪些？",  # 需要知识库
    ]
    
    # 选择测试查询
    query_index = 0 if len(sys.argv) <= 1 else int(sys.argv[1])
    query = test_queries[query_index]
    
    print(f"\n使用测试查询 #{query_index}: {query}\n")
    
    # 运行追踪
    tracer, context = trace_v2_agent(query)
    
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存追踪日志
    json_filepath = f"logs/v2_trace_{timestamp}.json"
    md_filepath = f"logs/v2_trace_{timestamp}.md"
    
    tracer.save_to_file(json_filepath)
    tracer.save_to_markdown(md_filepath)
    
    print(f"\n✅ 追踪完成！")
    print(f"   - JSON: {json_filepath}")
    print(f"   - Markdown: {md_filepath}")

