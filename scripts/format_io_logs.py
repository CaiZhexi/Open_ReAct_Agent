#!/usr/bin/env python3
"""
IO日志美化工具
将JSONL格式的API调用日志转换为易读的Markdown格式
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


class IOLogFormatter:
    """IO日志格式化器"""
    
    def __init__(self, input_file: str, output_file: str = None):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file) if output_file else self.input_file.with_suffix('.md')
        self.logs = []
        
    def load_logs(self):
        """加载JSONL日志文件"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.logs.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"⚠️  跳过无效JSON行: {e}")
        
        print(f"✅ 加载了 {len(self.logs)} 条日志记录")
    
    def format_to_markdown(self) -> str:
        """格式化为Markdown"""
        lines = []
        
        # 标题
        lines.append("# API调用日志\n")
        lines.append(f"**源文件**: `{self.input_file.name}`\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---\n\n")
        
        # 按 request_id 分组
        requests = self._group_by_request()
        
        # 总体统计
        total_llm_calls = sum(len([l for l in req['logs'] if l.get('type') == 'llm_call']) for req in requests.values())
        total_api_calls = sum(len([l for l in req['logs'] if l.get('type') in ['search_call', 'embed_call', 'rerank_call']]) for req in requests.values())
        
        lines.append("## 📊 总体统计\n")
        lines.append(f"- 用户请求数: **{len(requests)}** 次\n")
        lines.append(f"- LLM调用总数: **{total_llm_calls}** 次\n")
        lines.append(f"- 其他API调用: **{total_api_calls}** 次\n")
        lines.append("\n---\n\n")
        
        # 目录
        lines.append("## 📑 请求目录\n\n")
        for idx, (request_id, req_data) in enumerate(requests.items(), 1):
            query = req_data['query'][:50] + ('...' if len(req_data['query']) > 50 else '')
            lines.append(f"{idx}. [{request_id}](#{request_id}) - `{query}`\n")
        lines.append("\n---\n\n")
        
        # 按请求展示详细日志
        for idx, (request_id, req_data) in enumerate(requests.items(), 1):
            lines.append(self._format_request(request_id, req_data, idx))
            lines.append("\n---\n\n")
        
        return "".join(lines)
    
    def _group_by_request(self) -> Dict[str, Dict[str, Any]]:
        """按 request_id 分组日志"""
        requests = {}
        
        for log in self.logs:
            log_type = log.get('type')
            
            # 处理请求开始事件
            if log_type == 'request_start':
                request_id = log.get('request_id')
                requests[request_id] = {
                    'query': log.get('query', ''),
                    'start_time': log.get('timestamp'),
                    'metadata': log.get('metadata', {}),
                    'logs': [],
                    'end_time': None
                }
            
            # 处理请求结束事件
            elif log_type == 'request_end':
                request_id = log.get('request_id')
                if request_id in requests:
                    requests[request_id]['end_time'] = log.get('timestamp')
                    requests[request_id]['result'] = log.get('result_summary', {})
            
            # 处理其他日志（LLM调用、工具调用等）
            else:
                request_id = log.get('request_id', 'unknown')
                
                # 如果没有对应的请求记录，创建一个
                if request_id not in requests:
                    requests[request_id] = {
                        'query': '（未记录）',
                        'start_time': log.get('timestamp'),
                        'metadata': {},
                        'logs': [],
                        'end_time': None
                    }
                
                requests[request_id]['logs'].append(log)
        
        return requests
    
    def _format_request(self, request_id: str, req_data: Dict[str, Any], req_num: int) -> str:
        """格式化单个请求"""
        lines = []
        
        query = req_data['query']
        start_time = req_data['start_time']
        end_time = req_data['end_time']
        logs = req_data['logs']
        
        # 请求标题（添加锚点）
        lines.append(f"## 🔖 请求 #{req_num}: {request_id}\n\n")
        lines.append(f"<a id=\"{request_id}\"></a>\n\n")
        
        # 请求信息
        lines.append(f"**📝 用户查询**: {query}\n\n")
        lines.append(f"**⏰ 开始时间**: `{start_time}`\n")
        if end_time:
            lines.append(f"**⏰ 结束时间**: `{end_time}`\n")
        lines.append("\n")
        
        # 分类统计
        llm_calls = [l for l in logs if l.get('type') == 'llm_call']
        api_calls = [l for l in logs if l.get('type') in ['search_call', 'embed_call', 'rerank_call']]
        
        lines.append(f"**📊 本次请求统计**:\n")
        lines.append(f"- LLM调用: {len(llm_calls)} 次\n")
        lines.append(f"- API调用: {len(api_calls)} 次\n")
        lines.append("\n")
        
        # 按阶段分组展示LLM调用
        if llm_calls:
            lines.append("### 🔍 LLM调用详情\n\n")
            
            phases = {}
            for log in llm_calls:
                phase = log.get('phase', 'unknown')
                if phase not in phases:
                    phases[phase] = []
                phases[phase].append(log)
            
            # 按阶段顺序展示
            phase_order = ['Plan', 'CodeGen', 'Evaluate', 'Answer', 'FinalEvaluate', 'unknown']
            for phase in phase_order:
                if phase not in phases:
                    continue
                    
                logs_in_phase = phases[phase]
                lines.append(f"#### 阶段: {phase} ({len(logs_in_phase)} 次)\n\n")
                
                for log in logs_in_phase:
                    lines.append(self._format_llm_call(log, 0))
                    lines.append("\n")
        
        # API调用
        if api_calls:
            lines.append("### 🌐 其他API调用\n\n")
            for log in api_calls:
                lines.append(self._format_other_call(log, 0))
                lines.append("\n")
        
        return "".join(lines)
    
    def _format_llm_call(self, log: Dict[str, Any], idx: int = 0) -> str:
        """格式化单个LLM调用"""
        lines = []
        
        # 标题
        call_id = log.get('call_id', '?')
        phase = log.get('phase', 'unknown')
        timestamp = log.get('timestamp', '')
        duration = log.get('duration', 0)
        
        lines.append(f"**📞 LLM调用 #{call_id}**\n\n")
        lines.append(f"- ⏰ 时间: `{timestamp}`\n")
        lines.append(f"- ⏱️  耗时: `{duration:.3f}s` ({duration*1000:.0f}ms)\n")
        
        # 请求信息
        request = log.get('request', {})
        model = request.get('model', 'unknown')
        temp = request.get('temperature', 0.7)
        max_tokens = request.get('max_tokens', 2000)
        messages = request.get('messages', [])
        
        lines.append(f"- 🤖 模型: `{model}`\n")
        lines.append(f"- 🎛️  参数: temperature={temp}, max_tokens={max_tokens}\n")
        lines.append(f"- 💬 消息数: {len(messages)}\n\n")
        
        # Prompt内容 - 完整显示，不截断
        lines.append("**📝 完整请求 Prompt:**\n\n")
        if messages:
            # 显示所有消息
            for msg_idx, msg in enumerate(messages, 1):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                if len(messages) > 1:
                    lines.append(f"*消息 #{msg_idx} ({role}):*\n\n")
                
                lines.append("```text\n")
                lines.append(content)
                lines.append("\n```\n\n")
        else:
            lines.append("*(无消息)*\n\n")
        
        # 响应内容 - 完整显示，不截断
        response = log.get('response', {})
        content = response.get('content', '')
        error = response.get('error')
        
        if error:
            lines.append(f"**❌ 错误:** `{error}`\n\n")
        else:
            lines.append("**📤 完整响应内容:**\n\n")
            lines.append("```text\n")
            lines.append(content)
            lines.append("\n```\n\n")
        
        # 性能信息
        perf = log.get('performance', {})
        if perf:
            lines.append("**📊 性能统计:**\n\n")
            lines.append(f"- 输入token估算: {perf.get('estimated_input_tokens', 0)}\n")
            lines.append(f"- 输出token估算: {perf.get('estimated_output_tokens', 0)}\n")
            
            usage = perf.get('usage', {})
            if usage:
                lines.append(f"- 实际token使用: {usage.get('total_tokens', 0)} (输入: {usage.get('prompt_tokens', 0)}, 输出: {usage.get('completion_tokens', 0)})\n")
            
            lines.append("\n")
        
        return "".join(lines)
    
    def _format_other_call(self, log: Dict[str, Any], idx: int) -> str:
        """格式化其他API调用"""
        lines = []
        
        call_type = log.get('type', 'unknown')
        call_id = log.get('call_id', '?')
        timestamp = log.get('timestamp', '')
        duration = log.get('duration', 0)
        
        lines.append(f"#### 🔧 {call_type} #{call_id}\n\n")
        lines.append(f"- ⏰ 时间: `{timestamp}`\n")
        lines.append(f"- ⏱️  耗时: `{duration:.3f}s`\n\n")
        
        # 请求
        request = log.get('request', {})
        lines.append("**请求参数:**\n")
        lines.append("```json\n")
        lines.append(json.dumps(request, ensure_ascii=False, indent=2))
        lines.append("\n```\n\n")
        
        # 响应（简要）
        response = log.get('response', {})
        lines.append("**响应摘要:**\n")
        lines.append("```json\n")
        
        # 只显示响应的关键信息，不显示完整数据
        response_summary = {}
        for key in ['result_count', 'embedding_count', 'dimension', 'success', 'error']:
            if key in response:
                response_summary[key] = response[key]
        
        lines.append(json.dumps(response_summary, ensure_ascii=False, indent=2))
        lines.append("\n```\n\n")
        
        return "".join(lines)
    
    def save(self, content: str):
        """保存到文件"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 格式化完成，已保存到: {self.output_file}")
        print(f"📄 文件大小: {self.output_file.stat().st_size / 1024:.1f} KB")
    
    def run(self):
        """执行格式化"""
        print(f"🔄 正在处理: {self.input_file}")
        self.load_logs()
        content = self.format_to_markdown()
        self.save(content)


def find_latest_log_file():
    """查找最新的API日志文件"""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return None
    
    # 查找所有 api_io_*.jsonl 文件
    log_files = list(logs_dir.glob('api_io_*.jsonl'))
    if not log_files:
        return None
    
    # 按修改时间排序，返回最新的
    latest_file = max(log_files, key=lambda p: p.stat().st_mtime)
    return latest_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='将JSONL格式的API调用日志转换为易读的Markdown格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 格式化指定日志文件
  python format_io_logs.py logs/api_io_20251006_160550.jsonl
  
  # 格式化最新的日志文件
  python format_io_logs.py --latest
  
  # 指定输出文件
  python format_io_logs.py input.jsonl -o output.md
  
  # 格式化最新日志并直接查看
  python format_io_logs.py --latest --view
        """
    )
    
    parser.add_argument('input_file', nargs='?', help='输入的JSONL日志文件')
    parser.add_argument('-o', '--output', help='输出的Markdown文件（默认与输入文件同名）')
    parser.add_argument('--latest', action='store_true', help='自动处理最新的日志文件')
    parser.add_argument('--view', action='store_true', help='格式化后自动用浏览器打开')
    
    args = parser.parse_args()
    
    # 确定输入文件
    if args.latest:
        input_file = find_latest_log_file()
        if not input_file:
            print("❌ 未找到任何API日志文件（api_io_*.jsonl）")
            sys.exit(1)
        print(f"📂 找到最新日志文件: {input_file}")
    elif args.input_file:
        input_file = args.input_file
    else:
        parser.print_help()
        sys.exit(1)
    
    # 执行格式化
    formatter = IOLogFormatter(input_file, args.output)
    formatter.run()
    
    # 是否自动打开
    if args.view:
        import webbrowser
        webbrowser.open(f'file://{formatter.output_file.absolute()}')
        print(f"🌐 已在浏览器中打开: {formatter.output_file}")


if __name__ == '__main__':
    main()

