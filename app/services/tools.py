"""工具注册和管理模块"""
import time
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class ToolCategory(Enum):
    """工具类别"""
    RETRIEVAL = "retrieval"  # 检索工具
    RERANK = "rerank"  # 重排工具
    EVALUATION = "evaluation"  # 评估工具
    GENERATION = "generation"  # 生成工具
    ANALYSIS = "analysis"  # 分析工具
    WEB_SEARCH = "web_search"  # 网络搜索工具
    CODE_EXECUTION = "code_execution"  # 代码执行工具


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'execution_time': self.execution_time,
            'metadata': self.metadata
        }


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory
    handler: Callable
    required_args: List[str]
    optional_args: List[str] = field(default_factory=list)
    max_retry: int = 0
    timeout: int = 30  # 超时时间（秒）
    enabled: bool = True
    
    def validate_args(self, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """验证参数"""
        # 检查必需参数
        missing_args = [arg for arg in self.required_args if arg not in args]
        if missing_args:
            return False, f"缺少必需参数: {', '.join(missing_args)}"
        
        return True, None
    
    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """执行工具"""
        # 验证参数
        valid, error_msg = self.validate_args(args)
        if not valid:
            return ToolResult(success=False, error=error_msg)
        
        # 执行工具
        start_time = time.time()
        try:
            result = self.handler(**args)
            execution_time = time.time() - start_time
            
            return ToolResult(
                success=True,
                data=result,
                execution_time=execution_time,
                metadata={
                    'tool_name': self.name,
                    'category': self.category.value
                }
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                metadata={
                    'tool_name': self.name,
                    'category': self.category.value
                }
            )


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
    
    def register(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        handler: Callable,
        required_args: List[str],
        optional_args: List[str] = None,
        max_retry: int = 0,
        timeout: int = 30,
        enabled: bool = True
    ) -> None:
        """注册工具"""
        tool = Tool(
            name=name,
            description=description,
            category=category,
            handler=handler,
            required_args=required_args,
            optional_args=optional_args or [],
            max_retry=max_retry,
            timeout=timeout,
            enabled=enabled
        )
        
        self._tools[name] = tool
        self._execution_stats[name] = {
            'total_calls': 0,
            'success_calls': 0,
            'failed_calls': 0,
            'total_execution_time': 0.0,
            'last_called': None
        }
        
        print(f"工具已注册: {name} ({category.value})")
    
    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            del self._execution_stats[name]
            print(f"工具已注销: {name}")
            return True
        return False
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """列出工具"""
        tools = []
        for name, tool in self._tools.items():
            # 过滤类别
            if category and tool.category != category:
                continue
            
            # 过滤启用状态
            if enabled_only and not tool.enabled:
                continue
            
            tools.append({
                'name': name,
                'description': tool.description,
                'category': tool.category.value,
                'required_args': tool.required_args,
                'optional_args': tool.optional_args,
                'enabled': tool.enabled
            })
        
        return tools
    
    def execute_tool(self, name: str, args: Dict[str, Any]) -> ToolResult:
        """执行工具"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(success=False, error=f"工具不存在: {name}")
        
        if not tool.enabled:
            return ToolResult(success=False, error=f"工具已禁用: {name}")
        
        # 更新统计
        self._execution_stats[name]['total_calls'] += 1
        self._execution_stats[name]['last_called'] = time.time()
        
        # 执行工具
        result = tool.execute(args)
        
        # 更新统计
        if result.success:
            self._execution_stats[name]['success_calls'] += 1
        else:
            self._execution_stats[name]['failed_calls'] += 1
        
        self._execution_stats[name]['total_execution_time'] += result.execution_time
        
        return result
    
    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        if name:
            return self._execution_stats.get(name, {})
        return self._execution_stats.copy()
    
    def enable_tool(self, name: str) -> bool:
        """启用工具"""
        tool = self.get_tool(name)
        if tool:
            tool.enabled = True
            return True
        return False
    
    def disable_tool(self, name: str) -> bool:
        """禁用工具"""
        tool = self.get_tool(name)
        if tool:
            tool.enabled = False
            return True
        return False
    
    def clear_stats(self) -> None:
        """清除统计信息"""
        for name in self._execution_stats:
            self._execution_stats[name] = {
                'total_calls': 0,
                'success_calls': 0,
                'failed_calls': 0,
                'total_execution_time': 0.0,
                'last_called': None
            }


# 全局工具注册表实例
tool_registry = ToolRegistry()
