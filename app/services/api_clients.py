"""API客户端服务"""
import requests
import json
import time
from typing import List, Dict, Any, Optional, Generator
from config import Config

class EmbeddingClient:
    """嵌入模型API客户端 - 支持多提供商"""
    
    def __init__(self):
        self.api_key = Config.EMBED_API_KEY
        self.base_url = Config.EMBED_API_URL
        self.model = Config.EMBED_MODEL
        self.dimensions = Config.EMBED_DIMENSIONS
        
        if not self.api_key:
            raise ValueError("未设置 EMBED_API_KEY")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取单个文本的嵌入向量"""
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else None
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本的嵌入向量"""
        if not texts:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
            "dimensions": self.dimensions
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 提取嵌入向量并按索引排序
            embeddings_data = result.get('data', [])
            embeddings_data.sort(key=lambda x: x.get('index', 0))
            
            embeddings = [item.get('embedding', []) for item in embeddings_data]
            return embeddings
            
        except requests.RequestException as e:
            print(f"嵌入API请求失败: {e}")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"嵌入API响应解析失败: {e}")
            return []

class RerankClient:
    """重排模型API客户端 - 支持多提供商"""
    
    def __init__(self):
        self.api_key = Config.RERANK_API_KEY
        self.base_url = Config.RERANK_API_URL
        self.model = Config.RERANK_MODEL
        
        if not self.api_key:
            raise ValueError("未设置 RERANK_API_KEY")
    
    def rerank(self, query: str, documents: List[str], top_n: int = None, 
              instruction: str = None) -> List[Dict[str, Any]]:
        """对文档列表进行重排序"""
        if not documents:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "return_documents": True
        }
        
        if top_n is not None:
            payload["top_n"] = min(top_n, len(documents))
        
        if instruction and self.model.startswith("Qwen/Qwen3-Reranker"):
            payload["instruction"] = instruction
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 提取重排结果
            rerank_results = []
            for item in result.get('results', []):
                rerank_results.append({
                    'index': item.get('index', 0),
                    'text': item.get('document', {}).get('text', ''),
                    'relevance_score': item.get('relevance_score', 0.0)
                })
            
            return rerank_results
            
        except requests.RequestException as e:
            print(f"重排API请求失败: {e}")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            print(f"重排API响应解析失败: {e}")
            return []

class ChatClient:
    """聊天模型API客户端 - 支持多提供商"""
    
    def __init__(self):
        self.api_key = Config.CHAT_API_KEY
        self.base_url = Config.CHAT_API_URL
        self.model = Config.CHAT_MODEL
        
        if not self.api_key:
            raise ValueError("未设置 CHAT_API_KEY")
    
    def chat(self, messages: List[Dict[str, str]], stream: bool = False, 
             max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """发送聊天请求"""
        if stream:
            return self._chat_stream(messages, max_tokens, temperature)
        else:
            return self._chat_non_stream(messages, max_tokens, temperature)
    
    def _chat_non_stream(self, messages: List[Dict[str, str]], 
                        max_tokens: int, temperature: float) -> str:
        """非流式聊天请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "enable_thinking": False,  # 根据要求禁用思考模式
            "stream": False
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 提取回答内容
            choices = result.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                return message.get('content', '抱歉，未能获取到回答。')
            else:
                return '抱歉，未能获取到回答。'
                
        except requests.RequestException as e:
            print(f"聊天API请求失败: {e}")
            return f"请求失败：{str(e)}"
        except (json.JSONDecodeError, KeyError) as e:
            print(f"聊天API响应解析失败: {e}")
            return "响应解析失败，请稍后重试。"
    
    def _chat_stream(self, messages: List[Dict[str, str]], 
                    max_tokens: int, temperature: float) -> str:
        """流式聊天请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "enable_thinking": False,
            "stream": True
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=120,
                stream=True
            )
            response.raise_for_status()
            
            content = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:].strip()
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get('choices', [])
                            if choices:
                                delta = choices[0].get('delta', {})
                                content_chunk = delta.get('content', '')
                                content += content_chunk
                        except json.JSONDecodeError:
                            continue
            
            return content or "抱歉，未能获取到回答。"
            
        except requests.RequestException as e:
            print(f"流式聊天API请求失败: {e}")
            return f"请求失败：{str(e)}"
    
    def chat_stream_generator(self, messages: List[Dict[str, str]], 
                             max_tokens: int = 2000, temperature: float = 0.7) -> Generator[str, None, None]:
        """流式聊天生成器（用于实时响应）"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "enable_thinking": False,
            "stream": True
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=120,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:].strip()
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get('choices', [])
                            if choices:
                                delta = choices[0].get('delta', {})
                                content_chunk = delta.get('content', '')
                                if content_chunk:
                                    yield content_chunk
                        except json.JSONDecodeError:
                            continue
                            
        except requests.RequestException as e:
            yield f"请求失败：{str(e)}"

class MetasoSearchClient:
    """网络搜索客户端 - 支持多提供商"""
    
    def __init__(self):
        self.api_key = Config.SEARCH_API_KEY
        self.search_url = Config.SEARCH_API_URL
        
        if not self.api_key:
            print("警告：未设置 SEARCH_API_KEY，网络搜索功能将不可用")
            self.api_key = None
    
    def search(self, query: str, top_k: int = 5, enable_deep_search: bool = False) -> Dict[str, Any]:
        """
        使用Metaso执行网络搜索
        
        Args:
            query: 搜索查询
            top_k: 返回的最大结果数量
            enable_deep_search: 保留参数以兼容旧代码
            
        Returns:
            包含搜索结果的字典
        """
        # 检查配置
        if not self.api_key:
            print("Metaso API Key未配置，跳过网络搜索")
            return {
                'success': False,
                'error': 'API Key未配置',
                'results': []
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "scope": "webpage",
            "includeSummary": True,
            "size": str(min(top_k, 10)),  # Metaso最多返回10条
            "includeRawContent": False,
            "conciseSnippet": True
        }
        
        try:
            response = requests.post(
                self.search_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"API返回错误（状态码: {response.status_code}）"
                print(f"Metaso搜索请求失败: {error_msg}")
                print(f"   响应: {response.text[:300]}")
                return {
                    'success': False,
                    'error': error_msg,
                    'results': []
                }
            
            result = response.json()
            
            # 提取网页搜索结果
            webpages = result.get('webpages', [])
            if not webpages:
                return {
                    'success': True,
                    'query': query,
                    'results': [],
                    'total': 0
                }
            
            # 转换为标准格式
            search_results = []
            for page in webpages[:top_k]:
                # 使用summary（如果有），否则使用snippet
                content = page.get('summary', page.get('snippet', ''))
                
                search_results.append({
                    'title': page.get('title', ''),
                    'url': page.get('link', ''),
                    'content': content,
                    'date': page.get('date', ''),
                    'score': page.get('score', 'medium'),
                    'position': page.get('position', 0),
                    'relevance_score': 0.9 if page.get('score') == 'high' else 0.7,
                    'type': 'web'
                })
            
            return {
                'success': True,
                'query': query,
                'results': search_results,
                'total': len(search_results),
                'credits_used': result.get('credits', 0)
            }
            
        except requests.RequestException as e:
            print(f"Metaso搜索API请求失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Metaso搜索API响应解析失败: {e}")
            return {
                'success': False,
                'error': f"响应解析失败: {str(e)}",
                'results': []
            }
    
# 全局客户端实例
embedding_client = EmbeddingClient()
chat_client = ChatClient()
rerank_client = RerankClient()
metaso_search_client = MetasoSearchClient()
# 保持向后兼容
baidu_search_client = metaso_search_client
