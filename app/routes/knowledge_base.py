"""资源管理API"""
from flask import Blueprint, request, jsonify
from app.models.database import DatabaseManager
from app.models.vector_store import vector_manager
from app.services.document_queue import document_queue
from app.utils.security import require_api_key, make_error_response

# 创建蓝图
kb_bp = Blueprint('knowledge_base', __name__, url_prefix='/api/kb')

# 初始化数据库管理器
db_manager = DatabaseManager()

@kb_bp.route('/list', methods=['GET'])
def list_knowledge_bases():
    """获取知识库列表"""
    try:
        knowledge_bases = db_manager.get_knowledge_bases()
        
        # 获取向量统计信息
        vector_stats = vector_manager.get_all_stats()
        
        # 补充统计信息
        for kb in knowledge_bases:
            kb_id = kb['id']
            kb['vector_stats'] = vector_stats.get(kb_id, {
                'total_vectors': 0,
                'dimensions': 0,
                'unique_documents': 0
            })
            
            # 获取文档数量
            documents = db_manager.get_documents(kb_id)
            kb['document_count'] = len(documents)
            
            # 获取处理状态信息
            status_info = document_queue.get_queue_status(kb_id)
            kb['status'] = status_info['kb_status']['status'] if status_info['kb_status'] else 'ready'
            kb['processing_progress'] = status_info['kb_status']['processing_progress'] if status_info['kb_status'] else 1.0
            kb['is_ready'] = kb['status'] == 'ready'
            
            # 添加队列信息
            if kb['status'] == 'processing':
                kb['queue_info'] = {
                    'total_pending': status_info['kb_status']['total_pending_docs'] if status_info['kb_status'] else 0,
                    'processed': status_info['kb_status']['processed_docs'] if status_info['kb_status'] else 0,
                    'queue_stats': status_info['queue_stats']
                }
        
        return jsonify({
            'success': True,
            'data': knowledge_bases,
            'message': '获取知识库列表成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取知识库列表失败')

@kb_bp.route('/create', methods=['POST'])
@require_api_key
def create_knowledge_base():
    """创建知识库"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({
                'success': False,
                'message': '知识库名称不能为空'
            }), 400
        
        # 检查名称是否已存在
        existing_kbs = db_manager.get_knowledge_bases()
        for kb in existing_kbs:
            if kb['name'] == name:
                return jsonify({
                    'success': False,
                    'message': '知识库名称已存在'
                }), 400
        
        # 创建知识库
        kb_id = db_manager.create_knowledge_base(name, description)
        
        # 获取创建的知识库信息
        new_kb = db_manager.get_knowledge_base(kb_id)
        
        return jsonify({
            'success': True,
            'data': new_kb,
            'message': '知识库创建成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='创建知识库失败')

@kb_bp.route('/<int:kb_id>', methods=['GET'])
def get_knowledge_base(kb_id):
    """获取知识库详情"""
    try:
        kb = db_manager.get_knowledge_base(kb_id)
        
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        # 获取文档列表
        documents = db_manager.get_documents(kb_id)
        kb['documents'] = documents
        kb['document_count'] = len(documents)
        
        # 获取向量统计信息
        vector_store = vector_manager.get_store(kb_id)
        kb['vector_stats'] = vector_store.get_stats()
        
        return jsonify({
            'success': True,
            'data': kb,
            'message': '获取知识库详情成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取知识库详情失败')

@kb_bp.route('/<int:kb_id>/update', methods=['PUT'])
@require_api_key
def update_knowledge_base(kb_id):
    """更新知识库信息"""
    try:
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        name = data.get('name', '').strip() if 'name' in data else None
        description = data.get('description', '').strip() if 'description' in data else None
        
        # 如果更新名称，检查是否重复
        if name and name != kb['name']:
            existing_kbs = db_manager.get_knowledge_bases()
            for existing_kb in existing_kbs:
                if existing_kb['name'] == name and existing_kb['id'] != kb_id:
                    return jsonify({
                        'success': False,
                        'message': '知识库名称已存在'
                    }), 400
        
        # 更新知识库
        success = db_manager.update_knowledge_base(kb_id, name, description)
        
        if not success:
            return jsonify({
                'success': False,
                'message': '没有需要更新的内容'
            }), 400
        
        # 获取更新后的知识库信息
        updated_kb = db_manager.get_knowledge_base(kb_id)
        
        return jsonify({
            'success': True,
            'data': updated_kb,
            'message': '知识库更新成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='更新知识库失败')

@kb_bp.route('/<int:kb_id>/delete', methods=['DELETE'])
@require_api_key
def delete_knowledge_base(kb_id):
    """删除知识库"""
    try:
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        # 删除向量存储
        vector_manager.delete_store(kb_id)
        
        # 删除数据库记录（包括相关文档）
        success = db_manager.delete_knowledge_base(kb_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '知识库删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '知识库删除失败'
            }), 500
    
    except Exception as e:
        return make_error_response(e, public_message='删除知识库失败')

@kb_bp.route('/<int:kb_id>/stats', methods=['GET'])
def get_knowledge_base_stats(kb_id):
    """获取知识库统计信息"""
    try:
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        # 获取文档统计
        documents = db_manager.get_documents(kb_id)
        total_chunks = sum(doc.get('chunk_count', 0) for doc in documents)
        
        # 获取向量统计
        vector_store = vector_manager.get_store(kb_id)
        vector_stats = vector_store.get_stats()
        
        stats = {
            'kb_info': {
                'id': kb['id'],
                'name': kb['name'],
                'description': kb['description'],
                'created_at': kb['created_at']
            },
            'document_count': len(documents),
            'total_chunks': total_chunks,
            'vector_stats': vector_stats
        }
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': '获取统计信息成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取统计信息失败')

@kb_bp.route('/<int:kb_id>/force-stop', methods=['POST'])
@require_api_key
def force_stop_kb_processing(kb_id):
    """强制停止知识库处理"""
    try:
        # 获取知识库
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        # 清空该知识库的处理队列
        document_queue.clear_kb_queue(kb_id)
        
        # 重置知识库状态
        db_manager.update_knowledge_base_status(kb_id, 'ready')
        
        return jsonify({
            'success': True,
            'message': f'已停止知识库"{kb["name"]}"的处理，状态已重置为就绪'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='停止处理失败')
