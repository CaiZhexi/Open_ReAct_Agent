"""
带日志记录的 API 客户端
在原有 API 客户端基础上，添加完整的 IO 日志记录
"""
import time
from typing import List, Dict, Any, Generator
from app.services.api_clients import (
    ChatClient as OriginalChatClient,
    EmbeddingClient as OriginalEmbeddingClient,
    RerankClient as OriginalRerankClient,
    MetasoSearchClient as OriginalMetasoSearchClient
)
from app.services.io_logger import get_logger


class ChatClientWithLogging(OriginalChatClient):
    """带日志记录的聊天模型客户端"""
    
    def chat(self, messages: List[Dict[str, str]], stream: bool = False, 
             max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """发送聊天请求（带日志记录）"""
        logger = get_logger()
        
        # 构造请求载荷
        request_payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': stream,
            'enable_thinking': False
        }
        
        # 推断当前阶段
        phase = self._infer_phase(messages)
        
        # 执行调用
        start_time = time.time()
        error = None
        response_content = ''
        
        try:
            response_content = super().chat(messages, stream, max_tokens, temperature)
            
            # 记录日志
            if logger.enabled:
                response_payload = {
                    'choices': [{
                        'message': {
                            'content': response_content
                        }
                    }],
                    'usage': {
                        # 如果 API 返回了 usage，这里可以填充
                        # 否则用估算值
                        'prompt_tokens': sum(len(m['content']) for m in messages) // 4,
                        'completion_tokens': len(response_content) // 4,
                        'total_tokens': (sum(len(m['content']) for m in messages) + len(response_content)) // 4
                    }
                }
                
                duration = time.time() - start_time
                logger.log_llm_call(phase, request_payload, response_payload, duration, None)
            
            return response_content
            
        except Exception as e:
            error = str(e)
            
            # 记录错误日志
            if logger.enabled:
                duration = time.time() - start_time
                logger.log_llm_call(phase, request_payload, {}, duration, error)
            
            raise
    
    def chat_stream_generator(self, messages: List[Dict[str, str]], 
                             max_tokens: int = 2000, temperature: float = 0.7) -> Generator[str, None, None]:
        """流式聊天生成器（带日志记录）"""
        logger = get_logger()
        
        # 构造请求载荷
        request_payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': True,
            'enable_thinking': False
        }
        
        phase = self._infer_phase(messages)
        
        # 执行调用
        start_time = time.time()
        accumulated_content = ''
        error = None
        
        try:
            for chunk in super().chat_stream_generator(messages, max_tokens, temperature):
                accumulated_content += chunk
                yield chunk
            
            # 记录完整的流式响应
            if logger.enabled:
                response_payload = {
                    'choices': [{
                        'message': {
                            'content': accumulated_content
                        }
                    }],
                    'usage': {
                        'prompt_tokens': sum(len(m['content']) for m in messages) // 4,
                        'completion_tokens': len(accumulated_content) // 4,
                        'total_tokens': (sum(len(m['content']) for m in messages) + len(accumulated_content)) // 4
                    }
                }
                
                duration = time.time() - start_time
                logger.log_llm_call(phase, request_payload, response_payload, duration, None)
        
        except Exception as e:
            error = str(e)
            
            if logger.enabled:
                duration = time.time() - start_time
                logger.log_llm_call(phase, request_payload, {'error': error}, duration, error)
            
            raise
    
    def _infer_phase(self, messages: List[Dict[str, str]]) -> str:
        """推断当前阶段（按优先级从高到低判断，避免误判）"""
        if not messages:
            return 'unknown'
        
        content = messages[0].get('content', '')
        
        # 优先级1: CodeGen（最具体）
        if '代码生成专家' in content or 'Python代码生成专家' in content:
            return 'CodeGen'
        
        # 优先级2: Answer（包含完整答案生成标识）
        if '专业问答助手' in content and '生成最终答案' in content:
            return 'Answer'
        if '请基于证据生成最终答案' in content:
            return 'Answer'
        
        # 优先级3: Final Evaluate（质量评估）
        if '请综合评估以下答案的质量' in content or ('AI回答' in content and '答案表达质量' in content):
            return 'FinalEvaluate'
        
        # 优先级4: Evaluate（信息充分性评估）
        if '信息充分性评估专家' in content or ('should_answer' in content and '请评估' in content):
            return 'Evaluate'
        
        # 优先级5: Plan（决策规划）
        if '决策' in content and '请决策' in content:
            return 'Plan'
        if 'ReAct (Reasoning + Acting) 智能体' in content and '可用工具定义' in content:
            return 'Plan'
        
        # 兜底：关键词匹配
        if '代码' in content and 'Python' in content:
            return 'CodeGen'
        elif '评估' in content:
            return 'Evaluate'
        elif '回答' in content:
            return 'Answer'
        else:
            return 'unknown'


class EmbeddingClientWithLogging(OriginalEmbeddingClient):
    """带日志记录的嵌入模型客户端"""
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本的嵌入向量（带日志记录）"""
        logger = get_logger()
        
        if not logger.enabled:
            return super().get_embeddings(texts)
        
        request_payload = {
            'model': self.model,
            'input': texts,
            'dimensions': self.dimensions,
            'text_count': len(texts),
            'total_chars': sum(len(t) for t in texts)
        }
        
        start_time = time.time()
        error = None
        
        try:
            embeddings = super().get_embeddings(texts)
            
            response_payload = {
                'embedding_count': len(embeddings),
                'dimension': len(embeddings[0]) if embeddings else 0
            }
            
            duration = time.time() - start_time
            logger.log_api_call('embed', request_payload, response_payload, duration, None)
            
            return embeddings
            
        except Exception as e:
            error = str(e)
            duration = time.time() - start_time
            logger.log_api_call('embed', request_payload, {'error': error}, duration, error)
            raise


class RerankClientWithLogging(OriginalRerankClient):
    """带日志记录的重排模型客户端"""
    
    def rerank(self, query: str, documents: List[str], top_n: int = None, 
              instruction: str = None) -> List[Dict[str, Any]]:
        """对文档列表进行重排序（带日志记录）"""
        logger = get_logger()
        
        if not logger.enabled:
            return super().rerank(query, documents, top_n, instruction)
        
        request_payload = {
            'model': self.model,
            'query': query,
            'document_count': len(documents),
            'top_n': top_n,
            'instruction': instruction
        }
        
        start_time = time.time()
        error = None
        
        try:
            results = super().rerank(query, documents, top_n, instruction)
            
            response_payload = {
                'result_count': len(results),
                'results': results[:3] if len(results) > 3 else results  # 只记录前3个
            }
            
            duration = time.time() - start_time
            logger.log_api_call('rerank', request_payload, response_payload, duration, None)
            
            return results
            
        except Exception as e:
            error = str(e)
            duration = time.time() - start_time
            logger.log_api_call('rerank', request_payload, {'error': error}, duration, error)
            raise


class MetasoSearchClientWithLogging(OriginalMetasoSearchClient):
    """带日志记录的网络搜索客户端"""
    
    def search(self, query: str, top_k: int = 5, enable_deep_search: bool = False) -> Dict[str, Any]:
        """执行网络搜索（带日志记录）"""
        logger = get_logger()
        
        if not logger.enabled:
            return super().search(query, top_k, enable_deep_search)
        
        request_payload = {
            'query': query,
            'top_k': top_k,
            'enable_deep_search': enable_deep_search
        }
        
        start_time = time.time()
        error = None
        
        try:
            result = super().search(query, top_k, enable_deep_search)
            
            # 记录完整的搜索结果（实际 HTTP 响应）
            response_payload = result
            
            duration = time.time() - start_time
            logger.log_api_call('search', request_payload, response_payload, duration, None)
            
            return result
            
        except Exception as e:
            error = str(e)
            duration = time.time() - start_time
            logger.log_api_call('search', request_payload, {'error': error}, duration, error)
            raise


# 创建全局实例
chat_client_with_logging = ChatClientWithLogging()
embedding_client_with_logging = EmbeddingClientWithLogging()
rerank_client_with_logging = RerankClientWithLogging()
search_client_with_logging = MetasoSearchClientWithLogging()

