"""
RAG V2 路由 - 增量式上下文迭代架构
独立于V1，采用全新的 Plan → Tool → Evaluate → Output → Finish 工作流
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context, send_file
import json
import time
import os
from datetime import datetime

from app.services.v2_agent import v2_agent
from app.models.database import DatabaseManager
from app.services.io_logger import get_logger

rag_v2_bp = Blueprint('rag_v2', __name__)

# 初始化数据库管理器
db_manager = DatabaseManager()


@rag_v2_bp.route('/v2/chat', methods=['POST'])
def v2_chat():
    """
    V2 Agentic RAG 接口 - 增量式上下文迭代
    
    Request Body:
    {
        "query": "用户问题",
        "stream": true/false,  # 可选，默认true
        "history": [  # 可选，对话历史
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    
    注意：不再需要传递kb_ids，系统会自动获取所有知识库并展示给Agent
    
    Response (stream=true):
        Server-Sent Events格式的流式响应
    
    Response (stream=false):
        JSON格式的完整响应
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        use_stream = data.get('stream', True)
        history = data.get('history', [])  # 获取对话历史
        selected_files = data.get('selected_files', [])  # 获取选中的文件列表
        
        if not query:
            return jsonify({
                'success': False,
                'error': '查询不能为空'
            }), 400
        
        # 获取所有知识库
        all_kbs = db_manager.get_knowledge_bases()
        kb_ids = [kb['id'] for kb in all_kbs]
        kb_names = {kb['id']: kb['name'] for kb in all_kbs}
        
        # 开始记录请求日志
        io_logger = get_logger()
        request_id = io_logger.start_request(query, metadata={
            'kb_ids': kb_ids,
            'kb_names': kb_names,
            'stream': use_stream,
            'history_length': len(history),
            'selected_files': selected_files
        })
        
        # 流式响应
        if use_stream:
            return Response(
                stream_with_context(_stream_v2_chat(query, kb_ids, kb_names, request_id, history, selected_files)),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Connection': 'keep-alive'
                }
            )
        # 非流式响应
        else:
            result = v2_agent.run(query, kb_ids, kb_names, history, selected_files)
            # 添加request_id到结果中
            result['request_id'] = request_id
            # 结束记录请求日志
            io_logger.end_request(request_id, result)
            return jsonify(result)
            
    except Exception as e:
        print(f"V2 Chat 错误: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _stream_v2_chat(query: str, kb_ids: list, kb_names: dict, request_id: str = None, history: list = None, selected_files: list = None):
    """流式生成V2响应"""
    io_logger = get_logger()
    
    try:
        step = 0
        iteration = 0  # 迭代轮次
        final_answer = ""  # 保存答案
        final_result = None  # 保存最终结果
        
        for event in v2_agent.run_stream(query, kb_ids, kb_names, history, selected_files):
            event_type = event.get('event')
            event_data = event.get('data', {})
            
            # 转换为前端期望的格式
            if event_type == 'start':
                yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"
            
            elif event_type == 'plan_start':
                # 规划开始 - 显示思考状态
                iteration += 1
                plan_start_data = {
                    'type': 'thinking',
                    'message': f'[第 {iteration} 轮规划] 正在分析问题和决策下一步行动',
                    'iteration': iteration
                }
                yield f"data: {json.dumps(plan_start_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'plan_complete':
                # 规划完成
                plan = event_data.get('plan', {})
                action = plan.get('action', '')
                reasoning = plan.get('reasoning', '')
                
                plan_data = {
                    'type': 'plan',
                    'iteration': iteration,
                    'action': action,
                    'reasoning': reasoning,
                    'message': f'[决策] {_get_action_display(action)} - {reasoning[:50]}...' if len(reasoning) > 50 else f'[决策] {_get_action_display(action)} - {reasoning}'
                }
                yield f"data: {json.dumps(plan_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'tool_start':
                # 工具开始
                step += 1
                tool_data = {
                    'type': 'tool_start',
                    'step': step,
                    'tool': event_data.get('tool'),
                    'tool_name': _get_tool_display_name(event_data.get('tool')),
                    'reasoning': event_data.get('reasoning', ''),
                    'args': event_data.get('args', {})
                }
                yield f"data: {json.dumps(tool_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'tool_end':
                # 工具完成
                tool_data = {
                    'type': 'tool_end',
                    'step': step,
                    'tool': event_data.get('tool'),
                    'execution_time': event_data.get('execution_time', 0),
                    'result_summary': event_data.get('summary', ''),
                }
                
                # 添加具体结果数据（兼容前端）
                if 'web_search_results' in event_data:
                    tool_data['web_search_results'] = event_data['web_search_results']
                if 'search_results' in event_data:
                    tool_data['search_results'] = event_data['search_results']
                if 'python_output' in event_data:
                    tool_data['python_details'] = {
                        'output': event_data['python_output'],
                        'code': event_data.get('python_code', ''),
                        'execution_time': event_data.get('execution_time', 0)
                    }
                
                yield f"data: {json.dumps(tool_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'evaluate':
                # 评估
                should_answer = event_data.get('should_answer', False)
                confidence = event_data.get('confidence', 0)
                reasoning = event_data.get('reasoning', '')
                
                if should_answer:
                    eval_message = f'[评估] 信息已充分，准备生成答案（置信度: {confidence:.0%}）'
                else:
                    eval_message = f'[评估] 信息不足，继续收集 - {reasoning[:60]}...' if len(reasoning) > 60 else f'[评估] 信息不足，继续收集 - {reasoning}'
                
                eval_data = {
                    'type': 'evaluate',
                    'should_answer': should_answer,
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'message': eval_message,
                    'evaluation': event_data
                }
                yield f"data: {json.dumps(eval_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'answer_start':
                # 开始生成答案
                yield f"data: {json.dumps({'type': 'answer_start'}, ensure_ascii=False)}\n\n"
            
            elif event_type == 'answer_chunk':
                # 答案片段（流式输出）
                chunk = event_data.get('chunk', '')
                if chunk:
                    chunk_data = {
                        'type': 'answer_chunk',
                        'chunk': chunk
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'answer':
                # 答案生成完成（保存完整答案）
                final_answer = event_data.get('answer', '')
                answer_data = {
                    'type': 'answer',
                    'answer': final_answer
                }
                yield f"data: {json.dumps(answer_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'refuse_request' or event_type == 'security_blocked':
                # 【安全拦截】拒绝请求或安全阻止
                refuse_data = {
                    'type': event_type,
                    'reason': event_data.get('reason', '该请求超出了系统职责范围'),
                    'message': event_data.get('message', ''),
                    'refuse_layer': event_data.get('refuse_layer', 'unknown')
                }
                yield f"data: {json.dumps(refuse_data, ensure_ascii=False)}\n\n"
            
            elif event_type == 'finish' or event_type == 'done':
                # 完成 - 包含答案（兼容前端）
                # 优先使用event_data中的final_answer（安全拒绝情况下会用到）
                if 'final_answer' in event_data:
                    final_answer = event_data['final_answer']
                
                done_data = {
                    'type': 'done',
                    'answer': final_answer,  # 添加答案字段
                    'sources': event_data.get('sources', []),
                    'process_log': event_data.get('process_log', {}),
                    'confidence': event_data.get('confidence', event_data.get('process_log', {}).get('final_evaluation', {}).get('confidence', 0.5)),
                    'confidence_reason': event_data.get('process_log', {}).get('final_evaluation', {}).get('reason', ''),
                    'used_retrieval': len(event_data.get('sources', [])) > 0,
                    'request_id': request_id  # 添加request_id
                }
                final_result = done_data  # 保存最终结果
                yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        
        # 结束请求日志记录
        if request_id and final_result:
            io_logger.end_request(request_id, final_result)
            
    except Exception as e:
        print(f"流式处理错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 发送错误事件
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"


def _get_tool_display_name(tool: str) -> str:
    """获取工具的显示名称"""
    tool_names = {
        'search': '知识库检索',
        'web_search': '网络搜索',
        'python_code': 'Python代码执行',
        'ready_to_answer': '准备回答'
    }
    return tool_names.get(tool, tool)


def _get_action_display(action: str) -> str:
    """获取行动的显示名称"""
    action_names = {
        'search': '知识库检索',
        'web_search': '网络搜索',
        'python_code': '代码执行',
        'ready_to_answer': '生成答案',
        'decompose_tasks': '任务分解'
    }
    return action_names.get(action, action)


@rag_v2_bp.route('/v2/info', methods=['GET'])
def v2_info():
    """
    获取V2架构信息
    """
    return jsonify({
        'success': True,
        'architecture': 'incremental_context',
        'version': 'v2.0',
        'description': '增量式上下文迭代架构',
        'features': [
            '单一上下文对象：所有信息在一个上下文中累积',
            'Plan → Tool → Evaluate → Output → Finish 工作流',
            '思维链可见：展示完整的推理过程',
            '避免重复调用：基于上下文历史智能决策'
        ],
        'workflow': {
            'Plan': '根据当前上下文规划下一步行动',
            'Tool Using': '执行工具调用，结果累积到上下文',
            'Evaluate': '评估信息是否足以回答',
            'Streaming Output': '流式输出最终答案',
            'Finish': '完成并记录完整上下文快照'
        }
    })


@rag_v2_bp.route('/v2/download_llm_io/<request_id>', methods=['GET'])
def download_llm_io(request_id):
    """
    下载指定请求的完整LLM调用载荷
    """
    try:
        io_logger = get_logger()
        if not io_logger or not io_logger.enabled:
            return jsonify({
                'success': False,
                'error': 'IO日志未启用'
            }), 404
        
        # 读取最新的日志文件
        log_file = io_logger.log_file
        if not os.path.exists(log_file):
            return jsonify({
                'success': False,
                'error': '日志文件不存在'
            }), 404
        
        # 解析日志文件，提取该request_id的所有记录
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line.strip())
                    if log.get('request_id') == request_id or log.get('type') in ['request_start', 'request_end'] and log.get('request_id') == request_id:
                        logs.append(log)
                except json.JSONDecodeError:
                    continue
        
        if not logs:
            return jsonify({
                'success': False,
                'error': f'未找到请求ID为 {request_id} 的日志'
            }), 404
        
        # 格式化为Markdown
        markdown_content = _format_llm_io_to_markdown(request_id, logs)
        
        # 创建临时文件
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
        temp_file.write(markdown_content)
        temp_file.close()
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'llm-io-{request_id}-{timestamp}.md'
        
        # 发送文件
        response = send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='text/markdown'
        )
        
        # 清理临时文件（在请求完成后）
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(temp_file.name)
            except:
                pass
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _format_llm_io_to_markdown(request_id, logs):
    """
    将日志格式化为易读的Markdown
    """
    lines = []
    
    # 标题
    lines.append('# LLM调用载荷详情\n\n')
    lines.append(f'**请求ID**: `{request_id}`\n')
    lines.append(f'**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
    lines.append('---\n\n')
    
    # 找出request_start和request_end
    request_start = None
    request_end = None
    llm_calls = []
    tool_calls = []
    api_calls = []
    
    for log in logs:
        log_type = log.get('type')
        if log_type == 'request_start':
            request_start = log
        elif log_type == 'request_end':
            request_end = log
        elif log_type == 'llm_call':
            llm_calls.append(log)
        elif log_type == 'tool_call':
            tool_calls.append(log)
        elif log_type == 'api_call':
            api_calls.append(log)
    
    # 用户问题
    if request_start:
        lines.append('## 📝 用户问题\n\n')
        lines.append(f'{request_start.get("query", "（无记录）")}\n\n')
        lines.append(f'**开始时间**: {request_start.get("timestamp")}\n')
        if request_end:
            lines.append(f'**结束时间**: {request_end.get("timestamp")}\n')
        lines.append('\n---\n\n')
    
    # 统计信息
    lines.append('## 📊 统计摘要\n\n')
    lines.append(f'- LLM调用: {len(llm_calls)} 次\n')
    lines.append(f'- 工具调用: {len(tool_calls)} 次\n')
    lines.append(f'- API调用: {len(api_calls)} 次\n')
    
    # 按阶段统计LLM调用
    phase_counts = {}
    for call in llm_calls:
        phase = call.get('phase', 'Unknown')
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    
    if phase_counts:
        lines.append('\n**LLM调用按阶段统计**:\n')
        for phase, count in sorted(phase_counts.items()):
            lines.append(f'- {phase}: {count}次\n')
    
    lines.append('\n---\n\n')
    
    # LLM调用详情 - 这是重点！
    if llm_calls:
        lines.append('## 🤖 LLM调用详情（完整载荷）\n\n')
        
        # 按阶段分组
        phases = {}
        for call in llm_calls:
            phase = call.get('phase', 'Unknown')
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(call)
        
        # 按顺序显示各阶段（包含Lite模式的阶段）
        phase_order = ['Plan', 'LitePlan', 'CodeGen', 'Evaluate', 'Answer', 'LiteAnswer', 'FinalEvaluate']
        for phase in phase_order:
            if phase not in phases:
                continue
            
            lines.append(f'### 阶段: {phase} ({len(phases[phase])} 次)\n\n')
            
            for idx, call in enumerate(phases[phase], 1):
                call_id = call.get('call_id')
                timestamp = call.get('timestamp', '')
                
                # 从正确的位置提取数据
                request_data = call.get('request', {})
                response_data = call.get('response', {})
                perf_data = call.get('performance', {})
                
                # 提取duration，可能在顶层或performance中
                duration_s = call.get('duration', 0)
                duration_ms = perf_data.get('duration_ms', duration_s * 1000)
                
                # 提取模型和参数
                model = request_data.get('model', 'unknown')
                temperature = request_data.get('temperature', 0)
                max_tokens = request_data.get('max_tokens', 0)
                messages = request_data.get('messages', [])
                
                lines.append(f'#### LLM调用 #{call_id}\n\n')
                lines.append(f'- **时间**: {timestamp}\n')
                lines.append(f'- **耗时**: {duration_ms:.0f}ms ({duration_ms/1000:.3f}秒)\n')
                lines.append(f'- **模型**: `{model}`\n')
                lines.append(f'- **参数**: temperature={temperature}, max_tokens={max_tokens}\n\n')
                
                # 完整Prompt
                lines.append('**📝 完整请求 Prompt**:\n\n')
                if messages:
                    for msg_idx, msg in enumerate(messages, 1):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        
                        if len(messages) > 1:
                            lines.append(f'*消息 #{msg_idx} ({role}):*\n\n')
                        
                        # 使用4个反引号包裹，避免内层3个反引号被误识别
                        lines.append('````text\n')
                        lines.append(content)
                        lines.append('\n````\n\n')
                else:
                    lines.append('*(无消息)*\n\n')
                
                # 完整Response
                content = response_data.get('content', '')
                error = response_data.get('error')
                
                if error:
                    lines.append(f'**❌ 错误**: `{error}`\n\n')
                else:
                    lines.append('**📤 完整响应内容**:\n\n')
                    # 使用4个反引号包裹，避免内层3个反引号被误识别
                    lines.append('````text\n')
                    lines.append(content)
                    lines.append('\n````\n\n')
                
                # 性能统计
                usage = perf_data.get('usage', {})
                if usage:
                    lines.append('**📊 性能统计**:\n\n')
                    lines.append(f'- 输入token: {usage.get("prompt_tokens", 0)}\n')
                    lines.append(f'- 输出token: {usage.get("completion_tokens", 0)}\n')
                    lines.append(f'- 总token: {usage.get("total_tokens", 0)}\n\n')
                
                lines.append('---\n\n')
        
        # 显示其他阶段
        for phase, calls in phases.items():
            if phase in phase_order:
                continue
            lines.append(f'### 阶段: {phase} ({len(calls)} 次)\n\n')
            for call in calls:
                # ... 同样的格式化代码
                pass
    
    # 工具调用详情
    if tool_calls:
        lines.append('## 🔧 工具调用详情\n\n')
        for idx, call in enumerate(tool_calls, 1):
            lines.append(f'### 工具调用 #{idx}\n\n')
            lines.append(f'- **工具**: {call.get("tool_name", "unknown")}\n')
            lines.append(f'- **耗时**: {call.get("duration_ms", 0)}ms\n\n')
            
            # 输入
            tool_input = call.get('input', {})
            if tool_input:
                lines.append('**输入**:\n```json\n')
                lines.append(json.dumps(tool_input, ensure_ascii=False, indent=2))
                lines.append('\n```\n\n')
            
            # 输出
            tool_output = call.get('output', {})
            if tool_output:
                lines.append('**输出**:\n```json\n')
                # 限制输出长度
                output_str = json.dumps(tool_output, ensure_ascii=False, indent=2)
                if len(output_str) > 3000:
                    output_str = output_str[:3000] + '\n... (输出过长，已截断)'
                lines.append(output_str)
                lines.append('\n```\n\n')
            
            lines.append('---\n\n')
    
    return ''.join(lines)

