"""
IO Logger - 记录所有 LLM 和工具的输入输出
在 API 客户端层面拦截请求和响应，记录完整的载荷信息
"""
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import wraps
import threading


class IOLogger:
    """IO 日志记录器 - 线程安全"""
    
    def __init__(self, log_file: str = None, http_only: bool = True):
        self.enabled = False
        self.log_file = log_file
        self.logs = []
        self.lock = threading.Lock()
        self.session_start = None
        self.http_only = http_only  # 只记录 HTTP 请求（LLM、搜索 API），不记录 Agent 层抽象
        self.call_counter = {
            'llm': 0,
            'tool': 0,
            'embed': 0,
            'rerank': 0,
            'search': 0
        }
        self.current_request_id = None  # 当前请求ID
        self.request_counter = 0  # 请求计数器
    
    def enable(self, log_file: str = None):
        """启用日志记录"""
        self.enabled = True
        self.session_start = time.time()
        
        if log_file:
            self.log_file = log_file
        elif not self.log_file:
            # 自动生成日志文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = f"logs/io_trace_{timestamp}.jsonl"
        
        # 确保日志目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # 写入会话开始标记
        self._write_log({
            'type': 'session_start',
            'timestamp': datetime.now().isoformat(),
            'log_file': self.log_file
        })
        
        print(f"✅ IO 日志记录已启用: {self.log_file}")
    
    def disable(self):
        """禁用日志记录"""
        if self.enabled:
            # 写入会话结束标记
            self._write_log({
                'type': 'session_end',
                'timestamp': datetime.now().isoformat(),
                'duration': time.time() - self.session_start if self.session_start else 0,
                'statistics': self.get_statistics()
            })
            print(f"✅ IO 日志记录已保存: {self.log_file}")
        
        self.enabled = False
    
    def start_request(self, query: str, metadata: Dict[str, Any] = None) -> str:
        """
        开始一个新的用户请求，返回request_id
        
        Args:
            query: 用户查询
            metadata: 额外的元数据（如kb_ids等）
        
        Returns:
            request_id: 请求唯一标识
        """
        if not self.enabled:
            return None
        
        with self.lock:
            self.request_counter += 1
            request_id = f"req_{self.request_counter}_{int(time.time())}"
            self.current_request_id = request_id
        
        # 记录请求开始事件
        self._write_log({
            'type': 'request_start',
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'metadata': metadata or {}
        })
        
        return request_id
    
    def end_request(self, request_id: str, result: Dict[str, Any] = None):
        """
        结束一个用户请求
        
        Args:
            request_id: 请求ID
            result: 最终结果（可选）
        """
        if not self.enabled:
            return
        
        # 记录请求结束事件
        self._write_log({
            'type': 'request_end',
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'result_summary': {
                'success': result.get('success', False) if result else None,
                'answer_length': len(result.get('answer', '')) if result else 0
            } if result else None
        })
        
        # 清除当前request_id
        with self.lock:
            if self.current_request_id == request_id:
                self.current_request_id = None
    
    def log_llm_call(self, 
                     phase: str,
                     request_payload: Dict[str, Any],
                     response_payload: Dict[str, Any],
                     duration: float,
                     error: Optional[str] = None):
        """记录 LLM 调用"""
        if not self.enabled:
            return
        
        with self.lock:
            self.call_counter['llm'] += 1
            call_id = self.call_counter['llm']
        
        # 提取关键信息
        messages = request_payload.get('messages', [])
        model = request_payload.get('model', 'unknown')
        temperature = request_payload.get('temperature', 0.7)
        max_tokens = request_payload.get('max_tokens', 2000)
        
        # 计算上下文长度（估算）
        total_chars = sum(len(m.get('content', '')) for m in messages)
        estimated_tokens = total_chars // 4  # 粗略估算：4字符≈1token
        
        # 提取响应内容
        response_content = ''
        usage = {}
        if not error and response_payload:
            choices = response_payload.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                response_content = message.get('content', '')
            usage = response_payload.get('usage', {})
        
        log_entry = {
            'type': 'llm_call',
            'call_id': call_id,
            'request_id': self.current_request_id,  # 关联到当前请求
            'timestamp': datetime.now().isoformat(),
            'phase': phase,
            'duration': round(duration, 3),
            
            # 请求信息
            'request': {
                'model': model,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': request_payload.get('stream', False),
                'messages': messages,
                'message_count': len(messages),
            },
            
            # 响应信息
            'response': {
                'content': response_content,
                'content_length': len(response_content),
                'error': error,
                'raw_response': response_payload if error else None
            },
            
            # 性能统计
            'performance': {
                'duration_ms': round(duration * 1000, 2),
                'estimated_input_tokens': estimated_tokens,
                'estimated_output_tokens': len(response_content) // 4,
                'usage': usage  # 如果 API 返回了 usage 信息
            },
            
            # 原始载荷（用于调试）
            'raw_request': request_payload,
            'raw_response': response_payload
        }
        
        self._write_log(log_entry)
    
    def log_tool_call(self,
                     tool_name: str,
                     tool_type: str,  # 'vector_search', 'web_search', 'python_code'
                     request_args: Dict[str, Any],
                     response_data: Dict[str, Any],
                     duration: float,
                     error: Optional[str] = None):
        """记录工具调用"""
        if not self.enabled:
            return
        
        # http_only 模式：跳过 Agent 层的工具调用记录（避免与 HTTP 层重复）
        if self.http_only:
            return
        
        with self.lock:
            self.call_counter['tool'] += 1
            call_id = self.call_counter['tool']
        
        # 根据工具类型提取关键信息
        summary = self._summarize_tool_result(tool_name, response_data)
        
        log_entry = {
            'type': 'tool_call',
            'call_id': call_id,
            'request_id': self.current_request_id,  # 关联到当前请求
            'timestamp': datetime.now().isoformat(),
            'tool_name': tool_name,
            'tool_type': tool_type,
            'duration': round(duration, 3),
            
            # 请求信息
            'request': request_args,
            
            # 响应信息
            'response': {
                'summary': summary,
                'data': response_data,
                'error': error
            },
            
            # 性能统计
            'performance': {
                'duration_ms': round(duration * 1000, 2),
                'result_count': self._count_results(tool_name, response_data),
                'data_size_bytes': len(json.dumps(response_data, ensure_ascii=False))
            }
        }
        
        self._write_log(log_entry)
    
    def log_api_call(self,
                    api_type: str,  # 'embed', 'rerank', 'search'
                    request_payload: Dict[str, Any],
                    response_payload: Dict[str, Any],
                    duration: float,
                    error: Optional[str] = None):
        """记录其他 API 调用（embedding、rerank、搜索等）"""
        if not self.enabled:
            return
        
        with self.lock:
            self.call_counter[api_type] += 1
            call_id = self.call_counter[api_type]
        
        log_entry = {
            'type': f'{api_type}_call',
            'call_id': call_id,
            'request_id': self.current_request_id,  # 关联到当前请求
            'timestamp': datetime.now().isoformat(),
            'duration': round(duration, 3),
            
            'request': request_payload,
            'response': response_payload,
            'error': error,
            
            'performance': {
                'duration_ms': round(duration * 1000, 2),
                'request_size_bytes': len(json.dumps(request_payload, ensure_ascii=False)),
                'response_size_bytes': len(json.dumps(response_payload, ensure_ascii=False))
            }
        }
        
        self._write_log(log_entry)
    
    def _write_log(self, log_entry: Dict[str, Any]):
        """写入日志到文件"""
        with self.lock:
            self.logs.append(log_entry)
            
            # 写入 JSONL 格式（每行一个 JSON 对象）
            if self.log_file:
                try:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                except Exception as e:
                    print(f"⚠️  写入日志失败: {e}")
    
    def _summarize_tool_result(self, tool_name: str, response_data: Dict[str, Any]) -> str:
        """生成工具结果摘要"""
        if tool_name == 'vector_search':
            chunks = response_data.get('chunks', [])
            if chunks:
                avg_score = sum(c.get('score', 0) for c in chunks) / len(chunks)
                return f"检索到 {len(chunks)} 条文档，平均相关度 {avg_score:.3f}"
            return "未检索到文档"
        
        elif tool_name == 'web_search':
            results = response_data.get('results', [])
            return f"搜索到 {len(results)} 条网络信息"
        
        elif tool_name == 'python_code':
            if response_data.get('error'):
                return f"代码执行失败: {response_data['error']}"
            output = response_data.get('output', '')
            return f"代码执行成功，输出 {len(output)} 字符"
        
        return "执行完成"
    
    def _count_results(self, tool_name: str, response_data: Dict[str, Any]) -> int:
        """统计结果数量"""
        if tool_name == 'vector_search':
            return len(response_data.get('chunks', []))
        elif tool_name == 'web_search':
            return len(response_data.get('results', []))
        elif tool_name == 'python_code':
            return 1 if response_data.get('output') else 0
        return 0
    
    def log_event(self, event: Dict[str, Any]):
        """
        记录一个通用事件
        
        Args:
            event: 事件字典，必须包含 'type' 字段
        """
        if not self.enabled:
            return
        
        # http_only 模式：跳过 Flask API 请求日志（只保留外部 HTTP 调用）
        if self.http_only and event.get('type') == 'api_request':
            return
        
        try:
            self.logs.append(event)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  写入事件日志失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息（公开方法）
        
        Returns:
            统计信息字典
        """
        total_llm_time = 0
        total_tool_time = 0
        total_tokens_in = 0
        total_tokens_out = 0
        
        for log in self.logs:
            if log['type'] == 'llm_call':
                total_llm_time += log['duration']
                perf = log.get('performance', {})
                total_tokens_in += perf.get('estimated_input_tokens', 0)
                total_tokens_out += perf.get('estimated_output_tokens', 0)
            elif log['type'] == 'tool_call':
                total_tool_time += log['duration']
        
        return {
            'call_counts': self.call_counter.copy(),
            'total_llm_time': round(total_llm_time, 3),
            'total_tool_time': round(total_tool_time, 3),
            'total_time': round(total_llm_time + total_tool_time, 3),
            'estimated_total_tokens': total_tokens_in + total_tokens_out,
            'estimated_input_tokens': total_tokens_in,
            'estimated_output_tokens': total_tokens_out
        }
    
    def get_summary(self) -> str:
        """获取可读的摘要"""
        stats = self.get_statistics()
        
        lines = [
            "\n" + "="*80,
            "IO 日志统计摘要",
            "="*80,
            f"LLM 调用: {stats['call_counts']['llm']} 次 (耗时 {stats['total_llm_time']:.3f}s)",
            f"工具调用: {stats['call_counts']['tool']} 次 (耗时 {stats['total_tool_time']:.3f}s)",
            f"总耗时: {stats['total_time']:.3f}s",
            f"估算 Token 消耗: {stats['estimated_total_tokens']} tokens",
            f"  - 输入: {stats['estimated_input_tokens']} tokens",
            f"  - 输出: {stats['estimated_output_tokens']} tokens",
            f"日志文件: {self.log_file}",
            "="*80 + "\n"
        ]
        
        return "\n".join(lines)


# 全局单例 - 默认只记录 HTTP 请求层面的日志
_global_logger = IOLogger(http_only=True)


def get_logger() -> IOLogger:
    """获取全局 IO 日志记录器"""
    return _global_logger


def enable_io_logging(log_file: str = None):
    """启用 IO 日志记录"""
    _global_logger.enable(log_file)


def disable_io_logging():
    """禁用 IO 日志记录"""
    _global_logger.disable()


# ============ 装饰器：自动记录函数调用 ============

def log_llm_io(phase: str):
    """装饰器：记录 LLM 调用的 IO"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            if not logger.enabled:
                return func(*args, **kwargs)
            
            # 提取请求参数
            # 假设第一个参数是 self，第二个是 messages
            messages = args[1] if len(args) > 1 else kwargs.get('messages', [])
            temperature = kwargs.get('temperature', 0.7)
            max_tokens = kwargs.get('max_tokens', 2000)
            stream = kwargs.get('stream', False)
            
            # 构造请求载荷
            request_payload = {
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'stream': stream,
                'model': args[0].model if hasattr(args[0], 'model') else 'unknown'
            }
            
            # 执行调用
            start_time = time.time()
            error = None
            response_payload = {}
            
            try:
                result = func(*args, **kwargs)
                response_payload = {'choices': [{'message': {'content': result}}]}
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration = time.time() - start_time
                logger.log_llm_call(phase, request_payload, response_payload, duration, error)
        
        return wrapper
    return decorator


def log_tool_io(tool_name: str, tool_type: str):
    """装饰器：记录工具调用的 IO"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            if not logger.enabled:
                return func(*args, **kwargs)
            
            # 执行调用
            start_time = time.time()
            error = None
            
            try:
                result = func(*args, **kwargs)
                logger.log_tool_call(tool_name, tool_type, kwargs, result, 
                                    time.time() - start_time, None)
                return result
            except Exception as e:
                error = str(e)
                logger.log_tool_call(tool_name, tool_type, kwargs, {}, 
                                    time.time() - start_time, error)
                raise
        
        return wrapper
    return decorator

