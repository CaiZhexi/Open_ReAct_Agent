"""语义搜索服务 - 基于向量的知识库检索"""
import logging
from typing import List, Dict, Any, Optional
from app.models.database import DatabaseManager
from app.models.vector_store import vector_manager
from app.services.api_clients import embedding_client, rerank_client

logger = logging.getLogger(__name__)


def search_knowledge_base(
    query: str,
    kb_ids: List[int],
    top_k: int = 5,
    enable_rerank: bool = True
) -> Dict[str, Any]:
    """
    在知识库中进行语义搜索
    
    Args:
        query: 查询字符串
        kb_ids: 知识库ID列表
        top_k: 返回结果数量
        enable_rerank: 是否启用重排
    
    Returns:
        包含检索结果的字典
    """
    try:
        # 参数验证
        if not query or not query.strip():
            return {
                'success': False,
                'error': '查询内容不能为空',
                'chunks': []
            }
        
        if not kb_ids or not isinstance(kb_ids, list):
            return {
                'success': False,
                'error': '知识库ID列表不能为空',
                'chunks': []
            }
        
        # 获取查询向量
        logger.info(f"[搜索] 获取查询向量: {query[:50]}")
        query_embedding = embedding_client.get_embedding(query)
        
        if not query_embedding:
            return {
                'success': False,
                'error': '获取查询向量失败',
                'chunks': []
            }
        
        # 初始化数据库管理器
        db_manager = DatabaseManager()
        
        # 在多个知识库中搜索
        all_results = []
        for kb_id in kb_ids:
            try:
                kb = db_manager.get_knowledge_base(kb_id)
                if not kb:
                    logger.warning(f"[搜索] 知识库ID {kb_id} 不存在")
                    continue
                
                logger.info(f"[搜索] 在知识库 {kb['name']} 中搜索")
                
                # 获取向量存储
                vector_store = vector_manager.get_store(kb_id)
                
                # 向量搜索
                results = vector_store.search(query_embedding, top_k * 2)  # 取更多结果用于后续重排
                
                for result in results:
                    result['kb_id'] = kb_id
                    result['kb_name'] = kb['name']
                    all_results.append(result)
                    
            except Exception as e:
                logger.error(f"[搜索] 在知识库 {kb_id} 中搜索失败: {str(e)}")
                continue
        
        if not all_results:
            logger.info("[搜索] 未找到相关结果")
            return {
                'success': True,
                'chunks': [],
                'total': 0,
                'message': '未找到相关结果'
            }
        
        # 按相似度排序
        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # 如果启用重排，使用重排模型优化结果顺序
        if enable_rerank and len(all_results) > 0:
            try:
                logger.info(f"[搜索] 使用重排模型优化结果顺序")
                
                # 提取文档内容进行重排
                documents = [result.get('content', '') for result in all_results]
                
                # 执行重排
                rerank_results = rerank_client.rerank(
                    query=query,
                    documents=documents,
                    top_n=top_k
                )
                
                # 根据重排结果重新排序
                if rerank_results:
                    # 创建索引映射
                    reranked_results = []
                    for rerank_item in rerank_results:
                        original_index = rerank_item.get('index')
                        if isinstance(original_index, int) and original_index < len(all_results):
                            result = all_results[original_index].copy()
                            result['rerank_score'] = rerank_item.get('score', 0)
                            reranked_results.append(result)
                    
                    if reranked_results:
                        all_results = reranked_results
                        logger.info(f"[搜索] 重排完成: {len(reranked_results)} 个结果")
                        
            except Exception as e:
                logger.warning(f"[搜索] 重排失败，使用原始排序: {str(e)}")
                # 重排失败，继续使用原始排序
        
        # 返回前top_k个结果
        final_results = all_results[:top_k]
        
        logger.info(f"[搜索] 完成: 返回 {len(final_results)} 个结果")
        
        return {
            'success': True,
            'chunks': final_results,
            'total': len(final_results),
            'message': f'成功检索到 {len(final_results)} 个相关文档'
        }
        
    except Exception as e:
        logger.error(f"[搜索] 出错: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'搜索失败: {str(e)}',
            'chunks': []
        }
