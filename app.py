"""主Flask应用"""
import os
import time
import json
from datetime import datetime
from flask import Flask, render_template, send_from_directory, request, g
from flask_cors import CORS
from config import Config

# 导入路由蓝图
from app.routes.knowledge_base import kb_bp
from app.routes.documents import doc_bp
from app.routes.rag import rag_bp
from app.routes.rag_v2 import rag_v2_bp  # V2增量式上下文迭代架构
from app.routes.file_upload import file_upload_bp  # 文件上传功能

# 导入 IO 日志系统
from app.services.io_logger import enable_io_logging, disable_io_logging, get_logger

def create_app(enable_io_log=None):
    """
    创建Flask应用
    
    Args:
        enable_io_log: 是否启用IO日志，None表示从环境变量读取
    """
    app = Flask(__name__, 
                template_folder='app/templates',
                static_folder='app/static')
    
    # 加载配置
    app.config.from_object(Config)
    
    # 启用CORS（跨域资源共享）
    CORS(app)
    
    # ==================== IO 日志配置 ====================
    # 从环境变量或参数决定是否启用 IO 日志
    if enable_io_log is None:
        enable_io_log = os.getenv('ENABLE_IO_LOGGING', 'true').lower() == 'true'
    
    app.config['IO_LOGGING_ENABLED'] = enable_io_log
    
    if enable_io_log:
        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/api_io_{timestamp}.jsonl"
        enable_io_logging(log_file)
        app.config['IO_LOG_FILE'] = log_file
        print(f"✅ IO 日志已启用: {log_file}")
    
    # ==================== API 请求日志中间件 ====================
    
    @app.before_request
    def log_api_request():
        """记录 API 请求开始"""
        # 只记录 API 路径
        if request.path.startswith('/api/'):
            g.request_start_time = time.time()
            g.request_data = {
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.args),
                'headers': dict(request.headers),
                'remote_addr': request.remote_addr
            }
            
            # 记录请求体（如果有）
            if request.is_json:
                try:
                    g.request_data['body'] = request.get_json()
                except:
                    g.request_data['body'] = None
            elif request.data:
                g.request_data['body'] = request.data.decode('utf-8', errors='ignore')[:1000]
    
    @app.after_request
    def log_api_response(response):
        """记录 API 响应"""
        # 只记录 API 路径
        if request.path.startswith('/api/') and hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time
            
            # 构造日志条目
            log_entry = {
                'type': 'api_request',
                'timestamp': datetime.now().isoformat(),
                'duration': round(duration, 3),
                'request': g.request_data,
                'response': {
                    'status_code': response.status_code,
                    'content_type': response.content_type,
                    'content_length': response.content_length
                }
            }
            
            # 记录响应体（仅对 JSON 响应，且不是流式）
            if response.is_json and response.status_code < 400:
                try:
                    # 对于小响应，记录完整内容
                    if response.content_length and response.content_length < 10000:
                        log_entry['response']['body'] = response.get_json()
                    else:
                        log_entry['response']['body_size'] = response.content_length
                except:
                    pass
            
            # 写入 API 请求日志
            if app.config.get('IO_LOGGING_ENABLED'):
                logger = get_logger()
                logger.log_event(log_entry)
        
        return response
    
    # 注册蓝图
    app.register_blueprint(kb_bp)
    app.register_blueprint(doc_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(rag_v2_bp, url_prefix='/api')  # V2 API（独立路径）
    app.register_blueprint(file_upload_bp, url_prefix='/api')  # 文件上传
    
    # 主页路由
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')
    
    # API健康检查
    @app.route('/api/health')
    def health_check():
        """健康检查接口"""
        return {
            'status': 'ok',
            'message': 'RAG知识库系统运行正常',
            'config': {
                'embed_model': Config.EMBED_MODEL,
                'chat_model': Config.CHAT_MODEL,
                'embed_dimensions': Config.EMBED_DIMENSIONS,
                'max_file_size': f"{Config.MAX_FILE_SIZE / 1024 / 1024}MB",
                'allowed_extensions': list(Config.ALLOWED_EXTENSIONS)
            }
        }
    
    # 静态文件服务
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico')
    
    # IO 日志查询接口
    @app.route('/api/io-logs')
    def get_io_logs():
        """获取 IO 日志信息"""
        if not app.config.get('IO_LOGGING_ENABLED'):
            return {'enabled': False, 'message': 'IO 日志未启用'}
        
        logger = get_logger()
        return {
            'enabled': True,
            'log_file': app.config.get('IO_LOG_FILE'),
            'statistics': logger.get_statistics() if logger.enabled else {}
        }
    
    return app


if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 创建应用实例（启用 IO 日志）
    enable_logging = os.getenv('ENABLE_IO_LOGGING', 'true').lower() == 'true'
    app = create_app(enable_io_log=enable_logging)
    
    # 启动文档处理队列
    from app.services.document_queue import document_queue
    document_queue.start_processing()
    
    # 运行应用
    print("="*80)
    print("启动 RAG 知识库问答系统")
    print("="*80)
    print("📋 文档处理队列: 已启动")
    print("🌐 访问地址: http://localhost:5004")
    print("📚 API健康检查: http://localhost:5004/api/health")
    print("🆕 新功能: 批量文档上传 + Agentic RAG")
    print("🚀 V2架构: 增量式上下文迭代 - /api/v2/chat")
    print("📊 V2架构信息: /api/v2/info")
    
    if app.config.get('IO_LOGGING_ENABLED'):
        print(f"📝 IO日志: {app.config.get('IO_LOG_FILE')}")
        print(f"📊 日志状态: http://localhost:5004/api/io-logs")
        print("\n💡 提示:")
        print("   - 所有 /api/* 请求将被记录")
        print("   - 所有 LLM 调用将记录完整载荷")
        print("   - 查看日志: cat logs/api_io_*.jsonl | jq .")
        print("   - 分析日志: python analyze_io_log.py logs/api_io_*.jsonl")
        print("   - 禁用日志: export ENABLE_IO_LOGGING=false")
    else:
        print("📝 IO日志: 已禁用")
        print("   - 启用: export ENABLE_IO_LOGGING=true")
    
    print("="*80)
    
    try:
        app.run(
            host='0.0.0.0',
            port=5004,
            debug=Config.DEBUG,
            threaded=True
        )
    finally:
        # 确保应用关闭时停止处理队列
        document_queue.stop_processing()
        
        # 禁用 IO 日志
        if app.config.get('IO_LOGGING_ENABLED'):
            disable_io_logging()
            logger = get_logger()
            print("\n" + logger.get_summary())
