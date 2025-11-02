"""数据库模型和初始化"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from config import Config

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建知识库表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_bases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'ready',
                    processing_progress REAL DEFAULT 0.0,
                    total_pending_docs INTEGER DEFAULT 0,
                    processed_docs INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建文档表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    file_type VARCHAR(50),
                    file_size INTEGER,
                    chunk_count INTEGER DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'processed',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
                )
            """)
            
            # 创建文档处理队列表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_processing_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kb_id INTEGER NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    file_size INTEGER NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
                )
            """)
            
            # 创建文档块表（用于存储分块后的文档片段）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    vector_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_id ON documents(kb_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(doc_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_vector_id ON document_chunks(vector_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_kb_id ON document_processing_queue(kb_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON document_processing_queue(status)")
            
            conn.commit()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        return conn
    
    # 知识库相关操作
    def create_knowledge_base(self, name: str, description: str = "") -> int:
        """创建知识库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO knowledge_bases (name, description) VALUES (?, ?)",
                (name, description)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_knowledge_bases(self) -> List[Dict[str, Any]]:
        """获取所有知识库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_bases ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_knowledge_base(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取知识库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_knowledge_base(self, kb_id: int, name: str = None, description: str = None) -> bool:
        """更新知识库"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
            
        if not updates:
            return False
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(kb_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_knowledge_base(self, kb_id: int) -> bool:
        """删除知识库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # 文档相关操作
    def create_document(self, kb_id: int, name: str, content: str, 
                       file_type: str = None, file_size: int = None, status: str = 'processed') -> int:
        """创建文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (kb_id, name, content, file_type, file_size, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (kb_id, name, content, file_type, file_size, status))
            conn.commit()
            return cursor.lastrowid
    
    def get_documents(self, kb_id: int) -> List[Dict[str, Any]]:
        """获取知识库的所有文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, kb_id, name, file_type, file_size, chunk_count, 
                       status, error_message, created_at, updated_at
                FROM documents 
                WHERE kb_id = ? 
                ORDER BY created_at DESC
            """, (kb_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_document(self, doc_id: int, name: str = None, content: str = None) -> bool:
        """更新文档"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
            
        if not updates:
            return False
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(doc_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE documents SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_document(self, doc_id: int) -> bool:
        """删除文档"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # 文档块相关操作
    def create_document_chunks(self, doc_id: int, chunks: List[Dict[str, Any]]) -> bool:
        """批量创建文档块"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 先删除现有的块
            cursor.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
            
            # 插入新的块
            chunk_data = [
                (doc_id, chunk['chunk_index'], chunk['content'], chunk.get('vector_id'))
                for chunk in chunks
            ]
            cursor.executemany("""
                INSERT INTO document_chunks (doc_id, chunk_index, content, vector_id)
                VALUES (?, ?, ?, ?)
            """, chunk_data)
            
            # 更新文档的块数量
            cursor.execute("""
                UPDATE documents SET chunk_count = ? WHERE id = ?
            """, (len(chunks), doc_id))
            
            conn.commit()
            return True
    
    def get_document_chunks(self, doc_id: int) -> List[Dict[str, Any]]:
        """获取文档的所有块"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM document_chunks 
                WHERE doc_id = ? 
                ORDER BY chunk_index
            """, (doc_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_chunk_by_vector_id(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """根据向量ID获取文档块"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dc.*, d.name as doc_name, d.kb_id, kb.name as kb_name
                FROM document_chunks dc
                JOIN documents d ON dc.doc_id = d.id
                JOIN knowledge_bases kb ON d.kb_id = kb.id
                WHERE dc.vector_id = ?
            """, (vector_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # 知识库状态管理
    def update_knowledge_base_status(self, kb_id: int, status: str, 
                                   total_pending: int = None, processed: int = None) -> bool:
        """更新知识库状态"""
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if total_pending is not None:
            updates.append("total_pending_docs = ?")
            params.append(total_pending)
        
        if processed is not None:
            updates.append("processed_docs = ?")
            params.append(processed)
        
        # 计算进度
        if total_pending is not None and processed is not None and total_pending > 0:
            progress = processed / total_pending
            updates.append("processing_progress = ?")
            params.append(progress)
        elif status == 'ready':
            updates.append("processing_progress = ?")
            params.append(1.0)
        
        params.append(kb_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE knowledge_bases SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_knowledge_base_status(self, kb_id: int) -> Optional[Dict[str, Any]]:
        """获取知识库状态信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, processing_progress, total_pending_docs, processed_docs
                FROM knowledge_bases WHERE id = ?
            """, (kb_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # 文档处理队列管理
    def add_to_processing_queue(self, queue_items: List[Dict[str, Any]]) -> List[int]:
        """批量添加文档到处理队列"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            queue_ids = []
            for item in queue_items:
                cursor.execute("""
                    INSERT INTO document_processing_queue 
                    (kb_id, file_name, file_path, file_type, file_size)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    item['kb_id'], 
                    item['file_name'], 
                    item['file_path'],
                    item['file_type'], 
                    item['file_size']
                ))
                queue_ids.append(cursor.lastrowid)
            
            conn.commit()
            return queue_ids
    
    def get_pending_queue_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取待处理的队列项目"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM document_processing_queue 
                WHERE status = 'pending' 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_queue_item_status(self, queue_id: int, status: str, 
                                error_message: str = None) -> bool:
        """更新队列项目状态"""
        updates = ["status = ?"]
        params = [status]
        
        if status == 'processing':
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in ['completed', 'failed']:
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        if error_message:
            updates.append("error_message = ?")
            params.append(error_message)
        
        params.append(queue_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE document_processing_queue SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_queue_stats_for_kb(self, kb_id: int) -> Dict[str, int]:
        """获取知识库的队列处理统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) as pending,
                    COALESCE(SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END), 0) as processing,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed,
                    COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) as failed
                FROM document_processing_queue 
                WHERE kb_id = ?
            """, (kb_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 确保所有值都是整数
                for key in ['total', 'pending', 'processing', 'completed', 'failed']:
                    result[key] = int(result[key] or 0)
                return result
            else:
                return {'total': 0, 'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0}
    
    def cleanup_completed_queue_items(self, kb_id: int) -> bool:
        """清理已完成的队列项目"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM document_processing_queue 
                WHERE kb_id = ? AND status IN ('completed', 'failed')
            """, (kb_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_kb_processing_queue(self, kb_id: int) -> bool:
        """清空指定知识库的处理队列（删除pending和processing状态的项）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM document_processing_queue 
                WHERE kb_id = ? AND status IN ('pending', 'processing')
            """, (kb_id,))
            conn.commit()
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                print(f"已删除 {deleted_count} 个待处理/处理中的队列项")
            return True
