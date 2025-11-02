"""文档处理队列服务"""
import os
import time
import threading
from typing import List, Dict, Any
from datetime import datetime
from app.models.database import DatabaseManager
from app.models.vector_store import vector_manager
from app.services.document_processor import document_processor
from app.services.api_clients import embedding_client

class DocumentProcessingQueue:
    """文档处理队列"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.processing = False
        self.worker_thread = None
        self.stop_flag = False
    
    def start_processing(self):
        """启动处理线程"""
        if self.processing:
            return
        
        self.processing = True
        self.stop_flag = False
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        print("📋 文档处理队列已启动")
    
    def stop_processing(self):
        """停止处理线程"""
        if not self.processing:
            return
        
        self.stop_flag = True
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)  # 等待最多5秒
        
        self.processing = False
        print("📋 文档处理队列已停止")
    
    def _process_queue(self):
        """处理队列的主循环"""
        print("🔄 开始处理文档队列...")
        
        while not self.stop_flag:
            try:
                # 获取待处理的队列项目
                queue_items = self.db_manager.get_pending_queue_items(limit=5)
                
                if not queue_items:
                    # 没有待处理项目，休眠2秒
                    time.sleep(2)
                    continue
                
                for item in queue_items:
                    if self.stop_flag:
                        break
                    
                    self._process_single_item(item)
                
            except Exception as e:
                print(f"队列处理出错: {e}")
                time.sleep(5)  # 出错时休眠5秒再重试
        
        print("📋 文档队列处理循环结束")
    
    def _process_single_item(self, item: Dict[str, Any]):
        """处理单个队列项目"""
        queue_id = item['id']
        kb_id = item['kb_id']
        file_name = item['file_name']
        file_path = item['file_path']
        file_type = item['file_type']
        
        print(f"🔄 开始处理文档: {file_name}")
        
        try:
            # 更新状态为处理中
            self.db_manager.update_queue_item_status(queue_id, 'processing')
            
            # 验证文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 提取文档内容
            content = document_processor.extract_text_from_file(file_path, file_type)
            
            if not content.strip():
                raise ValueError("文件内容为空")
            
            # 创建文档记录
            doc_id = self.db_manager.create_document(
                kb_id=kb_id,
                name=file_name,
                content=content,
                file_type=file_type,
                file_size=item['file_size']
            )
            
            # 分割文档为块
            chunks = document_processor.split_text_into_chunks(content)
            
            if chunks:
                # 获取文本嵌入向量
                chunk_contents = [chunk['content'] for chunk in chunks]
                embeddings = embedding_client.get_embeddings(chunk_contents)
                
                if len(embeddings) == len(chunks):
                    # 存储向量
                    vector_store = vector_manager.get_store(kb_id)
                    vector_store.add_vectors(
                        vectors=embeddings,
                        chunk_ids=[chunk['vector_id'] for chunk in chunks],
                        contents=chunk_contents,
                        doc_names=[file_name] * len(chunks)
                    )
                    
                    # 存储文档块
                    self.db_manager.create_document_chunks(doc_id, chunks)
                    
                    print(f"✅ 文档处理成功: {file_name} ({len(chunks)}个块)")
                else:
                    print(f"⚠️ 嵌入向量数量不匹配: {file_name}")
            
            # 清理临时文件
            try:
                os.unlink(file_path)
            except:
                pass  # 忽略文件删除错误
            
            # 更新队列项目状态为完成
            self.db_manager.update_queue_item_status(queue_id, 'completed')
            
            # 更新知识库处理进度
            self._update_kb_progress(kb_id)
            
        except Exception as e:
            error_message = str(e)
            print(f"❌ 文档处理失败: {file_name} - {error_message}")
            
            # 更新队列项目状态为失败
            self.db_manager.update_queue_item_status(queue_id, 'failed', error_message)
            
            # 清理临时文件
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
            
            # 仍然需要更新知识库进度
            self._update_kb_progress(kb_id)
    
    def _update_kb_progress(self, kb_id: int):
        """更新知识库处理进度"""
        try:
            # 获取队列统计
            stats = self.db_manager.get_queue_stats_for_kb(kb_id)
            
            total = stats['total']
            completed = stats['completed']
            failed = stats['failed']
            processing = stats['processing']
            pending = stats['pending']
            
            # 计算已处理数量（包括成功和失败）
            processed = completed + failed
            
            if total == 0:
                # 没有队列项目，设置为就绪状态
                self.db_manager.update_knowledge_base_status(kb_id, 'ready', 0, 0)
            elif pending == 0 and processing == 0:
                # 所有项目都处理完成
                self.db_manager.update_knowledge_base_status(kb_id, 'ready', total, processed)
                # 清理已完成的队列项目
                self.db_manager.cleanup_completed_queue_items(kb_id)
                print(f"🎉 知识库 {kb_id} 所有文档处理完成")
            else:
                # 仍在处理中
                self.db_manager.update_knowledge_base_status(kb_id, 'processing', total, processed)
                print(f"📊 知识库 {kb_id} 处理进度: {processed}/{total}")
        
        except Exception as e:
            print(f"更新知识库进度失败: {e}")
    
    def add_documents_to_queue(self, kb_id: int, files_info: List[Dict[str, Any]]) -> bool:
        """批量添加文档到处理队列"""
        try:
            # 准备队列项目
            queue_items = []
            for file_info in files_info:
                queue_items.append({
                    'kb_id': kb_id,
                    'file_name': file_info['file_name'],
                    'file_path': file_info['file_path'],
                    'file_type': file_info['file_type'],
                    'file_size': file_info['file_size']
                })
            
            # 添加到队列
            queue_ids = self.db_manager.add_to_processing_queue(queue_items)
            
            # 更新知识库状态为处理中
            self.db_manager.update_knowledge_base_status(
                kb_id, 'processing', 
                total_pending=len(queue_items), 
                processed=0
            )
            
            print(f"📋 已添加 {len(queue_items)} 个文档到处理队列")
            
            # 如果处理线程未启动，启动它
            if not self.processing:
                self.start_processing()
            
            return True
            
        except Exception as e:
            print(f"添加文档到队列失败: {e}")
            return False
    
    def get_queue_status(self, kb_id: int) -> Dict[str, Any]:
        """获取知识库的队列处理状态"""
        try:
            # 获取知识库状态
            kb_status = self.db_manager.get_knowledge_base_status(kb_id)
            
            # 获取队列统计
            queue_stats = self.db_manager.get_queue_stats_for_kb(kb_id)
            
            return {
                'kb_status': kb_status,
                'queue_stats': queue_stats,
                'processing_active': self.processing
            }
        
        except Exception as e:
            print(f"获取队列状态失败: {e}")
            return {
                'kb_status': None,
                'queue_stats': {'total': 0, 'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0},
                'processing_active': False
            }
    
    def clear_kb_queue(self, kb_id: int) -> bool:
        """清空指定知识库的处理队列"""
        try:
            # 删除该知识库的所有pending和processing状态的队列项
            self.db_manager.clear_kb_processing_queue(kb_id)
            print(f"📋 已清空知识库 {kb_id} 的处理队列")
            return True
        except Exception as e:
            print(f"清空队列失败: {e}")
            return False

# 全局文档处理队列实例
document_queue = DocumentProcessingQueue()
