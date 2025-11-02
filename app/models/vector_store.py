"""向量数据库管理"""
import os
import json
import uuid
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from config import Config

class VectorStore:
    """基于Faiss的向量数据库"""
    
    def __init__(self, kb_id: int):
        self.kb_id = kb_id
        self.vector_db_path = Config.VECTOR_DB_PATH
        self.dimensions = Config.EMBED_DIMENSIONS
        
        # 创建知识库专用的向量存储目录
        self.kb_vector_dir = os.path.join(self.vector_db_path, f"kb_{kb_id}")
        os.makedirs(self.kb_vector_dir, exist_ok=True)
        
        # 索引文件路径
        self.index_file = os.path.join(self.kb_vector_dir, "faiss.index")
        self.metadata_file = os.path.join(self.kb_vector_dir, "metadata.json")
        
        # 初始化或加载索引
        self.index = None
        self.metadata = {}
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """加载或创建Faiss索引"""
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            # 加载现有索引
            self.index = faiss.read_index(self.index_file)
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            # 创建新索引（使用Inner Product相似度）
            self.index = faiss.IndexFlatIP(self.dimensions)
            self.metadata = {}
            self._save_index()
    
    def _save_index(self):
        """保存索引到磁盘"""
        faiss.write_index(self.index, self.index_file)
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def add_vectors(self, vectors: List[List[float]], chunk_ids: List[str], 
                   contents: List[str], doc_names: List[str]) -> bool:
        """添加向量到索引"""
        if not vectors or len(vectors) != len(chunk_ids):
            return False
        
        # 转换为numpy数组并标准化
        vectors_array = np.array(vectors, dtype=np.float32)
        
        # L2标准化（为Inner Product相似度做准备）
        faiss.normalize_L2(vectors_array)
        
        # 添加到索引
        start_id = self.index.ntotal
        self.index.add(vectors_array)
        
        # 更新元数据
        for i, (chunk_id, content, doc_name) in enumerate(zip(chunk_ids, contents, doc_names)):
            self.metadata[str(start_id + i)] = {
                'chunk_id': chunk_id,
                'content': content,
                'doc_name': doc_name
            }
        
        # 保存到磁盘
        self._save_index()
        return True
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        if self.index.ntotal == 0:
            return []
        
        # 转换并标准化查询向量
        query_array = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        # 执行搜索
        scores, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
        
        # 构建结果
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # Faiss返回-1表示无效索引
                continue
                
            metadata = self.metadata.get(str(idx), {})
            results.append({
                'score': float(score),
                'chunk_id': metadata.get('chunk_id', ''),
                'content': metadata.get('content', ''),
                'doc_name': metadata.get('doc_name', '')
            })
        
        return results
    
    def delete_document_vectors(self, doc_name: str) -> bool:
        """删除文档的所有向量（通过重建索引实现）"""
        if not self.metadata:
            return True
        
        # 收集需要保留的向量
        keep_vectors = []
        keep_metadata = {}
        new_index = 0
        
        for old_idx, meta in self.metadata.items():
            if meta.get('doc_name') != doc_name:
                # 获取原向量
                old_idx_int = int(old_idx)
                if old_idx_int < self.index.ntotal:
                    vector = self.index.reconstruct(old_idx_int)
                    keep_vectors.append(vector)
                    keep_metadata[str(new_index)] = meta
                    new_index += 1
        
        # 重建索引
        self.index = faiss.IndexFlatIP(self.dimensions)
        if keep_vectors:
            vectors_array = np.array(keep_vectors, dtype=np.float32)
            self.index.add(vectors_array)
        
        self.metadata = keep_metadata
        self._save_index()
        return True
    
    def clear(self) -> bool:
        """清空所有向量"""
        self.index = faiss.IndexFlatIP(self.dimensions)
        self.metadata = {}
        self._save_index()
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量库统计信息"""
        return {
            'total_vectors': self.index.ntotal,
            'dimensions': self.dimensions,
            'unique_documents': len(set(
                meta.get('doc_name', '') for meta in self.metadata.values()
            ))
        }

class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(self):
        self._stores: Dict[int, VectorStore] = {}
    
    def get_store(self, kb_id: int) -> VectorStore:
        """获取知识库的向量存储"""
        if kb_id not in self._stores:
            self._stores[kb_id] = VectorStore(kb_id)
        return self._stores[kb_id]
    
    def delete_store(self, kb_id: int) -> bool:
        """删除知识库的向量存储"""
        # 从内存中删除
        if kb_id in self._stores:
            del self._stores[kb_id]
        
        # 删除磁盘文件
        kb_vector_dir = os.path.join(Config.VECTOR_DB_PATH, f"kb_{kb_id}")
        if os.path.exists(kb_vector_dir):
            import shutil
            shutil.rmtree(kb_vector_dir)
        
        return True
    
    def get_all_stats(self) -> Dict[int, Dict[str, Any]]:
        """获取所有知识库的向量统计"""
        stats = {}
        vector_base_dir = Config.VECTOR_DB_PATH
        
        if os.path.exists(vector_base_dir):
            for item in os.listdir(vector_base_dir):
                if item.startswith("kb_"):
                    try:
                        kb_id = int(item.split("_")[1])
                        store = self.get_store(kb_id)
                        stats[kb_id] = store.get_stats()
                    except (ValueError, IndexError):
                        continue
        
        return stats

# 全局向量存储管理器实例
vector_manager = VectorStoreManager()
