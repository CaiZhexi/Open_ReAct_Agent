"""
文件上传路由
支持 xlsx 和 csv 文件的上传和管理
"""
from flask import Blueprint, request, jsonify
import os
import logging
from werkzeug.utils import secure_filename
from datetime import datetime

file_upload_bp = Blueprint('file_upload', __name__)
logger = logging.getLogger(__name__)

# 配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_size_str(size_bytes):
    """将字节转换为可读的文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


@file_upload_bp.route('/upload_files', methods=['POST'])
def upload_files():
    """
    上传文件接口
    
    Request:
        files: 文件列表（支持多文件上传）
    
    Response:
        {
            "success": true/false,
            "files": [...],  # 上传成功的文件列表
            "message": "..."
        }
    """
    try:
        # 检查是否有文件
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有文件被上传'
            }), 400
        
        files = request.files.getlist('files')
        
        if not files or files[0].filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        uploaded_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                # 使用安全的文件名
                filename = secure_filename(file.filename)
                
                # 如果文件名重复，添加时间戳
                name, ext = os.path.splitext(filename)
                unique_filename = filename
                counter = 1
                
                while os.path.exists(os.path.join(UPLOAD_FOLDER, unique_filename)):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{name}_{timestamp}_{counter}{ext}"
                    counter += 1
                
                filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(filepath)
                
                # 获取文件信息
                file_size = os.path.getsize(filepath)
                
                uploaded_files.append({
                    'filename': unique_filename,
                    'original_name': file.filename,
                    'size': file_size,
                    'size_str': get_file_size_str(file_size),
                    'type': ext[1:] if ext else 'unknown',
                    'upload_time': datetime.now().isoformat()
                })
                
                logger.info(f"文件上传成功: {unique_filename}")
            else:
                return jsonify({
                    'success': False,
                    'error': f'文件 {file.filename} 格式不支持。仅支持: {", ".join(ALLOWED_EXTENSIONS)}'
                }), 400
        
        return jsonify({
            'success': True,
            'files': uploaded_files,
            'message': f'成功上传 {len(uploaded_files)} 个文件'
        })
    
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@file_upload_bp.route('/list_files', methods=['GET'])
def list_files():
    """
    获取已上传的文件列表
    
    Response:
        {
            "success": true,
            "files": [...]
        }
    """
    try:
        files = []
        
        for filename in os.listdir(UPLOAD_FOLDER):
            # 只列出 csv 和 xlsx 文件
            if not filename.startswith('.') and allowed_file(filename):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file_size = os.path.getsize(filepath)
                file_mtime = os.path.getmtime(filepath)
                
                files.append({
                    'filename': filename,
                    'size': file_size,
                    'size_str': get_file_size_str(file_size),
                    'type': filename.rsplit('.', 1)[1].lower(),
                    'modified_time': datetime.fromtimestamp(file_mtime).isoformat()
                })
        
        # 按修改时间排序（最新的在前）
        files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files
        })
    
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@file_upload_bp.route('/delete_file/<filename>', methods=['DELETE'])
def delete_file(filename):
    """
    删除指定文件
    
    Args:
        filename: 文件名
    
    Response:
        {
            "success": true/false,
            "message": "..."
        }
    """
    try:
        # 安全检查：防止路径遍历攻击
        filename = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 检查文件类型
        if not allowed_file(filename):
            return jsonify({
                'success': False,
                'error': '无权删除该文件类型'
            }), 403
        
        os.remove(filepath)
        logger.info(f"文件删除成功: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 已删除'
        })
    
    except Exception as e:
        logger.error(f"文件删除失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@file_upload_bp.route('/clear_files', methods=['POST'])
def clear_files():
    """
    清空所有上传的文件
    
    Response:
        {
            "success": true/false,
            "message": "..."
        }
    """
    try:
        deleted_count = 0
        
        for filename in os.listdir(UPLOAD_FOLDER):
            if not filename.startswith('.') and allowed_file(filename):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                os.remove(filepath)
                deleted_count += 1
        
        logger.info(f"清空文件成功，共删除 {deleted_count} 个文件")
        
        return jsonify({
            'success': True,
            'message': f'已清空 {deleted_count} 个文件'
        })
    
    except Exception as e:
        logger.error(f"清空文件失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_upload_folder():
    """获取上传文件夹路径（供其他模块使用）"""
    return UPLOAD_FOLDER
