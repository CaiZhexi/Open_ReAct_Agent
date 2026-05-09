"""RAG问答系统API"""
from flask import Blueprint, request, jsonify, Response, stream_template
import json
from typing import List, Dict, Any
from app.models.database import DatabaseManager
from app.models.vector_store import vector_manager
from app.services.api_clients import embedding_client, chat_client, rerank_client
from app.services.tools import tool_registry
from app.utils.security import (
    require_api_key,
    make_error_response,
    quote_untrusted,
    UNTRUSTED_INSTRUCTION,
)

# 创建蓝图
rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')

# 初始化数据库管理器
db_manager = DatabaseManager()

@rag_bp.route('/agentic-chat', methods=['POST'])
@require_api_key
def agentic_chat():
    """Agentic RAG问答接口（Lite模式）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        question = data.get('question', '').strip()
        kb_ids = data.get('kb_ids', [])
        use_lite = data.get('use_lite', False)  # 是否使用 Lite 模式
        stream = data.get('stream', False)  # 是否流式响应
        
        if not question:
            return jsonify({
                'success': False,
                'message': '问题不能为空'
            }), 400
        
        # 允许空的kb_ids列表，Agent会智能决策是否需要知识库
        # Python工具、网络搜索、简单对话等场景不需要知识库
        
        # 验证知识库是否存在且为就绪状态
        valid_kb_ids = []
        processing_kbs = []
        for kb_id in kb_ids:
            kb = db_manager.get_knowledge_base(kb_id)
            if not kb:
                continue
            
            # 检查知识库状态
            status = kb.get('status', 'ready')
            if status == 'ready':
                valid_kb_ids.append(kb_id)
            elif status == 'processing':
                processing_kbs.append(kb['name'])
        
        # 如果用户选择了知识库但都不可用，才报错
        if kb_ids and not valid_kb_ids:
            message = '选择的知识库不存在'
            if processing_kbs:
                message = f'选择的知识库都在处理中，请等待处理完成。处理中的知识库：{", ".join(processing_kbs)}'
            return jsonify({
                'success': False,
                'message': message
            }), 404
        
        # 仅支持Lite模式
        if not use_lite:
            return jsonify({
                'success': False,
                'message': '此端点仅支持Lite模式，请使用 /api/v2/chat 端点访问完整版V2'
            }), 400
        
        # 根据是否流式响应选择不同的处理方式
        if stream:
            # Lite 模式流式响应
            user_id = request.headers.get('X-API-Key') or request.remote_addr or 'anonymous'
            return Response(
                _generate_lite_streaming_response(question, valid_kb_ids, user_id=user_id),
                mimetype='text/event-stream'
            )
        else:
            # Lite模式非流式暂不支持
            return jsonify({
                'success': False,
                'message': 'Lite模式仅支持流式响应，请设置 stream=true'
            }), 400
    
    except Exception as e:
        return make_error_response(e, public_message='Agentic RAG问答失败')

@rag_bp.route('/chat', methods=['POST'])
@require_api_key
def chat():
    """RAG问答接口"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        question = data.get('question', '').strip()
        kb_ids = data.get('kb_ids', [])  # 支持多个知识库
        stream = data.get('stream', False)  # 是否流式响应
        top_k = data.get('top_k', 5)  # 检索结果数量
        
        if not question:
            return jsonify({
                'success': False,
                'message': '问题不能为空'
            }), 400
        
        if not kb_ids:
            return jsonify({
                'success': False,
                'message': '请选择知识库'
            }), 400
        
        # 验证知识库是否存在且为就绪状态
        valid_kb_ids = []
        processing_kbs = []
        for kb_id in kb_ids:
            kb = db_manager.get_knowledge_base(kb_id)
            if not kb:
                continue
            
            # 检查知识库状态
            status = kb.get('status', 'ready')
            if status == 'ready':
                valid_kb_ids.append(kb_id)
            elif status == 'processing':
                processing_kbs.append(kb['name'])
        
        if not valid_kb_ids:
            message = '选择的知识库不存在'
            if processing_kbs:
                message = f'选择的知识库都在处理中，请等待处理完成。处理中的知识库：{", ".join(processing_kbs)}'
            return jsonify({
                'success': False,
                'message': message
            }), 404
        
        # 获取问题的嵌入向量
        question_embedding = embedding_client.get_embedding(question)
        if not question_embedding:
            return jsonify({
                'success': False,
                'message': '获取问题向量失败'
            }), 500
        
        # 在多个知识库中检索相关内容
        all_search_results = []
        kb_names = {}
        
        for kb_id in valid_kb_ids:
            kb = db_manager.get_knowledge_base(kb_id)
            kb_names[kb_id] = kb['name']
            
            vector_store = vector_manager.get_store(kb_id)
            search_results = vector_store.search(question_embedding, top_k)
            
            # 添加知识库信息到结果中
            for result in search_results:
                result['kb_id'] = kb_id
                result['kb_name'] = kb['name']
                all_search_results.append(result)
        
        # 按相似度排序并取前top_k个结果
        all_search_results.sort(key=lambda x: x['score'], reverse=True)
        top_results = all_search_results[:top_k]
        
        if not top_results:
            return jsonify({
                'success': True,
                'data': {
                    'answer': '抱歉，我在知识库中没有找到相关信息来回答您的问题。',
                    'sources': [],
                    'question': question
                },
                'message': '未找到相关内容'
            })
        
        # 构建上下文（包裹进 <untrusted_source> 标签以对抗 prompt injection）
        context_parts = []
        sources = []

        for i, result in enumerate(top_results, 1):
            wrapped = quote_untrusted(result['content'], tag='untrusted_source', max_len=4000)
            context_parts.append(f"参考资料{i}：\n{wrapped}")
            sources.append({
                'chunk_id': result['chunk_id'],
                'content': result['content'][:200] + '...' if len(result['content']) > 200 else result['content'],
                'doc_name': result['doc_name'],
                'kb_name': result['kb_name'],
                'kb_id': result['kb_id'],
                'score': result['score']
            })
        
        context = "\n\n".join(context_parts)
        
        # 构建提示词
        # 获取当前北京时间
        import datetime
        import pytz
        beijing_tz = pytz.timezone('Asia/Shanghai')
        current_time = datetime.datetime.now(beijing_tz).strftime('%Y年%m月%d日 %H:%M:%S')

        prompt = f"""基于以下参考资料回答用户问题。请确保：
1. 回答准确且基于参考资料
2. 如果参考资料中没有相关信息，请明确说明
3. 回答要简洁明了
4. 在回答末尾标明主要参考了哪些资料

{UNTRUSTED_INSTRUCTION}

⏰ 【当前系统时间】
北京时间：{current_time}
⚠️ 重要：回答时请使用这个实际的当前时间，不要使用训练数据中的旧时间。

参考资料：
{context}

用户问题：{question}

请回答："""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # 根据是否流式响应选择不同的处理方式
        if stream:
            return Response(
                _generate_streaming_response(messages, sources, question),
                mimetype='text/event-stream'
            )
        else:
            # 获取LLM回答
            answer = chat_client.chat(messages, stream=False)
            
            return jsonify({
                'success': True,
                'data': {
                    'answer': answer,
                    'sources': sources,
                    'question': question
                },
                'message': '回答成功'
            })
    
    except Exception as e:
        return make_error_response(e, public_message='问答失败')

def _generate_streaming_response(messages: List[Dict[str, str]], sources: List[Dict], question: str):
    """生成流式响应"""
    try:
        # 先发送基本信息
        yield f"data: {json.dumps({'type': 'start', 'sources': sources, 'question': question}, ensure_ascii=False)}\n\n"
        
        # 流式生成回答
        answer_parts = []
        for chunk in chat_client.chat_stream_generator(messages):
            if chunk:
                answer_parts.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
        
        # 发送完成信号
        final_answer = ''.join(answer_parts)
        yield f"data: {json.dumps({'type': 'done', 'answer': final_answer}, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

def _generate_lite_streaming_response(question: str, kb_ids: List[int], user_id: str = None):
    """生成 Lite 模式流式响应

    Lite 模式工作流：Plan → Execute → Answer（流式）
    """
    try:
        from app.models.database import DatabaseManager
        from app.services.lite_dispatcher import lite_dispatcher
        from app.services.io_logger import get_logger as get_io_logger
        
        # 获取知识库名称
        db_manager = DatabaseManager()
        kb_names = {}
        for kb_id in kb_ids:
            kb = db_manager.get_knowledge_base(kb_id)
            if kb:
                kb_names[kb_id] = kb.get('name', f'知识库{kb_id}')
        
        # 创建IO日志记录（兼容V2的格式）
        io_logger = get_io_logger()
        request_id = None
        if io_logger and io_logger.enabled:
            request_id = io_logger.start_request(question, metadata={
                'kb_ids': kb_ids,
                'kb_names': kb_names,
                'mode': 'lite',
                'stream': True
            })
        
        # 发送开始信号
        yield f"data: {json.dumps({'type': 'start', 'question': question}, ensure_ascii=False)}\n\n"
        
        # 调用 Lite 调度器的流式方法（传递request_id）
        final_result = None
        for event in lite_dispatcher.dispatch_stream(question, kb_ids, kb_names, request_id, user_id=user_id):
            event_type = event.get('event')
            event_data = event.get('data', {})
            
            # 转换为前端期望的格式
            if event_type == 'start':
                # 已经发送过 start 了，跳过
                continue
            
            elif event_type == 'thinking':
                yield f"data: {json.dumps({'type': 'thinking', 'message': event_data.get('message', '思考中...')}, ensure_ascii=False)}\n\n"
            
            elif event_type == 'plan_complete':
                yield f"data: {json.dumps({'type': 'plan', 'message': event_data.get('message', '规划完成')}, ensure_ascii=False)}\n\n"
            
            elif event_type == 'tool_start':
                tool_start_data = {
                    'type': 'tool_start',
                    'step': event_data.get('step'),
                    'tool': event_data.get('tool'),
                    'tool_name': _get_tool_display_name_lite(event_data.get('tool')),
                    'reasoning': event_data.get('reasoning', ''),
                    'args': event_data.get('args', {})
                }
                yield f"data: {json.dumps(tool_start_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'execute_start':
                yield f"data: {json.dumps({'type': 'thinking', 'message': event_data.get('message', '执行工具...')}, ensure_ascii=False)}\n\n"
            
            elif event_type == 'tool_end':
                tool_end_data = {
                    'type': 'tool_end',
                    'step': event_data.get('step'),
                    'tool': event_data.get('tool'),
                    'execution_time': event_data.get('execution_time', 0),
                    'result_summary': _get_result_summary_from_result(event_data.get('tool'), event_data.get('result')),
                }
                
                # 添加具体结果数据
                result_data = event_data.get('result', {})
                if isinstance(result_data, dict):
                    # Python 执行结果
                    if 'output' in result_data:
                        tool_end_data['python_details'] = {
                            'output': result_data.get('output', ''),
                            'code': result_data.get('code', ''),
                            'execution_time': event_data.get('execution_time', 0)
                        }
                    # 检索结果
                    elif 'chunks' in result_data:
                        tool_end_data['search_results'] = result_data.get('chunks', [])
                    # 网络搜索结果
                    elif 'results' in result_data:
                        tool_end_data['web_search_results'] = result_data.get('results', [])
                
                if event_data.get('retry_count', 0) > 0:
                    tool_end_data['retry_count'] = event_data.get('retry_count')
                
                yield f"data: {json.dumps(tool_end_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'tool_error':
                tool_error_data = {
                    'type': 'tool_error',
                    'step': event_data.get('step'),
                    'tool': event_data.get('tool'),
                    'error': event_data.get('error', '执行失败')
                }
                yield f"data: {json.dumps(tool_error_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'answer_start':
                yield f"data: {json.dumps({'type': 'answer_start', 'message': event_data.get('message', '生成答案...')}, ensure_ascii=False)}\n\n"
            
            elif event_type == 'answer_chunk':
                # 流式答案片段
                chunk_data = {
                    'type': 'answer_chunk',
                    'chunk': event_data.get('chunk', '')
                }
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'finish':
                # 完成
                done_data = {
                    'type': 'done',
                    'answer': event_data.get('final_answer', ''),
                    'sources': event_data.get('sources', []),
                    'confidence': event_data.get('confidence', 0),
                    'confidence_reason': event_data.get('confidence_reason', ''),
                    'used_retrieval': event_data.get('used_retrieval', False),
                    'process_log': event_data.get('process_log', {}),
                    'request_id': request_id  # 添加request_id
                }
                final_result = done_data
                yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'error':
                error_data = {'type': 'error', 'message': event_data.get('message', '执行失败')}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        # 结束IO日志记录
        if io_logger and io_logger.enabled and request_id and final_result:
            io_logger.end_request(request_id, final_result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_data = {'type': 'error', 'message': str(e)}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

def _get_tool_display_name_lite(tool: str) -> str:
    """获取工具的显示名称（Lite 模式）"""
    names = {
        'vector_search': '知识库检索',
        'web_search': '网络搜索',
        'python_executor': 'Python 执行'
    }
    return names.get(tool, tool)

def _get_result_summary_from_result(tool: str, result_data: Any) -> str:
    """从工具结果生成摘要"""
    if tool == 'python_executor':
        if isinstance(result_data, dict) and 'output' in result_data:
            output = result_data.get('output', '')
            if output:
                return f"执行成功，输出：{output[:50]}..." if len(output) > 50 else f"执行成功，输出：{output}"
            return "执行成功"
        return "代码已执行"
    
    elif tool == 'web_search':
        if isinstance(result_data, dict):
            results = result_data.get('results', [])
            return f"找到 {len(results)} 个搜索结果"
        return "搜索完成"
    
    elif tool == 'vector_search':
        if isinstance(result_data, dict):
            chunks = result_data.get('chunks', [])
            return f"检索到 {len(chunks)} 个相关文档"
        return "检索完成"
    
    return "执行完成"

@rag_bp.route('/search', methods=['POST'])
def search_knowledge():
    """知识检索接口"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        query = data.get('query', '').strip()
        kb_ids = data.get('kb_ids', [])
        top_k = data.get('top_k', 10)
        
        if not query:
            return jsonify({
                'success': False,
                'message': '搜索内容不能为空'
            }), 400
        
        if not kb_ids:
            return jsonify({
                'success': False,
                'message': '请选择知识库'
            }), 400
        
        # 获取查询向量
        query_embedding = embedding_client.get_embedding(query)
        if not query_embedding:
            return jsonify({
                'success': False,
                'message': '获取查询向量失败'
            }), 500
        
        # 在多个知识库中搜索
        all_results = []
        for kb_id in kb_ids:
            kb = db_manager.get_knowledge_base(kb_id)
            if not kb:
                continue
            
            vector_store = vector_manager.get_store(kb_id)
            results = vector_store.search(query_embedding, top_k)
            
            for result in results:
                result['kb_id'] = kb_id
                result['kb_name'] = kb['name']
                all_results.append(result)
        
        # 按相似度排序
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'query': query,
                'results': all_results[:top_k],
                'total': len(all_results)
            },
            'message': '搜索成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='搜索失败')

@rag_bp.route('/rerank', methods=['POST'])
def rerank_documents():
    """文档重排接口"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        query = data.get('query', '').strip()
        documents = data.get('documents', [])
        top_n = data.get('top_n', 10)
        instruction = data.get('instruction', '')
        
        if not query:
            return jsonify({
                'success': False,
                'message': '查询内容不能为空'
            }), 400
        
        if not documents:
            return jsonify({
                'success': False,
                'message': '文档列表不能为空'
            }), 400
        
        # 执行重排
        rerank_results = rerank_client.rerank(
            query=query,
            documents=documents,
            top_n=top_n,
            instruction=instruction if instruction else None
        )
        
        return jsonify({
            'success': True,
            'data': {
                'query': query,
                'results': rerank_results,
                'total': len(rerank_results)
            },
            'message': '重排成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='重排失败')

@rag_bp.route('/tools', methods=['GET'])
def list_tools():
    """列出所有已注册的工具"""
    try:
        category = request.args.get('category')
        enabled_only = request.args.get('enabled_only', 'true').lower() == 'true'
        
        # 转换类别参数
        from app.services.tools import ToolCategory
        tool_category = None
        if category:
            try:
                tool_category = ToolCategory(category)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f'无效的工具类别: {category}'
                }), 400
        
        # 获取工具列表
        tools = tool_registry.list_tools(category=tool_category, enabled_only=enabled_only)
        
        return jsonify({
            'success': True,
            'data': {
                'tools': tools,
                'total': len(tools)
            },
            'message': '获取工具列表成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取工具列表失败')

@rag_bp.route('/tools/stats', methods=['GET'])
def get_tool_stats():
    """获取工具执行统计信息"""
    try:
        tool_name = request.args.get('tool_name')
        
        # 获取统计信息
        stats = tool_registry.get_stats(tool_name)
        
        if tool_name and not stats:
            return jsonify({
                'success': False,
                'message': f'工具不存在: {tool_name}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats
            },
            'message': '获取统计信息成功'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='获取统计信息失败')

@rag_bp.route('/tools/<tool_name>/enable', methods=['POST'])
def enable_tool(tool_name):
    """启用工具"""
    try:
        success = tool_registry.enable_tool(tool_name)
        
        if not success:
            return jsonify({
                'success': False,
                'message': f'工具不存在: {tool_name}'
            }), 404
        
        return jsonify({
            'success': True,
            'message': f'工具已启用: {tool_name}'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='启用工具失败')

@rag_bp.route('/tools/<tool_name>/disable', methods=['POST'])
def disable_tool(tool_name):
    """禁用工具"""
    try:
        success = tool_registry.disable_tool(tool_name)
        
        if not success:
            return jsonify({
                'success': False,
                'message': f'工具不存在: {tool_name}'
            }), 404
        
        return jsonify({
            'success': True,
            'message': f'工具已禁用: {tool_name}'
        })
    
    except Exception as e:
        return make_error_response(e, public_message='禁用工具失败')
