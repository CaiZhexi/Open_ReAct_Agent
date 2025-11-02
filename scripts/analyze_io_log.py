"""
IO 日志分析工具
分析 JSONL 格式的 IO 日志，生成详细的分析报告
"""
import json
import sys
from collections import defaultdict, Counter
from datetime import datetime


class IOLogAnalyzer:
    """IO 日志分析器"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logs = []
        self.llm_calls = []
        self.tool_calls = []
        self.api_calls = []
        
        self._load_logs()
        self._categorize_logs()
    
    def _load_logs(self):
        """加载日志文件"""
        print(f"📂 加载日志文件: {self.log_file}")
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        log_entry = json.loads(line)
                        self.logs.append(log_entry)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  跳过无效行: {e}")
        
        print(f"✅ 加载了 {len(self.logs)} 条日志\n")
    
    def _categorize_logs(self):
        """分类日志"""
        for log in self.logs:
            log_type = log.get('type', '')
            
            if log_type == 'llm_call':
                self.llm_calls.append(log)
            elif log_type == 'tool_call':
                self.tool_calls.append(log)
            elif log_type in ['embed_call', 'rerank_call', 'search_call']:
                self.api_calls.append(log)
    
    def print_summary(self):
        """打印总体摘要"""
        print("="*80)
        print("IO 日志分析摘要")
        print("="*80)
        
        # 查找会话开始和结束
        session_start = None
        session_end = None
        for log in self.logs:
            if log.get('type') == 'session_start':
                session_start = log
            elif log.get('type') == 'session_end':
                session_end = log
        
        if session_start:
            print(f"会话开始: {session_start.get('timestamp', 'N/A')}")
        if session_end:
            print(f"会话结束: {session_end.get('timestamp', 'N/A')}")
            print(f"总耗时: {session_end.get('duration', 0):.3f}s")
            
            stats = session_end.get('statistics', {})
            print(f"\n调用统计:")
            for key, value in stats.get('call_counts', {}).items():
                print(f"  - {key}: {value} 次")
            
            print(f"\n时间统计:")
            print(f"  - LLM 总耗时: {stats.get('total_llm_time', 0):.3f}s")
            print(f"  - 工具总耗时: {stats.get('total_tool_time', 0):.3f}s")
            
            print(f"\nToken 估算:")
            print(f"  - 总计: {stats.get('estimated_total_tokens', 0)} tokens")
            print(f"  - 输入: {stats.get('estimated_input_tokens', 0)} tokens")
            print(f"  - 输出: {stats.get('estimated_output_tokens', 0)} tokens")
        
        print("="*80 + "\n")
    
    def print_llm_calls(self, verbose: bool = False):
        """打印 LLM 调用详情"""
        print("\n" + "="*80)
        print(f"LLM 调用详情 ({len(self.llm_calls)} 次)")
        print("="*80)
        
        for i, log in enumerate(self.llm_calls, 1):
            phase = log.get('phase', 'unknown')
            duration = log.get('duration', 0)
            
            request = log.get('request', {})
            response = log.get('response', {})
            perf = log.get('performance', {})
            
            print(f"\n[{i}] {phase} (Call #{log.get('call_id', 0)})")
            print(f"{'─'*80}")
            print(f"⏱️  耗时: {duration:.3f}s ({perf.get('duration_ms', 0):.2f}ms)")
            print(f"🌡️  温度: {request.get('temperature', 0.7)}")
            print(f"🎯 最大Token: {request.get('max_tokens', 2000)}")
            
            # 消息统计
            messages = request.get('messages', [])
            print(f"📨 消息数: {len(messages)}")
            for j, msg in enumerate(messages):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                print(f"   [{j+1}] {role}: {len(content)} 字符")
            
            # 响应统计
            response_content = response.get('content', '')
            print(f"📤 响应长度: {len(response_content)} 字符")
            
            # Token 统计
            print(f"🪙 Token 估算:")
            print(f"   - 输入: {perf.get('estimated_input_tokens', 0)} tokens")
            print(f"   - 输出: {perf.get('estimated_output_tokens', 0)} tokens")
            
            usage = perf.get('usage', {})
            if usage:
                print(f"   - API 返回: {usage}")
            
            # 错误信息
            if response.get('error'):
                print(f"❌ 错误: {response.get('error')}")
            
            # 详细内容
            if verbose:
                print(f"\n{'─'*40} 提示词 {'─'*40}")
                for msg in messages:
                    print(f"\n[{msg.get('role', 'unknown')}]")
                    content = msg.get('content', '')
                    if len(content) > 500:
                        print(content[:250] + "\n...\n" + content[-250:])
                    else:
                        print(content)
                
                print(f"\n{'─'*40} 响应 {'─'*40}")
                if len(response_content) > 500:
                    print(response_content[:250] + "\n...\n" + response_content[-250:])
                else:
                    print(response_content)
                print("─"*80)
    
    def print_tool_calls(self, verbose: bool = False):
        """打印工具调用详情"""
        print("\n" + "="*80)
        print(f"工具调用详情 ({len(self.tool_calls)} 次)")
        print("="*80)
        
        for i, log in enumerate(self.tool_calls, 1):
            tool_name = log.get('tool_name', 'unknown')
            tool_type = log.get('tool_type', 'unknown')
            duration = log.get('duration', 0)
            
            request = log.get('request', {})
            response = log.get('response', {})
            perf = log.get('performance', {})
            
            print(f"\n[{i}] {tool_name} ({tool_type}) - Call #{log.get('call_id', 0)}")
            print(f"{'─'*80}")
            print(f"⏱️  耗时: {duration:.3f}s ({perf.get('duration_ms', 0):.2f}ms)")
            print(f"📊 结果数: {perf.get('result_count', 0)}")
            print(f"💾 数据大小: {perf.get('data_size_bytes', 0)} bytes")
            
            print(f"\n📥 请求参数:")
            for key, value in request.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"   - {key}: {value[:50]}... ({len(value)} 字符)")
                else:
                    print(f"   - {key}: {value}")
            
            print(f"\n📤 响应:")
            print(f"   - 摘要: {response.get('summary', 'N/A')}")
            if response.get('error'):
                print(f"   - 错误: {response.get('error')}")
            
            if verbose:
                print(f"\n{'─'*40} 完整响应数据 {'─'*40}")
                data = response.get('data', {})
                print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])
                print("─"*80)
    
    def print_performance_analysis(self):
        """打印性能分析"""
        print("\n" + "="*80)
        print("性能分析")
        print("="*80)
        
        # LLM 性能分析
        if self.llm_calls:
            print("\n📊 LLM 调用性能:")
            
            phase_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'times': []})
            for log in self.llm_calls:
                phase = log.get('phase', 'unknown')
                duration = log.get('duration', 0)
                phase_stats[phase]['count'] += 1
                phase_stats[phase]['total_time'] += duration
                phase_stats[phase]['times'].append(duration)
            
            for phase, stats in sorted(phase_stats.items(), key=lambda x: x[1]['total_time'], reverse=True):
                avg_time = stats['total_time'] / stats['count']
                min_time = min(stats['times'])
                max_time = max(stats['times'])
                
                print(f"\n{phase}:")
                print(f"  - 调用次数: {stats['count']}")
                print(f"  - 总耗时: {stats['total_time']:.3f}s")
                print(f"  - 平均耗时: {avg_time:.3f}s")
                print(f"  - 最快/最慢: {min_time:.3f}s / {max_time:.3f}s")
        
        # 工具性能分析
        if self.tool_calls:
            print("\n\n🔧 工具调用性能:")
            
            tool_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'times': []})
            for log in self.tool_calls:
                tool_name = log.get('tool_name', 'unknown')
                duration = log.get('duration', 0)
                tool_stats[tool_name]['count'] += 1
                tool_stats[tool_name]['total_time'] += duration
                tool_stats[tool_name]['times'].append(duration)
            
            for tool, stats in sorted(tool_stats.items(), key=lambda x: x[1]['total_time'], reverse=True):
                avg_time = stats['total_time'] / stats['count']
                min_time = min(stats['times'])
                max_time = max(stats['times'])
                
                print(f"\n{tool}:")
                print(f"  - 调用次数: {stats['count']}")
                print(f"  - 总耗时: {stats['total_time']:.3f}s")
                print(f"  - 平均耗时: {avg_time:.3f}s")
                print(f"  - 最快/最慢: {min_time:.3f}s / {max_time:.3f}s")
        
        # Token 消耗分析
        if self.llm_calls:
            print("\n\n🪙 Token 消耗分析:")
            
            total_input_tokens = 0
            total_output_tokens = 0
            
            for log in self.llm_calls:
                perf = log.get('performance', {})
                total_input_tokens += perf.get('estimated_input_tokens', 0)
                total_output_tokens += perf.get('estimated_output_tokens', 0)
            
            total_tokens = total_input_tokens + total_output_tokens
            
            print(f"  - 总计: {total_tokens:,} tokens")
            print(f"  - 输入: {total_input_tokens:,} tokens ({total_input_tokens/total_tokens*100:.1f}%)")
            print(f"  - 输出: {total_output_tokens:,} tokens ({total_output_tokens/total_tokens*100:.1f}%)")
            
            # 估算成本（假设：输入 $0.001/1K tokens，输出 $0.002/1K tokens）
            estimated_cost = (total_input_tokens * 0.001 + total_output_tokens * 0.002) / 1000
            print(f"  - 估算成本: ${estimated_cost:.4f} (仅供参考)")
        
        print("="*80)
    
    def export_to_markdown(self, output_file: str):
        """导出为 Markdown 格式"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# IO 日志分析报告\n\n")
            f.write(f"**日志文件**: `{self.log_file}`\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 写入摘要
            f.write("## 执行摘要\n\n")
            
            session_end = next((log for log in self.logs if log.get('type') == 'session_end'), None)
            if session_end:
                stats = session_end.get('statistics', {})
                f.write(f"- 总耗时: {session_end.get('duration', 0):.3f}s\n")
                f.write(f"- LLM 调用: {stats.get('call_counts', {}).get('llm', 0)} 次\n")
                f.write(f"- 工具调用: {stats.get('call_counts', {}).get('tool', 0)} 次\n")
                f.write(f"- 估算 Token: {stats.get('estimated_total_tokens', 0):,} tokens\n\n")
            
            # 写入 LLM 调用
            f.write("## LLM 调用详情\n\n")
            for i, log in enumerate(self.llm_calls, 1):
                phase = log.get('phase', 'unknown')
                duration = log.get('duration', 0)
                request = log.get('request', {})
                response = log.get('response', {})
                
                f.write(f"### [{i}] {phase}\n\n")
                f.write(f"- 耗时: {duration:.3f}s\n")
                f.write(f"- 温度: {request.get('temperature', 0.7)}\n")
                f.write(f"- 消息数: {len(request.get('messages', []))}\n\n")
                
                f.write("**提示词**:\n```\n")
                messages = request.get('messages', [])
                for msg in messages:
                    content = msg.get('content', '')
                    if len(content) > 500:
                        f.write(content[:250] + "\n...\n" + content[-250:] + "\n")
                    else:
                        f.write(content + "\n")
                f.write("```\n\n")
                
                f.write("**响应**:\n```json\n")
                f.write(response.get('content', '')[:500] + "\n")
                f.write("```\n\n")
        
        print(f"✅ 已导出 Markdown 报告: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_io_log.py <log_file.jsonl> [options]")
        print("\nOptions:")
        print("  -v, --verbose     显示详细内容")
        print("  -m, --markdown    导出 Markdown 报告")
        sys.exit(1)
    
    log_file = sys.argv[1]
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    export_md = '-m' in sys.argv or '--markdown' in sys.argv
    
    # 创建分析器
    analyzer = IOLogAnalyzer(log_file)
    
    # 打印分析结果
    analyzer.print_summary()
    analyzer.print_llm_calls(verbose=verbose)
    analyzer.print_tool_calls(verbose=verbose)
    analyzer.print_performance_analysis()
    
    # 导出 Markdown
    if export_md:
        md_file = log_file.replace('.jsonl', '_analysis.md')
        analyzer.export_to_markdown(md_file)


if __name__ == '__main__':
    main()

