"""
V2 Agentic RAG Agent - 增量式上下文迭代架构

核心设计：
1. 单一上下文对象，增量式累积所有信息（思维链、工具调用、证据）
2. Plan → Tool Using → Evaluate → Streaming Output → Finish 工作流
3. 所有工具调用结果都在一个上下文中，确保Agent正确决策
"""
import json
import time
import logging
import os
from typing import Dict, Any, List, Generator, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 根据环境变量决定使用哪个客户端
_use_logging_client = os.getenv('ENABLE_IO_LOGGING', 'true').lower() == 'true'

if _use_logging_client:
    try:
        from app.services.api_clients_with_logging import (
            chat_client_with_logging as chat_client,
            search_client_with_logging as baidu_search_client
        )
    except ImportError:
        # 如果导入失败，回退到普通客户端
        from app.services.api_clients import chat_client, baidu_search_client
else:
    from app.services.api_clients import chat_client, baidu_search_client

from app.services.tools import tool_registry
from app.services.executor_factory import execute_python_code
from app.services.io_logger import get_logger as get_io_logger
from app.services.security_checker import security_checker
from config import PromptTemplates

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class SubTask:
    """子任务"""
    id: int
    description: str  # 子任务描述
    required_tool: Optional[str] = None  # 需要的工具类型
    status: str = "pending"  # pending, in_progress, completed, failed
    evidence_key: Optional[str] = None  # 对应的证据key
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolCallLog:
    """工具调用日志"""
    tool: str
    query: str
    args: Dict[str, Any]
    result_summary: str
    full_result: Any
    timestamp: float
    execution_time: float
    subtask_id: Optional[int] = None  # 关联的子任务ID
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentContext:
    """
    增量式上下文对象
    包含整个推理过程的所有信息，确保Agent在统一上下文中决策
    """
    user_query: str
    kb_ids: List[int]
    kb_names: Dict[int, str] = field(default_factory=dict)  # 知识库ID到名称的映射
    conversation_history: List[Dict[str, str]] = field(default_factory=list)  # 对话历史
    selected_files: List[str] = field(default_factory=list)  # 用户选中的文件列表
    
    # 任务分解（新增）
    subtasks: List[SubTask] = field(default_factory=list)
    current_subtask_id: Optional[int] = None  # 当前正在处理的子任务
    
    # 规划
    plan: Optional[str] = None
    
    # 证据（分类存储）
    evidence: Dict[str, List[Any]] = field(default_factory=dict)
    
    # 工具调用历史
    tools_log: List[ToolCallLog] = field(default_factory=list)
    
    # 工具调用次数统计（新增）
    tool_call_counts: Dict[str, int] = field(default_factory=lambda: {
        'web_search': 0,
        'python_code': 0,
        'search': 0
    })
    
    # 工具调用上限（新增）
    tool_call_limits: Dict[str, int] = field(default_factory=lambda: {
        'web_search': 3,
        'python_code': 10,
        'search': 10
    })
    
    # 评估历史
    evaluations: List[Dict[str, Any]] = field(default_factory=list)
    
    # 最终答案
    final_answer: Optional[str] = None
    
    # 最终评估
    final_evaluation: Optional[Dict[str, Any]] = None
    
    # 元数据
    iteration_count: int = 0
    status: str = "running"  # running, done, error
    
    # 错误追踪（新增）
    consecutive_errors: int = 0  # 连续错误次数
    max_consecutive_errors: int = 3  # 最大连续错误次数
    last_error_message: Optional[str] = None  # 最后的错误信息
    
    def add_tool_log(self, log: ToolCallLog):
        """添加工具调用日志"""
        self.tools_log.append(log)
        self.iteration_count += 1
        
        # 检测错误并更新连续错误计数
        # 修复：检查error的值是否非空，而不仅仅是键是否存在
        if log.full_result and log.full_result.get('error'):
            self.consecutive_errors += 1
            self.last_error_message = log.full_result.get('error', '')
            logger.warning(f"[V2] 检测到工具调用错误，连续错误次数: {self.consecutive_errors}/{self.max_consecutive_errors}")
        else:
            # 成功调用则重置连续错误计数
            if self.consecutive_errors > 0:
                logger.info(f"[V2] 工具调用成功，重置连续错误计数")
            self.consecutive_errors = 0
            self.last_error_message = None
    
    def add_evidence(self, category: str, data: Any):
        """添加证据"""
        if category not in self.evidence:
            self.evidence[category] = []
        self.evidence[category].append(data)
    
    def add_evaluation(self, evaluation: Dict[str, Any]):
        """添加评估"""
        self.evaluations.append(evaluation)
    
    def get_context_summary(self, for_planning: bool = True) -> str:
        """
        获取上下文摘要（用于提示词）
        
        Args:
            for_planning: True表示用于Plan阶段（显示下一轮），False表示用于Evaluate/Final（显示当前轮）
        """
        lines = []
        
        # 对话历史（如果有）
        if self.conversation_history:
            lines.append("【对话历史】")
            for msg in self.conversation_history:
                role = "用户" if msg['role'] == 'user' else "助手"
                content = msg['content']
                # 限制历史长度，避免过长
                if len(content) > 200:
                    content = content[:200] + "..."
                lines.append(f"{role}: {content}")
            lines.append("")
        
        lines.append(f"【当前问题】{self.user_query}")
        
        # 知识库信息
        if self.kb_names:
            lines.append(f"\n【可用知识库】")
            for kb_id, kb_name in self.kb_names.items():
                lines.append(f"- [{kb_id}] {kb_name}")
        
        # 用户选中的文件信息
        if self.selected_files:
            lines.append(f"\n【用户选中的文件（可直接分析）】")
            try:
                from app.routes.file_upload import get_upload_folder
                import os
                upload_dir = get_upload_folder()
                
                for filename in self.selected_files:
                    filepath = os.path.join(upload_dir, filename)
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        size_str = f"{file_size / 1024:.1f}KB" if file_size < 1024 * 1024 else f"{file_size / (1024*1024):.1f}MB"
                        lines.append(f"- {filename} ({size_str})")
                        lines.append(f"  文件路径: {filepath}")
                    else:
                        lines.append(f"- {filename} (文件不存在)")
                lines.append("提示：使用 python_code 工具时可以直接读取上述文件路径")
            except Exception as e:
                lines.append(f"- 文件信息获取失败: {str(e)}")
                pass
        
        # 工具使用情况
        lines.append(f"\n【工具使用情况】")
        lines.append(self.get_tool_usage_summary())
        
        # 子任务状态（新增）
        if self.subtasks:
            lines.append(f"\n【子任务列表】")
            lines.append(self.get_subtasks_summary())
        
        if self.plan:
            lines.append(f"\n【规划】{self.plan}")
        
        if self.tools_log:
            lines.append("\n【工具调用历史】")
            for i, log in enumerate(self.tools_log, 1):
                task_info = f" [任务{log.subtask_id}]" if log.subtask_id else ""
                lines.append(f"{i}. {log.tool}({log.query}){task_info} → {log.result_summary}")
        
        if self.evidence:
            lines.append("\n【已收集证据】")
            for category, items in self.evidence.items():
                lines.append(f"- {category}: {len(items)} 条")
        
        if self.evaluations:
            last_eval = self.evaluations[-1]
            lines.append(f"\n【上次评估】{last_eval.get('reason', '')}")
        
        return "\n".join(lines)
    
    def get_evidence_detail(self) -> str:
        """获取证据详情（用于生成答案）"""
        lines = []
        for category, items in self.evidence.items():
            lines.append(f"\n【{category}】")
            for i, item in enumerate(items, 1):
                if isinstance(item, dict):
                    lines.append(f"{i}. {json.dumps(item, ensure_ascii=False, indent=2)}")
                else:
                    lines.append(f"{i}. {str(item)}")
        return "\n".join(lines)
    
    def can_continue(self) -> bool:
        """是否可以继续迭代（不再限制总迭代次数，仅限制单个工具调用次数）"""
        # 检查连续错误次数
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.error(f"[V2] 连续错误达到上限 ({self.consecutive_errors}次)，强制停止")
            self.status = "error"
            return False
        
        return self.status == "running"
    
    def can_call_tool(self, tool_name: str) -> bool:
        """检查是否可以调用指定工具（是否超过调用次数限制）"""
        if tool_name not in self.tool_call_counts:
            return True
        current_count = self.tool_call_counts.get(tool_name, 0)
        limit = self.tool_call_limits.get(tool_name, float('inf'))
        return current_count < limit
    
    def increment_tool_count(self, tool_name: str):
        """增加工具调用次数"""
        if tool_name in self.tool_call_counts:
            self.tool_call_counts[tool_name] += 1
    
    def get_tool_usage_summary(self) -> str:
        """获取工具使用情况摘要"""
        lines = []
        for tool_name in ['search', 'web_search', 'python_code']:
            if tool_name in self.tool_call_counts:
                count = self.tool_call_counts[tool_name]
                limit = self.tool_call_limits[tool_name]
                # 明确标记已达上限的工具
                if count >= limit:
                    lines.append(f"- {tool_name}: {count}/{limit}次 ❌ 已达上限，不可再调用")
                else:
                    remaining = limit - count
                    lines.append(f"- {tool_name}: {count}/{limit}次 ✅ 剩余{remaining}次")
        return "\n".join(lines) if lines else "（无工具调用）"
    
    def add_subtask(self, description: str, required_tool: Optional[str] = None) -> SubTask:
        """添加子任务"""
        task_id = len(self.subtasks) + 1
        task = SubTask(id=task_id, description=description, required_tool=required_tool)
        self.subtasks.append(task)
        return task
    
    def get_subtask(self, task_id: int) -> Optional[SubTask]:
        """获取子任务"""
        for task in self.subtasks:
            if task.id == task_id:
                return task
        return None
    
    def get_pending_subtasks(self) -> List[SubTask]:
        """获取待处理的子任务"""
        return [t for t in self.subtasks if t.status == "pending"]
    
    def get_completed_subtasks(self) -> List[SubTask]:
        """获取已完成的子任务"""
        return [t for t in self.subtasks if t.status == "completed"]
    
    def mark_subtask_completed(self, task_id: int, evidence_key: str):
        """标记子任务为已完成"""
        task = self.get_subtask(task_id)
        if task:
            task.status = "completed"
            task.evidence_key = evidence_key
    
    def all_subtasks_completed(self) -> bool:
        """检查是否所有子任务都已完成"""
        if not self.subtasks:
            return False
        return all(t.status == "completed" for t in self.subtasks)
    
    def get_subtasks_summary(self) -> str:
        """获取子任务摘要"""
        if not self.subtasks:
            return "（未识别到子任务）"
        
        lines = []
        for task in self.subtasks:
            status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "failed": "❌"}
            emoji = status_emoji.get(task.status, "❓")
            tool_info = f" [需要: {task.required_tool}]" if task.required_tool else ""
            lines.append(f"{emoji} 任务{task.id}: {task.description}{tool_info}")
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "user_query": self.user_query,
            "kb_ids": self.kb_ids,
            "kb_names": self.kb_names,
            "conversation_history": self.conversation_history,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "current_subtask_id": self.current_subtask_id,
            "plan": self.plan,
            "evidence": self.evidence,
            "tools_log": [log.to_dict() for log in self.tools_log],
            "tool_call_counts": self.tool_call_counts,
            "tool_call_limits": self.tool_call_limits,
            "evaluations": self.evaluations,
            "final_answer": self.final_answer,
            "final_evaluation": self.final_evaluation,
            "iteration_count": self.iteration_count,
            "status": self.status,
            "consecutive_errors": self.consecutive_errors,
            "max_consecutive_errors": self.max_consecutive_errors,
            "last_error_message": self.last_error_message
        }


class V2Agent:
    """
    V2 Agentic RAG Agent
    
    工作流：Plan → Tool Using → Evaluate → Streaming Output → Finish
    特点：增量式上下文迭代，所有信息在单一上下文中累积
    """
    
    def __init__(self):
        self.model_name = "ERNIE-Speed-128K"
        self.temperature = 0.1
    
    def run(self, query: str, kb_ids: List[int] = None, kb_names: Dict[int, str] = None, history: List[Dict[str, str]] = None, selected_files: List[str] = None) -> Dict[str, Any]:
        """
        运行Agent（非流式）
        
        Args:
            query: 用户查询
            kb_ids: 知识库ID列表
            kb_names: 知识库ID到名称的映射
            history: 对话历史
            selected_files: 用户选中的文件列表
            
        Returns:
            包含完整上下文的结果字典
        """
        # 【第0层安全防护】基于LLM的智能安全审查
        logger.info(f"[V2] 开始LLM安全审查: {query[:50]}")
        try:
            security_prompt = PromptTemplates.get_security_review_prompt(query, history, selected_files)
            security_response = chat_client.chat(
                [{"role": "user", "content": security_prompt}],
                temperature=0.1  # 使用较低温度保证审查的一致性
            )
            
            # 解析安全审查结果
            security_result = self._parse_json_response(security_response)
            is_llm_safe = security_result.get('is_safe', True)
            risk_level = security_result.get('risk_level', 'unknown')
            security_reason = security_result.get('reason', '未知原因')
            category = security_result.get('category', '未分类')
            
            logger.info(f"[V2] LLM安全审查结果: is_safe={is_llm_safe}, risk_level={risk_level}, category={category}")
            
            # 如果LLM判定为不安全，立即拒绝
            if not is_llm_safe:
                logger.warning(f"[V2] LLM安全审查拒绝: {query[:50]} - {security_reason}")
                
                # 生成拒绝消息（简化版）
                final_answer = """该请求不被支持。"""
                
                return {
                    'success': False,
                    'answer': final_answer,
                    'confidence': 0,
                    'confidence_reason': security_reason,
                    'sources': [],
                    'process_log': {
                        'security_blocked': True,
                        'security_layer': 'llm_review',
                        'risk_level': risk_level,
                        'reason': security_reason,
                        'category': category
                    }
                }
                
        except Exception as e:
            # LLM安全审查失败，记录错误但继续执行（避免因审查失败导致服务不可用）
            logger.error(f"[V2] LLM安全审查异常: {e}")
            # 继续执行后续的安全检查
        
        # 【第1层安全防护】基于规则的安全检查
        is_safe, reason = security_checker.check_request_safety(query)
        if not is_safe:
            logger.warning(f"[V2] 安全拒绝（规则检查）: {query[:50]} - {reason}")
            
            final_answer = """该请求不被支持。"""
            
            return {
                'success': False,
                'answer': final_answer,
                'confidence': 0,
                'confidence_reason': reason,
                'sources': [],
                'process_log': {
                    'security_blocked': True,
                    'security_layer': 'rule_check',
                    'reason': reason
                }
            }
        
        # 初始化上下文
        context = AgentContext(
            user_query=query, 
            kb_ids=kb_ids or [],
            kb_names=kb_names or {},
            conversation_history=history or [],
            selected_files=selected_files or []
        )
        
        # 主循环
        while context.can_continue():
            # 1. Plan：规划下一步
            plan_result = self._plan(context)
            
            # 【安全防护】检查是否拒绝请求（LLM层面拒绝）
            if plan_result['action'] == 'refuse_request':
                logger.warning(f"[V2] 🛡️ 安全拒绝（LLM判断）: {plan_result.get('args', {}).get('reason', '未知原因')}")
                context.final_answer = "该请求不被支持。"
                refuse_reason = plan_result.get('args', {}).get('reason', '该请求超出了我的职责范围')
                return {
                    'success': False,
                    'answer': context.final_answer,
                    'confidence': 0,
                    'confidence_reason': refuse_reason,
                    'sources': [],
                    'process_log': {
                        'security_refused': True,
                        'refuse_reason': refuse_reason,
                        'refuse_layer': 'llm_plan'
                    }
                }
            
            # 2. Tool Using：执行工具
            if plan_result['action'] == 'ready_to_answer':
                # 准备回答
                break
            else:
                self._execute_tool(context, plan_result)
            
            # 3. Evaluate：评估是否需要继续
            eval_result = self._evaluate(context)
            
            if eval_result['should_answer']:
                break
        
        # 【重要】检查是否因错误而中止
        if context.status == "error":
            logger.error(f"[V2] 由于连续错误（{context.consecutive_errors}次），任务中止")
            return {
                'success': False,
                'answer': context.final_answer or '处理过程中遇到错误，无法生成答案',
                'confidence': 0,
                'confidence_reason': context.last_error_message or '连续工具调用失败',
                'sources': self._extract_sources(context),
                'process_log': {
                    'status': 'error',
                    'consecutive_errors': context.consecutive_errors,
                    'last_error': context.last_error_message,
                    'context': context.to_dict()
                }
            }
        
        # 4. Generate Answer：生成答案
        answer = self._generate_answer(context)
        context.final_answer = answer
        
        # 5. Final Evaluation：最终评估
        final_eval = self._final_evaluate(context)
        context.final_evaluation = final_eval
        context.status = "done"
        
        # 返回结果
        return {
            'success': True,
            'answer': answer,
            'confidence': final_eval.get('confidence', 0.5),
            'confidence_reason': final_eval.get('reason', ''),
            'sources': self._extract_sources(context),
            'process_log': context.to_dict()
        }
    
    def run_stream(self, query: str, kb_ids: List[int] = None, kb_names: Dict[int, str] = None, history: List[Dict[str, str]] = None, selected_files: List[str] = None) -> Generator[Dict[str, Any], None, None]:
        """
        运行Agent（流式）
        
        Args:
            query: 用户查询
            kb_ids: 知识库ID列表
            kb_names: 知识库ID到名称的映射
            history: 对话历史
            selected_files: 用户选中的文件列表
        
        Yields:
            事件字典 {'event': 事件类型, 'data': 数据}
        """
        # 【第0层安全防护】基于LLM的智能安全审查
        logger.info(f"[V2] 开始LLM安全审查: {query[:50]}")
        try:
            security_prompt = PromptTemplates.get_security_review_prompt(query, history, selected_files)
            security_response = chat_client.chat(
                [{"role": "user", "content": security_prompt}],
                temperature=0.1  # 使用较低温度保证审查的一致性
            )
            
            # 解析安全审查结果
            security_result = self._parse_json_response(security_response)
            is_llm_safe = security_result.get('is_safe', True)
            risk_level = security_result.get('risk_level', 'unknown')
            security_reason = security_result.get('reason', '未知原因')
            category = security_result.get('category', '未分类')
            
            logger.info(f"[V2] LLM安全审查结果: is_safe={is_llm_safe}, risk_level={risk_level}, category={category}")
            
            # 如果LLM判定为不安全，立即拒绝
            if not is_llm_safe:
                logger.warning(f"[V2] LLM安全审查拒绝: {query[:50]} - {security_reason}")
                yield {'event': 'start', 'data': {}}
                yield {
                    'event': 'security_blocked',
                    'data': {
                        'reason': '该请求不被支持',
                        'risk_level': risk_level,
                        'category': category,
                        'message': '该请求不被支持'
                    }
                }
                
                # 生成拒绝消息（简化版）
                final_answer = """该请求不被支持。"""
                
                yield {
                    'event': 'answer_chunk',
                    'data': {'chunk': final_answer}
                }
                yield {
                    'event': 'finish',
                    'data': {
                        'final_answer': final_answer,
                        'confidence': 0,
                        'sources': [],
                        'context': {
                            'security_blocked': True,
                            'security_layer': 'llm_review',
                            'risk_level': risk_level,
                            'reason': security_reason
                        }
                    }
                }
                return
                
        except Exception as e:
            # LLM安全审查失败，记录错误但继续执行（避免因审查失败导致服务不可用）
            logger.error(f"[V2] LLM安全审查异常: {e}")
            # 继续执行后续的安全检查
        
        # 【第1层安全防护】基于规则的安全检查
        is_safe, reason = security_checker.check_request_safety(query)
        if not is_safe:
            logger.warning(f"[V2] 安全拒绝: {query[:50]} - {reason}")
            yield {'event': 'start', 'data': {}}
            yield {
                'event': 'security_blocked',
                'data': {
                    'reason': '该请求不被支持',
                    'message': '该请求不被支持'
                }
            }
            # 直接返回拒绝消息（简化版）
            final_answer = "该请求不被支持。"
            
            yield {
                'event': 'answer_chunk',
                'data': {'chunk': final_answer}
            }
            yield {
                'event': 'finish',
                'data': {
                    'final_answer': final_answer,
                    'confidence': 0,
                    'sources': [],
                    'context': {'security_blocked': True, 'reason': reason}
                }
            }
            return
        
        # 初始化上下文
        context = AgentContext(
            user_query=query, 
            kb_ids=kb_ids or [],
            kb_names=kb_names or {},
            conversation_history=history or [],
            selected_files=selected_files or []
        )
        logger.info(f"[V2] 开始处理: {query[:50]}")
        
        yield {'event': 'start', 'data': {}}
        
        # 主循环
        while context.can_continue():
            logger.info(f"[V2] 迭代 {context.iteration_count + 1}")
            # 1. Plan
            yield {'event': 'plan_start', 'data': {}}
            plan_result = self._plan(context)
            logger.info(f"[V2] Plan: {plan_result.get('action')}")
            yield {'event': 'plan_complete', 'data': {'plan': plan_result}}
            
            # 2. 检查是否拒绝请求（LLM层面拒绝）
            if plan_result['action'] == 'refuse_request':
                logger.warning(f"[V2] 🛡️ 安全拒绝（LLM判断）: {plan_result.get('args', {}).get('reason', '未知原因')}")
                # 生成拒绝消息并结束（简化版）
                refuse_reason = plan_result.get('args', {}).get('reason', '该请求超出了我的职责范围')
                context.final_answer = "该请求不被支持。"
                
                yield {
                    'event': 'refuse_request',
                    'data': {
                        'reason': refuse_reason,
                        'message': context.final_answer
                    }
                }
                
                # 发送finish事件并立即终止
                yield {
                    'event': 'finish',
                    'data': {
                        'final_answer': context.final_answer,
                        'confidence': 0,
                        'sources': [],
                        'context': {
                            'security_refused': True,
                            'refuse_reason': refuse_reason,
                            'refuse_layer': 'llm_plan'
                        }
                    }
                }
                return  # 立即终止，不再生成答案
            
            # 3. Tool Using
            if plan_result['action'] == 'ready_to_answer':
                break
            else:
                # 发送工具开始事件
                yield {
                    'event': 'tool_start',
                    'data': {
                        'tool': plan_result['action'],
                        'reasoning': plan_result.get('reasoning', ''),
                        'args': plan_result.get('args', {})
                    }
                }
                
                # 执行工具
                start_time = time.time()
                tool_result = self._execute_tool(context, plan_result)
                execution_time = time.time() - start_time
                
                # 【安全检查】检测工具执行中的安全拦截
                if tool_result.get('error'):
                    error_msg = str(tool_result.get('error', ''))
                    # 检测是否为安全相关错误
                    security_keywords = [
                        '安全检查失败', '禁止使用', '禁止导入', '禁止访问',
                        '安全策略', '权限不足', '危险操作', '安全拒绝'
                    ]
                    is_security_error = any(keyword in error_msg for keyword in security_keywords)
                    
                    if is_security_error:
                        logger.warning(f"[V2] 🛡️ 安全拒绝（工具执行层）: {error_msg}")
                        
                        # 生成安全拒绝消息（简化版）
                        context.final_answer = "该请求不被支持。"
                        
                        # 发送工具错误事件
                        yield {
                            'event': 'tool_end',
                            'data': {
                                'tool': plan_result['action'],
                                'error': error_msg,
                                'security_blocked': True,
                                'execution_time': execution_time
                            }
                        }
                        
                        # 发送finish事件并立即终止
                        yield {
                            'event': 'finish',
                            'data': {
                                'final_answer': context.final_answer,
                                'confidence': 0,
                                'sources': [],
                                'context': {
                                    'security_refused': True,
                                    'refuse_reason': error_msg,
                                    'refuse_layer': 'tool_execution',
                                    'blocked_tool': plan_result['action']
                                }
                            }
                        }
                        return  # 立即终止
                
                # 发送工具完成事件
                yield {
                    'event': 'tool_end',
                    'data': {
                        'tool': plan_result['action'],
                        'result_summary': tool_result.get('summary', ''),
                        'execution_time': execution_time,
                        **tool_result  # 包含具体结果数据
                    }
                }
            
            # 4. Evaluate
            logger.info(f"[V2] Evaluate 开始")
            eval_result = self._evaluate(context)
            logger.info(f"[V2] Evaluate: {eval_result}")
            yield {'event': 'evaluate', 'data': eval_result}
            
            if 'should_answer' not in eval_result:
                logger.error(f"[V2] ❌ 缺少should_answer! eval_result={eval_result}")
                break
            
            if eval_result['should_answer']:
                logger.info(f"[V2] Evaluate决定: 可以回答")
                break
            else:
                logger.info(f"[V2] Evaluate决定: 继续迭代")
        
        # 检查是否因错误退出
        if context.status == "error":
            error_message = f"任务执行失败：连续出现{context.consecutive_errors}次错误"
            if context.last_error_message:
                error_message += f"，最后错误：{context.last_error_message}"
            
            logger.error(f"[V2] {error_message}")
            yield {
                'event': 'error',
                'data': {
                    'message': error_message,
                    'consecutive_errors': context.consecutive_errors,
                    'last_error': context.last_error_message
                }
            }
            return
        
        # 4. Generate Answer（流式）
        yield {'event': 'answer_start', 'data': {}}
        
        # 使用流式生成答案
        answer_chunks = []
        for chunk in self._generate_answer_stream(context):
            answer_chunks.append(chunk)
            # 发送答案片段事件
            yield {
                'event': 'answer_chunk',
                'data': {'chunk': chunk}
            }
        
        # 组合完整答案
        answer = ''.join(answer_chunks)
        context.final_answer = answer
        
        # 发送完整答案事件（保持兼容性）
        yield {'event': 'answer', 'data': {'answer': answer}}
        
        # 5. Final Evaluation
        final_eval = self._final_evaluate(context)
        context.final_evaluation = final_eval
        context.status = "done"
        
        yield {'event': 'evaluate', 'data': final_eval}
        
        # 6. Done
        yield {
            'event': 'done',
            'data': {
                'sources': self._extract_sources(context),
                'process_log': context.to_dict()
            }
        }
    
    def _plan(self, context: AgentContext) -> Dict[str, Any]:
        """
        【Plan】规划下一步行动
        
        根据当前上下文决定：
        1. 需要分解任务（多任务场景）
        2. 需要调用什么工具
        3. 还是已经可以回答
        """
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S 星期%w")
        context_summary = context.get_context_summary(for_planning=True)
        
        # 根据是否有知识库动态调整工具列表
        has_kb = bool(context.kb_ids)
        
        prompt = PromptTemplates.get_v2_plan_prompt(
            current_time=current_time,
            context_summary=context_summary,
            has_kb=has_kb
        )
        
        try:
            response = chat_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            
            # 解析JSON
            decision = self._parse_json_response(response)
            
            # 处理任务分解
            if decision.get('action') == 'decompose_tasks':
                self._decompose_tasks(context, decision)
                # 分解后，重新规划第一个任务
                logger.info(f"[V2] 任务分解完成，共{len(context.subtasks)}个子任务")
                # 选择第一个待处理任务
                pending = context.get_pending_subtasks()
                if pending:
                    first_task = pending[0]
                    first_task.status = "in_progress"
                    context.current_subtask_id = first_task.id
                    # 返回第一个任务的执行计划
                    decision = {
                        'action': first_task.required_tool or 'search',
                        'args': {'query': first_task.description, 'top_k': 5},
                        'reasoning': f"处理任务{first_task.id}: {first_task.description}"
                    }
            else:
                # 如果有子任务列表，需要跟踪当前正在处理哪个任务
                action = decision.get('action')
                if context.subtasks and action and action not in ['ready_to_answer', 'decompose_tasks']:
                    # 从pending任务中找到与当前action匹配的任务
                    pending_tasks = context.get_pending_subtasks()
                    for task in pending_tasks:
                        # 匹配工具类型或推理中包含任务描述
                        reasoning = decision.get('reasoning', '').lower()
                        if (task.required_tool == action or 
                            task.description.lower() in reasoning or
                            f"任务{task.id}" in reasoning):
                            task.status = "in_progress"
                            context.current_subtask_id = task.id
                            logger.info(f"[V2] 关联工具调用到任务{task.id}: {task.description}")
                            break
            
            # 更新plan
            if not context.plan:
                context.plan = decision.get('reasoning', '')
            
            return decision
            
        except Exception as e:
            logger.error(f"规划错误: {e}")
            return {
                'action': 'ready_to_answer',
                'args': {},
                'reasoning': f'规划出错，直接回答: {str(e)}'
            }
    
    def _decompose_tasks(self, context: AgentContext, decision: Dict[str, Any]):
        """分解任务"""
        subtasks_data = decision.get('subtasks', [])
        for task_data in subtasks_data:
            task_id = task_data.get('id', len(context.subtasks) + 1)
            description = task_data.get('description', '')
            tool = task_data.get('tool', None)
            context.add_subtask(description, tool)
    
    def _execute_tool(self, context: AgentContext, plan_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        【Tool Using】执行工具调用
        """
        # 兜底：如果LLM返回的JSON缺失action字段，默认ready_to_answer
        tool_name = plan_result.get('action', 'ready_to_answer')
        args = plan_result.get('args', {})
        query = args.get('query', context.user_query)
        
        # 检查工具调用次数限制
        if tool_name in ['search', 'web_search', 'python_code']:
            if not context.can_call_tool(tool_name):
                limit = context.tool_call_limits.get(tool_name, 0)
                error_msg = f"工具 {tool_name} 已达到调用上限（{limit}次）"
                logger.warning(f"[V2] {error_msg}")
                
                # 创建工具调用日志（标记为错误）
                error_result = {'error': error_msg, 'reached_limit': True}
                log = ToolCallLog(
                    tool=tool_name,
                    query=query,
                    args=args,
                    result_summary=error_msg,
                    full_result=error_result,
                    timestamp=time.time(),
                    execution_time=0.0,
                    subtask_id=context.current_subtask_id
                )
                context.add_tool_log(log)  # 这会触发错误计数
                
                # 记录到 IO 日志
                io_logger = get_io_logger()
                if io_logger.enabled:
                    io_logger.log_tool_call(
                        tool_name=tool_name,
                        tool_type=tool_name,
                        request_args={'query': query, **args},
                        response_data={'reached_limit': True},
                        duration=0.0,
                        error=error_msg
                    )
                
                return {
                    'summary': error_msg,
                    'error': error_msg,
                    'reached_limit': True
                }
        
        start_time = time.time()
        result = {}
        result_summary = ""
        
        try:
            if tool_name == 'search':
                # 知识库检索
                result = self._tool_kb_search(query, context.kb_ids, args)
                result_summary = f"检索到 {len(result.get('chunks', []))} 条相关文档"
                context.add_evidence('kb_retrieval', result)
                
            elif tool_name == 'web_search':
                # 网络搜索
                result = self._tool_web_search(query, args)
                result_summary = f"检索到 {len(result.get('results', []))} 条网络信息"
                context.add_evidence('web_search', result)
                
            elif tool_name == 'python_code':
                # Python代码执行
                result = self._tool_python_code(query, args)
                result_summary = f"代码执行完成: {result.get('output', '')[:50]}"
                context.add_evidence('python_execution', result)
                
            else:
                result_summary = f"未知工具: {tool_name}"
            
            # 增加工具调用次数
            if tool_name in ['search', 'web_search', 'python_code']:
                context.increment_tool_count(tool_name)
            
            # 标记当前子任务完成（仅在成功且有证据时）
            if context.current_subtask_id:
                # 判断工具是否成功执行并产生了有效证据
                has_evidence = False
                evidence_key = None
                is_tool_success = True  # 标记工具是否执行成功
                
                # 根据工具类型确定对应的证据key和成功条件
                tool_evidence_map = {
                    'search': 'kb_retrieval',
                    'web_search': 'web_search',
                    'python_code': 'python_execution'
                }
                expected_evidence_key = tool_evidence_map.get(tool_name)
                
                # 检查工具调用是否有错误
                if result.get('error'):
                    is_tool_success = False
                    logger.warning(f"[V2] 工具{tool_name}返回错误: {result.get('error')}")
                
                # 检查是否产生了有效证据（证据必须非空）
                if is_tool_success and expected_evidence_key and expected_evidence_key in context.evidence:
                    evidence_list = context.evidence[expected_evidence_key]
                    if evidence_list and len(evidence_list) > 0:
                        # 对不同工具类型进行额外验证
                        last_evidence = evidence_list[-1]  # 获取最后一条（当前调用的）证据
                        
                        if tool_name == 'search' or tool_name == 'web_search':
                            # 检查是否有实际的结果块
                            chunks = last_evidence.get('chunks') or last_evidence.get('results', [])
                            if chunks:
                                has_evidence = True
                                evidence_key = expected_evidence_key
                        elif tool_name == 'python_code':
                            # 检查是否有输出且无执行错误
                            output = last_evidence.get('output')
                            error = last_evidence.get('error')
                            if output is not None and not error:
                                has_evidence = True
                                evidence_key = expected_evidence_key
                
                if has_evidence:
                    context.mark_subtask_completed(context.current_subtask_id, evidence_key)
                    logger.info(f"[V2] 任务{context.current_subtask_id}已完成，证据类型: {evidence_key}")
                else:
                    # 标记为失败
                    task = context.get_subtask(context.current_subtask_id)
                    if task:
                        task.status = "failed"
                    reason = "无有效证据" if is_tool_success else f"工具错误: {result.get('error')}"
                    logger.warning(f"[V2] 任务{context.current_subtask_id}执行失败 - {reason}")
                
                # 保存子任务ID用于日志记录
                subtask_id_for_log = context.current_subtask_id
                # 重置当前任务ID
                context.current_subtask_id = None
            else:
                subtask_id_for_log = None
            
            # 记录工具调用到上下文
            execution_time = time.time() - start_time
            log = ToolCallLog(
                tool=tool_name,
                query=query,
                args=args,
                result_summary=result_summary,
                full_result=result,
                timestamp=time.time(),
                execution_time=execution_time,
                subtask_id=subtask_id_for_log  # 关联子任务
            )
            context.add_tool_log(log)
            
            # 记录工具调用到 IO 日志
            io_logger = get_io_logger()
            if io_logger.enabled:
                io_logger.log_tool_call(
                    tool_name=tool_name,
                    tool_type=tool_name,  # 类型与名称相同
                    request_args={'query': query, **args},
                    response_data=result,
                    duration=execution_time,
                    error=None
                )
            
            return {'summary': result_summary, **result}
            
        except Exception as e:
            logger.error(f"工具执行错误 {tool_name}: {e}")
            result_summary = f"执行失败: {str(e)}"
            execution_time = time.time() - start_time
            error_result = {'error': str(e)}
            
            log = ToolCallLog(
                tool=tool_name,
                query=query,
                args=args,
                result_summary=result_summary,
                full_result=error_result,
                timestamp=time.time(),
                execution_time=execution_time,
                subtask_id=context.current_subtask_id
            )
            context.add_tool_log(log)
            
            # 记录失败的工具调用到 IO 日志
            io_logger = get_io_logger()
            if io_logger.enabled:
                io_logger.log_tool_call(
                    tool_name=tool_name,
                    tool_type=tool_name,
                    request_args={'query': query, **args},
                    response_data=error_result,
                    duration=execution_time,
                    error=str(e)
                )
            
            # 标记任务为失败
            if context.current_subtask_id:
                task = context.get_subtask(context.current_subtask_id)
                if task:
                    task.status = "failed"
                logger.error(f"[V2] 任务{context.current_subtask_id}执行异常: {str(e)}")
                context.current_subtask_id = None
            
            return {'summary': result_summary, 'error': str(e)}
    
    def _evaluate(self, context: AgentContext) -> Dict[str, Any]:
        """
        【Evaluate】评估当前信息是否足以回答
        """
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S 星期%w")
        context_summary = context.get_context_summary(for_planning=False)
        evidence_detail = context.get_evidence_detail()
        
        prompt = PromptTemplates.get_v2_evaluate_prompt(
            current_time=current_time,
            query=context.user_query,
            context_summary=context_summary,
            evidence_detail=evidence_detail
        )
        
        try:
            logger.info(f"[V2 Evaluate] 调用LLM评估...")
            response = chat_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            logger.info(f"[V2 Evaluate] LLM响应: {response[:200]}")
            
            evaluation = self._parse_json_response(response)
            logger.info(f"[V2 Evaluate] 解析后: {evaluation}")
            
            # 确保包含必需的键
            if 'should_answer' not in evaluation:
                logger.warning(f"[V2 Evaluate] 缺少should_answer，原始响应: {response[:300]}")
                evaluation['should_answer'] = True  # 默认可以回答
            
            if 'reason' not in evaluation:
                evaluation['reason'] = '无理由说明'
            
            evaluation['timestamp'] = time.time()
            context.add_evaluation(evaluation)
            
            logger.info(f"[V2 Evaluate] 最终评估: should_answer={evaluation['should_answer']}")
            return evaluation
            
        except Exception as e:
            logger.error(f"[V2 Evaluate] 异常: {e}")
            import traceback
            traceback.print_exc()
            # 默认可以回答
            evaluation = {
                'should_answer': True,
                'reason': f'评估出错，默认生成答案: {str(e)}',
                'timestamp': time.time()
            }
            context.add_evaluation(evaluation)
            return evaluation
    
    def _generate_answer(self, context: AgentContext) -> str:
        """
        【Streaming Output】生成最终答案（非流式）
        """
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S 星期%w")
        evidence_detail = context.get_evidence_detail()
        
        prompt = PromptTemplates.get_v2_answer_prompt(
            current_time=current_time,
            query=context.user_query,
            evidence_detail=evidence_detail,
            conversation_history=context.conversation_history
        )
        
        try:
            answer = chat_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return answer
            
        except Exception as e:
            print(f"答案生成错误: {e}")
            return f"抱歉，生成答案时出错：{str(e)}"
    
    def _generate_answer_stream(self, context: AgentContext) -> Generator[str, None, None]:
        """
        【Streaming Output】生成最终答案（流式）
        逐字输出，支持 Markdown 和 LaTeX 渲染
        """
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S 星期%w")
        evidence_detail = context.get_evidence_detail()
        
        prompt = PromptTemplates.get_v2_answer_prompt(
            current_time=current_time,
            query=context.user_query,
            evidence_detail=evidence_detail,
            conversation_history=context.conversation_history
        )
        
        try:
            # 使用流式生成器
            for chunk in chat_client.chat_stream_generator(
                [{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3
            ):
                if chunk:
                    yield chunk
                    
        except Exception as e:
            logger.error(f"流式答案生成错误: {e}")
            yield f"\n\n抱歉，生成答案时出错：{str(e)}"
    
    def _final_evaluate(self, context: AgentContext) -> Dict[str, Any]:
        """
        【Finish】最终评估答案质量
        增强版：传入上下文摘要，评估信息来源完整性
        """
        if not context.final_answer:
            return {'confidence': 0.0, 'reason': '没有生成答案'}
        
        # 生成上下文摘要用于评估
        context_summary = context.get_context_summary(for_planning=False)
        
        prompt = PromptTemplates.get_v2_final_evaluate_prompt(
            query=context.user_query,
            answer=context.final_answer,
            has_evidence=len(context.evidence) > 0,
            context_summary=context_summary  # 传入上下文
        )
        
        try:
            response = chat_client.chat(
                [{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            
            evaluation = self._parse_json_response(response)
            return evaluation
            
        except Exception as e:
            logger.error(f"最终评估错误: {e}")
            return {'confidence': 0.5, 'reason': f'评估出错: {str(e)}'}
    
    # ============ 工具实现 ============
    
    def _tool_kb_search(self, query: str, kb_ids: List[int], args: Dict[str, Any]) -> Dict[str, Any]:
        """知识库检索工具"""
        top_k = args.get('top_k', 5)
        
        if not kb_ids:
            return {'chunks': [], 'message': '没有选择知识库'}
        
        # 使用tool_registry的execute_tool方法执行工具
        tool_result = tool_registry.execute_tool('vector_search', {
            'query': query,
            'kb_ids': kb_ids,
            'top_k': top_k
        })
        
        if not tool_result.success:
            return {'chunks': [], 'message': f'检索失败: {tool_result.error}'}
        
        # tool_result.data 可能是列表或字典，需要兼容处理
        result_data = tool_result.data
        if isinstance(result_data, list):
            # 如果是列表，直接作为chunks
            chunks = result_data
        elif isinstance(result_data, dict):
            # 如果是字典，提取chunks
            chunks = result_data.get('chunks', [])
        else:
            chunks = []
        
        return {
            'chunks': chunks,
            'search_results': chunks  # 兼容前端
        }
    
    def _tool_web_search(self, query: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """网络搜索工具（增强错误处理）"""
        top_k = args.get('top_k', 5)
        
        try:
            # 使用百度搜索客户端
            result = baidu_search_client.search(query, top_k=top_k)
            
            # 检查搜索是否成功
            if not result.get('success', True):
                error_msg = result.get('error', '网络搜索服务不可用')
                logger.warning(f"网络搜索失败: {error_msg}")
                return {
                    'results': [],
                    'web_search_results': [],
                    'error': error_msg,
                    'success': False
                }
            
            results = result.get('results', [])
            
            # 如果没有结果，添加提示
            if not results:
                logger.info(f"网络搜索未找到结果: query={query}")
                return {
                    'results': [],
                    'web_search_results': [],
                    'message': '未找到相关网络搜索结果',
                    'success': True
                }
            
            return {
                'results': results,
                'web_search_results': results,  # 兼容前端
                'success': True
            }
            
        except Exception as e:
            error_msg = f'网络搜索异常: {str(e)}'
            logger.error(error_msg)
            return {
                'results': [],
                'web_search_results': [],
                'error': error_msg,
                'success': False
            }
    
    def _tool_python_code(self, query: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Python代码执行工具"""
        # 获取上传文件目录
        from app.routes.file_upload import get_upload_folder
        upload_dir = get_upload_folder()
        
        # 列出可用文件
        import os
        available_files = []
        try:
            for filename in os.listdir(upload_dir):
                if filename.endswith(('.csv', '.xlsx')) and not filename.startswith('.'):
                    available_files.append(filename)
        except:
            pass
        
        # 生成代码（添加安全指南和文件信息）
        files_info = ""
        if available_files:
            files_info = f"\n\n【可用文件】\n已上传的数据文件（位于 upload_dir 目录）：\n"
            for f in available_files:
                files_info += f"- {f}\n"
            files_info += f"\n📁 **访问方式**：\n"
            files_info += f"- upload_dir 变量已预先定义，指向上传文件目录\n"
            files_info += f"- pandas 模块已导入（使用 pandas 而不是 pd）\n"
            files_info += f"- 使用方式：`df = pandas.read_csv(os.path.join(upload_dir, '文件名.csv'))`\n"
            files_info += f"- 或简写：`df = pandas.read_csv(upload_dir + '/文件名.csv')`\n"
            files_info += f"- 注意：不要使用 import 语句，所有模块已预先导入\n"
        
        code_prompt = PromptTemplates.get_python_code_generation_prompt(query) + files_info
        # 在prompt中添加安全指南
        safe_guidelines = security_checker.get_safe_code_generation_guidelines()
        enhanced_prompt = f"{safe_guidelines}\n\n{code_prompt}"
        
        code = chat_client.chat(
            [{"role": "user", "content": enhanced_prompt}],
            temperature=0.1
        )
        
        # 【第2层安全防护】验证生成的代码是否安全
        is_safe, reason = security_checker.validate_generated_code(code)
        if not is_safe:
            logger.warning(f"[V2] 代码生成被拒绝: {reason}")
            return {
                'code': code,
                'output': '',
                'error': f"{reason}\n\n由于安全策略限制，无法执行该代码。请修改任务需求，避免使用被禁止的函数或模块。",
                'python_output': '',
                'python_code': code
            }
        
        # 执行代码（使用executor factory中的沙箱执行器，传入upload_dir）
        exec_result = execute_python_code(code, context={'upload_dir': upload_dir})
        
        return {
            'code': code,
            'output': exec_result.get('output', ''),
            'error': exec_result.get('error'),
            'python_output': exec_result.get('output', ''),  # 兼容前端
            'python_code': code  # 兼容前端
        }
    
    def _extract_sources(self, context: AgentContext) -> List[Dict[str, Any]]:
        """提取来源信息"""
        sources = []
        
        # 从知识库检索证据中提取
        if 'kb_retrieval' in context.evidence:
            for item in context.evidence['kb_retrieval']:
                for chunk in item.get('chunks', []):
                    sources.append({
                        'type': 'knowledge_base',
                        'content': chunk.get('text', ''),
                        'score': chunk.get('score', 0),
                        'metadata': chunk.get('metadata', {})
                    })
        
        # 从网络搜索证据中提取
        if 'web_search' in context.evidence:
            for item in context.evidence['web_search']:
                for result in item.get('results', []):
                    sources.append({
                        'type': 'web_search',
                        'title': result.get('title', ''),
                        'content': result.get('content', ''),
                        'url': result.get('url', ''),
                        'metadata': {
                            'source': 'web_search',
                            'url': result.get('url', '')
                        }
                    })
        
        # 从Python代码执行证据中提取（如果有）
        if 'python_execution' in context.evidence:
            for item in context.evidence['python_execution']:
                sources.append({
                    'type': 'code_execution',
                    'code': item.get('code', ''),
                    'output': item.get('output', ''),
                    'metadata': {
                        'source': 'python_executor'
                    }
                })
        
        return sources
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应（更稳健的JSON提取）"""
        import re
        
        # 尝试直接解析
        try:
            return json.loads(response.strip())
        except:
            pass
        
        # 尝试提取JSON（非贪婪模式，从第一个{到第一个匹配的}）
        # 使用非贪婪模式避免截取多余内容
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # 尝试更复杂的JSON提取：使用栈匹配平衡的大括号
        try:
            start_idx = response.find('{')
            if start_idx != -1:
                brace_count = 0
                for i in range(start_idx, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # 找到匹配的右括号
                            json_str = response[start_idx:i+1]
                            return json.loads(json_str)
        except:
            pass
        
        # 解析失败，返回默认（兜底机制）
        return {
            'action': 'ready_to_answer',
            'args': {},
            'reasoning': '无法解析模型响应，默认直接回答'
        }


# 全局实例
v2_agent = V2Agent()

