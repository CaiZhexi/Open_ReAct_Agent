"""文档管理API"""
import os
import tempfile
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from config import Config
from app.models.database import DatabaseManager
from app.models.vector_store import vector_manager
from app.services.document_processor import document_processor
from app.services.api_clients import embedding_client
from app.services.document_queue import document_queue
from app.utils.security import require_api_key, safe_basename, ensure_within, make_error_response

# 创建蓝图
doc_bp = Blueprint('documents', __name__, url_prefix='/api/docs')

# 初始化数据库管理器
db_manager = DatabaseManager()

@doc_bp.route('/list/<int:kb_id>', methods=['GET'])
def list_documents(kb_id):
    """获取知识库的文档列表"""
    try:
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        documents = db_manager.get_documents(kb_id)
        
        return jsonify({
            'success': True,
            'data': documents,
            'message': '获取文档列表成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取文档列表失败')

@doc_bp.route('/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """获取文档详情"""
    try:
        document = db_manager.get_document(doc_id)
        
        if not document:
            return jsonify({
                'success': False,
                'message': '文档不存在'
            }), 404
        
        # 获取文档块
        chunks = db_manager.get_document_chunks(doc_id)
        document['chunks'] = chunks
        
        return jsonify({
            'success': True,
            'data': document,
            'message': '获取文档详情成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取文档详情失败')

@doc_bp.route('/batch-upload/<int:kb_id>', methods=['POST'])
@require_api_key
def batch_upload_documents(kb_id):
    """批量上传文档到知识库"""
    try:
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        # 检查文件
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({
                'success': False,
                'message': '请选择文件'
            }), 400
        
        # 创建临时目录存储文件
        temp_dir = os.path.join(tempfile.gettempdir(), f'batch_upload_{uuid.uuid4()}')
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            processed_files = []
            validation_errors = []
            
            # 处理每个文件
            for file in files:
                if file.filename == '':
                    validation_errors.append("发现空文件名的文件")
                    continue
                
                # 安全文件名处理（保留中文字符；强制 basename + 拒绝 ..）
                def safe_filename(filename):
                    import re
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    safe_name = ' '.join(safe_name.split())
                    return safe_basename(safe_name.strip())

                original_filename = safe_filename(file.filename)
                if not original_filename:
                    validation_errors.append(f"{file.filename}: 文件名无效")
                    continue

                file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

                # 检查文件类型
                if not file_extension:
                    validation_errors.append(f"文件 '{file.filename}' -> '{original_filename}': 缺少文件扩展名")
                    continue
                elif file_extension not in Config.ALLOWED_EXTENSIONS:
                    validation_errors.append(f"{original_filename}: 不支持的文件类型 '{file_extension}'，支持的类型：{', '.join(Config.ALLOWED_EXTENSIONS)}")
                    continue

                # 保存临时文件，并确保结果路径仍在 temp_dir 内
                temp_file_path = os.path.join(temp_dir, original_filename)
                if not ensure_within(temp_dir, temp_file_path):
                    validation_errors.append(f"{original_filename}: 非法路径")
                    continue
                file.save(temp_file_path)
                
                # 验证文件
                validation_result = document_processor.validate_file(temp_file_path, file_extension)
                if not validation_result['valid']:
                    validation_errors.append(f"{original_filename}: {validation_result['error']}")
                    os.unlink(temp_file_path)
                    continue
                
                # 检查文档名称是否已存在
                existing_docs = db_manager.get_documents(kb_id)
                if any(doc['name'] == original_filename for doc in existing_docs):
                    validation_errors.append(f"{original_filename}: 文档名称已存在")
                    os.unlink(temp_file_path)
                    continue
                
                # 添加到处理列表
                processed_files.append({
                    'file_name': original_filename,
                    'file_path': temp_file_path,
                    'file_type': file_extension,
                    'file_size': validation_result['file_size']
                })
            
            if not processed_files:
                return jsonify({
                    'success': False,
                    'message': '没有有效的文件可以处理',
                    'errors': validation_errors
                }), 400
            
            # 添加到处理队列
            success = document_queue.add_documents_to_queue(kb_id, processed_files)
            
            if success:
                response_data = {
                    'success': True,
                    'message': f'已提交 {len(processed_files)} 个文档到处理队列',
                    'queued_files': len(processed_files),
                    'total_files': len(files),
                    'skipped_files': len(files) - len(processed_files)
                }
                
                if validation_errors:
                    response_data['warnings'] = validation_errors
                
                return jsonify(response_data)
            else:
                # 清理临时文件
                for file_info in processed_files:
                    try:
                        os.unlink(file_info['file_path'])
                    except:
                        pass
                
                return jsonify({
                    'success': False,
                    'message': '添加到处理队列失败'
                }), 500
        
        except Exception as e:
            # 清理临时目录
            import shutil
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            raise e
    
    except Exception as e:
        return make_error_response(e, public_message='批量上传失败')

@doc_bp.route('/upload/<int:kb_id>', methods=['POST'])
@require_api_key
def upload_document(kb_id):
    """上传文档到知识库"""
    try:
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '文件名不能为空'
            }), 400
        
        # 获取文件信息
        original_filename = safe_basename(secure_filename(file.filename))
        if not original_filename:
            return jsonify({'success': False, 'message': '无效的文件名'}), 400
        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # 验证文件
            validation_result = document_processor.validate_file(temp_file_path, file_extension)
            if not validation_result['valid']:
                return jsonify({
                    'success': False,
                    'message': validation_result['error']
                }), 400
            
            # 提取文本内容
            content = document_processor.extract_text_from_file(temp_file_path, file_extension)
            if not content.strip():
                return jsonify({
                    'success': False,
                    'message': '文件内容为空'
                }), 400
            
            # 检查文档名称是否已存在
            existing_docs = db_manager.get_documents(kb_id)
            for doc in existing_docs:
                if doc['name'] == original_filename:
                    return jsonify({
                        'success': False,
                        'message': '文档名称已存在'
                    }), 400
            
            # 创建文档记录
            doc_id = db_manager.create_document(
                kb_id=kb_id,
                name=original_filename,
                content=content,
                file_type=file_extension,
                file_size=validation_result['file_size']
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
                        doc_names=[original_filename] * len(chunks)
                    )
                    
                    # 存储文档块
                    db_manager.create_document_chunks(doc_id, chunks)
                else:
                    print(f"嵌入向量数量({len(embeddings)})与文档块数量({len(chunks)})不匹配")
            
            # 获取创建的文档信息
            document = db_manager.get_document(doc_id)
            
            return jsonify({
                'success': True,
                'data': document,
                'message': '文档上传成功'
            })
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except Exception as e:
        return make_error_response(e, public_message='文档上传失败')

@doc_bp.route('/create/<int:kb_id>', methods=['POST'])
@require_api_key
def create_text_document(kb_id):
    """创建文本文档"""
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
        
        name = data.get('name', '').strip()
        content = data.get('content', '').strip()
        
        if not name:
            return jsonify({
                'success': False,
                'message': '文档名称不能为空'
            }), 400
        
        if not content:
            return jsonify({
                'success': False,
                'message': '文档内容不能为空'
            }), 400
        
        # 检查文档名称是否已存在
        existing_docs = db_manager.get_documents(kb_id)
        for doc in existing_docs:
            if doc['name'] == name:
                return jsonify({
                    'success': False,
                    'message': '文档名称已存在'
                }), 400
        
        # 创建文档记录
        doc_id = db_manager.create_document(
            kb_id=kb_id,
            name=name,
            content=content,
            file_type='txt',
            file_size=len(content.encode('utf-8'))
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
                    doc_names=[name] * len(chunks)
                )
                
                # 存储文档块
                db_manager.create_document_chunks(doc_id, chunks)
        
        # 获取创建的文档信息
        document = db_manager.get_document(doc_id)
        
        return jsonify({
            'success': True,
            'data': document,
            'message': '文档创建成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='文档创建失败')

@doc_bp.route('/<int:doc_id>/update', methods=['PUT'])
@require_api_key
def update_document(doc_id):
    """更新文档"""
    try:
        # 检查文档是否存在
        document = db_manager.get_document(doc_id)
        if not document:
            return jsonify({
                'success': False,
                'message': '文档不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        name = data.get('name', '').strip() if 'name' in data else None
        content = data.get('content', '').strip() if 'content' in data else None
        
        # 如果更新名称，检查是否重复
        if name and name != document['name']:
            existing_docs = db_manager.get_documents(document['kb_id'])
            for doc in existing_docs:
                if doc['name'] == name and doc['id'] != doc_id:
                    return jsonify({
                        'success': False,
                        'message': '文档名称已存在'
                    }), 400
        
        # 如果更新内容，需要重新处理向量
        if content and content != document['content']:
            # 删除原有向量
            vector_store = vector_manager.get_store(document['kb_id'])
            vector_store.delete_document_vectors(document['name'])
            
            # 分割新内容为块
            chunks = document_processor.split_text_into_chunks(content)
            
            if chunks:
                # 获取嵌入向量
                chunk_contents = [chunk['content'] for chunk in chunks]
                embeddings = embedding_client.get_embeddings(chunk_contents)
                
                if len(embeddings) == len(chunks):
                    # 存储新向量
                    new_doc_name = name if name else document['name']
                    vector_store.add_vectors(
                        vectors=embeddings,
                        chunk_ids=[chunk['vector_id'] for chunk in chunks],
                        contents=chunk_contents,
                        doc_names=[new_doc_name] * len(chunks)
                    )
                    
                    # 更新文档块
                    db_manager.create_document_chunks(doc_id, chunks)
        
        # 更新数据库记录
        success = db_manager.update_document(doc_id, name, content)
        
        if not success:
            return jsonify({
                'success': False,
                'message': '没有需要更新的内容'
            }), 400
        
        # 获取更新后的文档信息
        updated_document = db_manager.get_document(doc_id)
        
        return jsonify({
            'success': True,
            'data': updated_document,
            'message': '文档更新成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='文档更新失败')

@doc_bp.route('/<int:doc_id>/delete', methods=['DELETE'])
@require_api_key
def delete_document(doc_id):
    """删除文档"""
    try:
        # 检查文档是否存在
        document = db_manager.get_document(doc_id)
        if not document:
            return jsonify({
                'success': False,
                'message': '文档不存在'
            }), 404
        
        # 删除向量
        vector_store = vector_manager.get_store(document['kb_id'])
        vector_store.delete_document_vectors(document['name'])
        
        # 删除数据库记录
        success = db_manager.delete_document(doc_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '文档删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '文档删除失败'
            }), 500
    
    except Exception as e:
        return make_error_response(e, public_message='文档删除失败')

@doc_bp.route('/<int:doc_id>/chunks', methods=['GET'])
def get_document_chunks(doc_id):
    """获取文档块列表"""
    try:
        # 检查文档是否存在
        document = db_manager.get_document(doc_id)
        if not document:
            return jsonify({
                'success': False,
                'message': '文档不存在'
            }), 404
        
        chunks = db_manager.get_document_chunks(doc_id)
        
        return jsonify({
            'success': True,
            'data': {
                'document': {
                    'id': document['id'],
                    'name': document['name'],
                    'kb_id': document['kb_id']
                },
                'chunks': chunks,
                'total_chunks': len(chunks)
            },
            'message': '获取文档块成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取文档块失败')

@doc_bp.route('/processing-status/<int:kb_id>', methods=['GET'])
def get_processing_status(kb_id):
    """获取知识库的文档处理状态"""
    try:
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base(kb_id)
        if not kb:
            return jsonify({
                'success': False,
                'message': '知识库不存在'
            }), 404
        
        # 获取处理状态
        status_info = document_queue.get_queue_status(kb_id)
        
        return jsonify({
            'success': True,
            'data': {
                'kb_id': kb_id,
                'kb_name': kb['name'],
                'status': status_info['kb_status']['status'] if status_info['kb_status'] else 'ready',
                'progress': status_info['kb_status']['processing_progress'] if status_info['kb_status'] else 1.0,
                'total_pending_docs': status_info['kb_status']['total_pending_docs'] if status_info['kb_status'] else 0,
                'processed_docs': status_info['kb_status']['processed_docs'] if status_info['kb_status'] else 0,
                'queue_stats': status_info['queue_stats'],
                'processing_active': status_info['processing_active']
            },
            'message': '获取处理状态成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取处理状态失败')
