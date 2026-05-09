"""
V1 Lite 调度器 - 简化的并行工具调用模式

工作流：
1. Plan: 分析问题，决定需要调用哪些工具
2. Execute: 并行执行所有工具
3. Answer: 基于工具结果生成最终答案

特点：
- 简化的调度逻辑（非完整 ReAct）
- 并行执行工具（提高效率）
- 工具调用限制：总共 0-5 次，web_search≤2, python_code≤2, search≤1
- 错误重试：仅当工具执行出错时修正并重试（最多 1 次）
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.api_clients import chat_client, baidu_search_client
from app.services.tools import tool_registry
from app.services.executor_factory import execute_python_code
from app.services.io_logger import get_logger as get_io_logger
from config import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """工具调用定义"""
    tool: str  # 工具名称
    args: Dict[str, Any]  # 工具参数
    reasoning: str = ""  # 调用理由
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tool': self.tool,
            'args': self.args,
            'reasoning': self.reasoning
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    tool: str
    success: bool
    result: Any = None
    error: str = ""
    execution_time: float = 0.0
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'tool': self.tool,
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time,
            'retry_count': self.retry_count
        }


@dataclass
class LiteDispatcherState:
    """Lite 调度器状态"""
    query: str
    kb_ids: List[int]
    kb_names: Dict[int, str] = field(default_factory=dict)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # 工具调用计划
    planned_tools: List[ToolCall] = field(default_factory=list)
    
    # 工具执行结果
    tool_results: List[ToolResult] = field(default_factory=list)
    
    # 最终答案
    final_answer: str = ""
    confidence: float = 0.0
    confidence_reason: str = ""
    
    # 状态标记
    completed: bool = False
    has_errors: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'query': self.query,
            'kb_ids': self.kb_ids,
            'kb_names': self.kb_names,
            'planned_tools': [t.to_dict() for t in self.planned_tools],
            'tool_results': [r.to_dict() for r in self.tool_results],
            'final_answer': self.final_answer,
            'confidence': self.confidence,
            'confidence_reason': self.confidence_reason,
            'completed': self.completed
        }


class LiteDispatcher:
    """
    V1 Lite 调度器
    
    简化的三阶段工作流：Plan → Execute → Answer
    """
    
    def __init__(self):
        self.max_total_tools = 5  # 总共最多 5 次工具调用
        self.max_web_search = 2   # 网络搜索最多 2 次
        self.max_python_code = 2  # Python 执行最多 2 次
        self.max_search = 1       # 知识库检索最多 1 次
        self.max_retry = 1        # 每个工具最多重试 1 次
    
    def dispatch(self, query: str, kb_ids: List[int], kb_names: Dict[int, str] = None, user_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        主调度函数
        
        Args:
            query: 用户问题
            kb_ids: 知识库 ID 列表
            kb_names: 知识库名称映射
            
        Returns:
            包含答案和执行日志的字典
        """
        state = LiteDispatcherState(
            query=query,
            kb_ids=kb_ids,
            kb_names=kb_names or {},
            user_id=user_id,
            request_id=request_id,
        )

        try:
            # 阶段 1: Plan - 规划工具调用
            logger.info(f"[Lite Dispatcher] 阶段 1: Plan - 规划工具调用")
            self._plan_phase(state)

            # 阶段 2: Execute - 并行执行工具
            logger.info(f"[Lite Dispatcher] 阶段 2: Execute - 并行执行 {len(state.planned_tools)} 个工具")
            self._execute_phase(state)
            
            # 阶段 3: Answer - 生成最终答案
            logger.info(f"[Lite Dispatcher] 阶段 3: Answer - 生成最终答案")
            self._answer_phase(state)
            
            state.completed = True
            
            return {
                'success': True,
                'answer': state.final_answer,
                'confidence': state.confidence,
                'confidence_reason': state.confidence_reason,
                'sources': self._extract_sources(state),
                'used_retrieval': any(r.tool == 'search' and r.success for r in state.tool_results),
                'process_log': state.to_dict()
            }
        
        except Exception as e:
            logger.error(f"[Lite Dispatcher] 执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'message': f'调度器执行失败: {str(e)}',
                'process_log': state.to_dict()
            }
    
    def dispatch_stream(self, query: str, kb_ids: List[int], kb_names: Dict[int, str] = None, request_id: str = None, user_id: Optional[str] = None):
        """
        流式调度函数 - 生成器模式
        
        Args:
            query: 用户问题
            kb_ids: 知识库 ID 列表
            kb_names: 知识库名称映射
            request_id: IO日志请求ID（可选）
            
        Yields:
            事件字典
        """
        # 设置当前请求ID到IO日志
        io_logger = get_io_logger()
        if io_logger and io_logger.enabled and request_id:
            io_logger.current_request_id = request_id
        
        state = LiteDispatcherState(
            query=query,
            kb_ids=kb_ids,
            kb_names=kb_names or {},
            user_id=user_id,
            request_id=request_id,
        )

        try:
            # 发送开始事件
            yield {'event': 'start', 'data': {}}
            
            # 阶段 1: Plan - 规划工具调用
            yield {'event': 'thinking', 'data': {'message': '正在规划工具调用...'}}
            self._plan_phase(state)
            
            # 发送规划完成事件
            if state.planned_tools:
                yield {
                    'event': 'plan_complete',
                    'data': {
                        'tool_count': len(state.planned_tools),
                        'message': f'规划了 {len(state.planned_tools)} 个工具调用'
                    }
                }
                
                # 发送每个工具的开始事件
                for i, tool_call in enumerate(state.planned_tools, 1):
                    yield {
                        'event': 'tool_start',
                        'data': {
                            'step': i,
                            'tool': tool_call.tool,
                            'reasoning': tool_call.reasoning,
                            'args': tool_call.args
                        }
                    }
            
            # 阶段 2: Execute - 并行执行工具
            yield {'event': 'execute_start', 'data': {'message': '并行执行工具...'}}
            self._execute_phase(state)
            
            # 发送每个工具的完成事件
            for i, tool_result in enumerate(state.tool_results, 1):
                if tool_result.success:
                    yield {
                        'event': 'tool_end',
                        'data': {
                            'step': i,
                            'tool': tool_result.tool,
                            'execution_time': tool_result.execution_time,
                            'result': tool_result.result,
                            'retry_count': tool_result.retry_count
                        }
                    }
                else:
                    yield {
                        'event': 'tool_error',
                        'data': {
                            'step': i,
                            'tool': tool_result.tool,
                            'error': tool_result.error,
                            'retry_count': tool_result.retry_count
                        }
                    }
            
            # 阶段 3: Answer - 生成最终答案（流式）
            yield {'event': 'answer_start', 'data': {'message': '正在生成答案...'}}
            
            # 流式生成答案
            for chunk in self._answer_phase_stream(state):
                yield {'event': 'answer_chunk', 'data': {'chunk': chunk}}
            
            state.completed = True
            
            # 发送完成事件
            yield {
                'event': 'finish',
                'data': {
                    'final_answer': state.final_answer,
                    'confidence': state.confidence,
                    'confidence_reason': state.confidence_reason,
                    'sources': self._extract_sources(state),
                    'used_retrieval': any(r.tool == 'search' and r.success for r in state.tool_results),
                    'process_log': state.to_dict()
                }
            }
        
        except Exception as e:
            logger.error(f"[Lite Dispatcher Stream] 执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            yield {
                'event': 'error',
                'data': {
                    'message': f'调度器执行失败: {str(e)}',
                    'process_log': state.to_dict()
                }
            }
    
    def _plan_phase(self, state: LiteDispatcherState):
        """
        阶段 1: Plan - 规划工具调用
        
        让 LLM 分析问题，决定需要调用哪些工具及其参数
        """
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        has_kb = bool(state.kb_ids)
        
        # 构建规划提示词
        prompt = PromptTemplates.get_lite_plan_prompt(
            current_time=current_time,
            query=state.query,
            has_kb=has_kb,
            kb_names=state.kb_names,
            max_web_search=self.max_web_search,
            max_python_code=self.max_python_code,
            max_search=self.max_search
        )
        
        # 记录LLM调用（Plan阶段）
        io_logger = get_io_logger()
        start_time = time.time()
        messages = [{"role": "user", "content": prompt}]
        
        # 调用 LLM 生成计划
        response = chat_client.chat(
            messages,
            temperature=0.1
        )
        
        # 记录IO日志
        if io_logger and io_logger.enabled:
            duration = time.time() - start_time
            io_logger.log_llm_call(
                phase='LitePlan',
                request_payload={
                    'model': chat_client.model,
                    'messages': messages,
                    'temperature': 0.1,
                    'max_tokens': 2000
                },
                response_payload={
                    'choices': [{'message': {'content': response}}]
                },
                duration=duration
            )
        
        # 解析计划
        plan = self._parse_plan(response)
        
        # 验证工具调用限制
        validated_plan = self._validate_plan(plan)
        
        state.planned_tools = validated_plan
        logger.info(f"[Plan] 规划了 {len(validated_plan)} 个工具调用")
    
    def _parse_plan(self, response: str) -> List[ToolCall]:
        """解析 LLM 返回的工具调用计划"""
        try:
            # 尝试提取 JSON
            json_match = None
            
            # 方法1: 寻找 JSON 数组
            import re
            array_match = re.search(r'\[[\s\S]*\]', response)
            if array_match:
                json_str = array_match.group()
                plan_data = json.loads(json_str)
            else:
                # 方法2: 寻找单个 JSON 对象
                obj_match = re.search(r'\{[\s\S]*\}', response)
                if obj_match:
                    json_str = obj_match.group()
                    obj = json.loads(json_str)
                    # 如果是包含 tools 字段的对象
                    if 'tools' in obj:
                        plan_data = obj['tools']
                    else:
                        plan_data = [obj]
                else:
                    logger.warning(f"[Plan] 无法解析计划，返回空列表")
                    return []
            
            # 转换为 ToolCall 对象
            tool_calls = []
            for item in plan_data:
                if isinstance(item, dict) and 'tool' in item:
                    tool_calls.append(ToolCall(
                        tool=item['tool'],
                        args=item.get('args', {}),
                        reasoning=item.get('reasoning', '')
                    ))
            
            return tool_calls
        
        except Exception as e:
            logger.error(f"[Plan] 解析计划失败: {e}")
            return []
    
    def _validate_plan(self, plan: List[ToolCall]) -> List[ToolCall]:
        """验证并调整工具调用计划，确保符合限制"""
        validated = []
        
        # 支持的工具列表
        supported_tools = {'python_code', 'web_search', 'vector_search'}
        
        # 统计各类工具数量
        web_search_count = 0
        python_code_count = 0
        search_count = 0
        
        for tool_call in plan:
            tool = tool_call.tool
            
            # 检查工具是否支持
            if tool not in supported_tools:
                logger.warning(f"[Plan] 工具 {tool} 不支持，跳过")
                continue
            
            # 检查各类工具的数量限制
            if tool == 'web_search':
                if web_search_count >= self.max_web_search:
                    logger.warning(f"[Plan] web_search 已达上限 {self.max_web_search}，跳过")
                    continue
                web_search_count += 1
            
            elif tool == 'python_code':
                if python_code_count >= self.max_python_code:
                    logger.warning(f"[Plan] python_code 已达上限 {self.max_python_code}，跳过")
                    continue
                python_code_count += 1
            
            elif tool == 'vector_search':
                if search_count >= self.max_search:
                    logger.warning(f"[Plan] vector_search 已达上限 {self.max_search}，跳过")
                    continue
                search_count += 1
            
            # 检查总数限制
            if len(validated) >= self.max_total_tools:
                logger.warning(f"[Plan] 工具调用总数已达上限 {self.max_total_tools}，停止添加")
                break
            
            validated.append(tool_call)
        
        return validated
    
    def _execute_phase(self, state: LiteDispatcherState):
        """
        阶段 2: Execute - 并行执行所有工具

        使用线程池并行执行，提高效率
        """
        if not state.planned_tools:
            logger.info("[Execute] 无需执行工具")
            return

        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=min(len(state.planned_tools), 5)) as executor:
            # 提交所有任务
            future_to_tool = {
                executor.submit(self._execute_tool, tool_call, state): tool_call
                for tool_call in state.planned_tools
            }
            
            # 收集结果
            for future in as_completed(future_to_tool):
                tool_call = future_to_tool[future]
                try:
                    result = future.result()
                    state.tool_results.append(result)
                    
                    if not result.success:
                        state.has_errors = True
                        logger.warning(f"[Execute] 工具 {result.tool} 执行失败: {result.error}")
                except Exception as e:
                    logger.error(f"[Execute] 工具 {tool_call.tool} 执行异常: {e}")
                    state.tool_results.append(ToolResult(
                        tool=tool_call.tool,
                        success=False,
                        error=str(e)
                    ))
                    state.has_errors = True
        
        # 如果有错误，尝试重试失败的工具
        if state.has_errors:
            self._retry_failed_tools(state)
    
    def _execute_tool(self, tool_call: ToolCall, state: LiteDispatcherState) -> ToolResult:
        """执行单个工具"""
        start_time = time.time()
        
        try:
            args = tool_call.args.copy()
            
            # 根据工具类型执行
            if tool_call.tool == 'python_code':
                # Python代码执行（state.user_id/request_id 用于速率限制和审计）
                query = args.get('query', '')
                result_data = execute_python_code(
                    query,
                    user_id=state.user_id,
                    request_id=state.request_id,
                )
                
                execution_time = time.time() - start_time
                
                if result_data.get('error'):
                    return ToolResult(
                        tool=tool_call.tool,
                        success=False,
                        error=result_data['error'],
                        execution_time=execution_time
                    )
                else:
                    return ToolResult(
                        tool=tool_call.tool,
                        success=True,
                        result=result_data,
                        execution_time=execution_time
                    )
            
            elif tool_call.tool == 'web_search':
                # 网络搜索
                query = args.get('query', '')
                top_k = args.get('top_k', 5)
                
                search_results = baidu_search_client.search(query, top_k=top_k)
                
                execution_time = time.time() - start_time
                
                return ToolResult(
                    tool=tool_call.tool,
                    success=True,
                    result=search_results,
                    execution_time=execution_time
                )
            
            elif tool_call.tool == 'vector_search':
                # 向量检索
                from app.services.semantic_search import search_knowledge_base
                
                query = args.get('query', '')
                kb_ids = args.get('kb_ids', state.kb_ids)
                top_k = args.get('top_k', 5)
                
                # 执行搜索
                search_result = search_knowledge_base(query, kb_ids, top_k=top_k)
                
                execution_time = time.time() - start_time
                
                # 检查搜索是否成功
                if not search_result.get('success', False):
                    return ToolResult(
                        tool=tool_call.tool,
                        success=False,
                        error=search_result.get('error', '向量搜索失败'),
                        execution_time=execution_time
                    )
                
                return ToolResult(
                    tool=tool_call.tool,
                    success=True,
                    result=search_result,
                    execution_time=execution_time
                )
            
            else:
                return ToolResult(
                    tool=tool_call.tool,
                    success=False,
                    error=f"未知工具: {tool_call.tool}"
                )
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            execution_time = time.time() - start_time
            return ToolResult(
                tool=tool_call.tool,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _retry_failed_tools(self, state: LiteDispatcherState):
        """重试失败的工具（最多重试 1 次）"""
        failed_results = [r for r in state.tool_results if not r.success and r.retry_count < self.max_retry]
        
        if not failed_results:
            return
        
        logger.info(f"[Retry] 重试 {len(failed_results)} 个失败的工具")
        
        # 为失败的工具重新生成参数
        retry_tools = []
        for failed_result in failed_results:
            # 找到原始的 tool_call
            original_call = next(
                (tc for tc in state.planned_tools if tc.tool == failed_result.tool),
                None
            )
            
            if original_call:
                # 尝试修正参数
                corrected_call = self._correct_tool_call(original_call, failed_result.error, state)
                if corrected_call:
                    retry_tools.append((corrected_call, failed_result))
        
        # 执行重试
        for corrected_call, failed_result in retry_tools:
            logger.info(f"[Retry] 重试工具 {corrected_call.tool}")
            new_result = self._execute_tool(corrected_call, state)
            new_result.retry_count = failed_result.retry_count + 1
            
            # 移除旧的失败结果，添加新结果
            state.tool_results.remove(failed_result)
            state.tool_results.append(new_result)
            
            if new_result.success:
                logger.info(f"[Retry] 工具 {corrected_call.tool} 重试成功")
            else:
                logger.warning(f"[Retry] 工具 {corrected_call.tool} 重试仍然失败")
    
    def _correct_tool_call(self, tool_call: ToolCall, error: str, state: LiteDispatcherState) -> Optional[ToolCall]:
        """
        根据错误信息修正工具调用参数
        
        使用 LLM 分析错误并生成修正后的参数
        """
        try:
            prompt = f"""工具调用失败，请分析错误并修正参数。

【原始工具调用】
工具: {tool_call.tool}
参数: {json.dumps(tool_call.args, ensure_ascii=False)}
理由: {tool_call.reasoning}

【错误信息】
{error}

【用户问题】
{state.query}

请分析错误原因，并返回修正后的工具调用（JSON格式）：
{{
    "tool": "{tool_call.tool}",
    "args": {{...修正后的参数...}},
    "reasoning": "修正理由"
}}

只返回 JSON，不要其他解释。"""
            
            response = chat_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            # 解析修正后的工具调用
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                corrected = json.loads(json_match.group())
                return ToolCall(
                    tool=corrected['tool'],
                    args=corrected.get('args', {}),
                    reasoning=corrected.get('reasoning', '参数修正')
                )
        
        except Exception as e:
            logger.error(f"[Retry] 修正工具调用失败: {e}")
        
        return None
    
    def _answer_phase(self, state: LiteDispatcherState):
        """
        阶段 3: Answer - 基于工具结果生成最终答案
        """
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        
        # 构建工具结果摘要
        tools_summary = self._build_tools_summary(state)
        
        # 构建答案生成提示词
        prompt = PromptTemplates.get_lite_answer_prompt(
            current_time=current_time,
            query=state.query,
            tools_summary=tools_summary
        )
        
        # 调用 LLM 生成答案
        answer = chat_client.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        state.final_answer = answer
        
        # 简单的置信度评估
        successful_tools = sum(1 for r in state.tool_results if r.success)
        total_tools = len(state.tool_results)
        
        if total_tools == 0:
            # 无工具调用，直接回答
            state.confidence = 0.7
            state.confidence_reason = "基于通用知识直接回答"
        elif successful_tools == total_tools:
            # 所有工具都成功
            state.confidence = 0.9
            state.confidence_reason = f"所有 {total_tools} 个工具调用均成功"
        else:
            # 部分工具失败
            state.confidence = 0.5 + (successful_tools / total_tools) * 0.3
            state.confidence_reason = f"{total_tools} 个工具中 {successful_tools} 个成功"
    
    def _answer_phase_stream(self, state: LiteDispatcherState):
        """
        阶段 3: Answer - 基于工具结果生成最终答案（流式）
        
        Yields:
            答案片段（字符串）
        """
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        
        # 构建工具结果摘要
        tools_summary = self._build_tools_summary(state)
        
        # 构建答案生成提示词
        prompt = PromptTemplates.get_lite_answer_prompt(
            current_time=current_time,
            query=state.query,
            tools_summary=tools_summary
        )
        
        # 记录LLM调用（Answer阶段）
        io_logger = get_io_logger()
        start_time = time.time()
        messages = [{"role": "user", "content": prompt}]
        
        # 流式调用 LLM 生成答案
        answer_buffer = []
        for chunk in chat_client.chat_stream_generator(
            messages,
            temperature=0.3
        ):
            answer_buffer.append(chunk)
            yield chunk
        
        # 保存完整答案
        state.final_answer = ''.join(answer_buffer)
        
        # 记录IO日志
        if io_logger and io_logger.enabled:
            duration = time.time() - start_time
            io_logger.log_llm_call(
                phase='LiteAnswer',
                request_payload={
                    'model': chat_client.model,
                    'messages': messages,
                    'temperature': 0.3,
                    'max_tokens': 2000,
                    'stream': True
                },
                response_payload={
                    'choices': [{'message': {'content': state.final_answer}}]
                },
                duration=duration
            )
        
        # 简单的置信度评估
        successful_tools = sum(1 for r in state.tool_results if r.success)
        total_tools = len(state.tool_results)
        
        if total_tools == 0:
            # 无工具调用，直接回答
            state.confidence = 0.7
            state.confidence_reason = "基于通用知识直接回答"
        elif successful_tools == total_tools:
            # 所有工具都成功
            state.confidence = 0.9
            state.confidence_reason = f"所有 {total_tools} 个工具调用均成功"
        else:
            # 部分工具失败
            state.confidence = 0.5 + (successful_tools / total_tools) * 0.3
            state.confidence_reason = f"{total_tools} 个工具中 {successful_tools} 个成功"
    
    def _build_tools_summary(self, state: LiteDispatcherState) -> str:
        """构建工具执行结果摘要"""
        if not state.tool_results:
            return "无工具调用"
        
        lines = []
        for i, result in enumerate(state.tool_results, 1):
            status = "✅ 成功" if result.success else "❌ 失败"
            lines.append(f"\n【工具 {i}: {result.tool}】")
            lines.append(f"状态: {status}")
            
            if result.success:
                # 格式化结果
                if isinstance(result.result, dict):
                    lines.append(f"结果: {json.dumps(result.result, ensure_ascii=False, indent=2)}")
                else:
                    lines.append(f"结果: {result.result}")
            else:
                lines.append(f"错误: {result.error}")
            
            if result.retry_count > 0:
                lines.append(f"重试次数: {result.retry_count}")
        
        return "\n".join(lines)
    
    def _extract_sources(self, state: LiteDispatcherState) -> List[Dict[str, Any]]:
        """从工具结果中提取来源信息"""
        sources = []
        
        for result in state.tool_results:
            if not result.success:
                continue
            
            # 从知识库检索结果中提取
            if result.tool == 'vector_search' and isinstance(result.result, dict):
                chunks = result.result.get('chunks', [])
                for chunk in chunks:
                    sources.append({
                        'type': 'knowledge_base',
                        'content': chunk.get('text', ''),
                        'score': chunk.get('score', 0),
                        'metadata': chunk.get('metadata', {})
                    })
            
            # 从网络搜索结果中提取
            elif result.tool == 'web_search' and isinstance(result.result, dict):
                results = result.result.get('results', [])
                for item in results:
                    sources.append({
                        'type': 'web_search',
                        'title': item.get('title', ''),
                        'content': item.get('content', ''),
                        'url': item.get('url', '')
                    })
            
            # 从代码执行结果中提取
            elif result.tool == 'python_code' and isinstance(result.result, dict):
                sources.append({
                    'type': 'code_execution',
                    'code': result.result.get('code', ''),
                    'output': result.result.get('output', '')
                })
        
        return sources


# 全局实例
lite_dispatcher = LiteDispatcher()

