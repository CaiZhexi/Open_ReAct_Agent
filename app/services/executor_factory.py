"""Python执行器工厂和统一接口"""
from typing import Dict, Any, Optional
from config import Config


class ExecutorWrapper:
    """执行器包装器，统一管理监控、审计和速率限制"""
    
    def __init__(self):
        """初始化执行器包装器"""
        # 根据配置选择执行器
        self.executor_type = Config.PYTHON_EXECUTOR_TYPE
        self.executor = self._create_executor()
        
        # 可选功能模块
        self.monitor = None
        self.audit_logger = None
        self.rate_limiter = None
        
        # 根据配置启用功能
        self._initialize_optional_features()
    
    def _create_executor(self):
        """创建执行器实例"""
        if self.executor_type == 'process_isolated':
            from app.services.python_executor_v2 import ProcessIsolatedExecutor
            return ProcessIsolatedExecutor(
                timeout=Config.PYTHON_EXECUTOR_TIMEOUT,
                max_memory_mb=Config.PYTHON_EXECUTOR_MAX_MEMORY_MB,
                max_cpu_time=Config.PYTHON_EXECUTOR_MAX_CPU_TIME,
                max_output_length=Config.PYTHON_EXECUTOR_MAX_OUTPUT
            )
        else:
            # 默认执行器
            from app.services.python_executor import python_executor
            return python_executor
    
    def _initialize_optional_features(self):
        """初始化可选功能模块"""
        # 监控
        if Config.PYTHON_EXECUTOR_ENABLE_MONITORING:
            from app.services.executor_monitor import executor_monitor
            self.monitor = executor_monitor
        
        # 审计
        if Config.PYTHON_EXECUTOR_ENABLE_AUDIT:
            from app.services.executor_monitor import executor_audit_logger
            self.audit_logger = executor_audit_logger
        
        # 速率限制
        if Config.PYTHON_EXECUTOR_ENABLE_RATE_LIMIT:
            from app.services.executor_monitor import ExecutorRateLimiter
            self.rate_limiter = ExecutorRateLimiter(
                max_requests_per_minute=Config.PYTHON_EXECUTOR_RATE_LIMIT_PER_MINUTE,
                max_requests_per_hour=Config.PYTHON_EXECUTOR_RATE_LIMIT_PER_HOUR,
                global_max_per_minute=Config.PYTHON_EXECUTOR_GLOBAL_RATE_LIMIT
            )
    
    def execute(
        self,
        code: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行Python代码（带监控、审计和速率限制）
        
        Args:
            code: 要执行的Python代码
            user_id: 用户ID（用于速率限制和审计）
            request_id: 请求ID（用于审计）
            context: 可选的上下文字典（如 upload_dir）
            
        Returns:
            执行结果字典
        """
        # 1. 速率限制检查
        if self.rate_limiter and user_id:
            rate_check = self.rate_limiter.check_rate_limit(user_id)
            if not rate_check['allowed']:
                result = {
                    'success': False,
                    'error': f"速率限制: {rate_check['reason']}",
                    'output': '',
                    'execution_time': 0,
                    'rate_limited': True
                }
                
                # 记录安全事件
                if self.audit_logger:
                    self.audit_logger.log_security_event(
                        'rate_limit_exceeded',
                        {
                            'user_id': user_id,
                            'reason': rate_check['reason']
                        },
                        severity='WARNING'
                    )
                
                return result
        
        # 2. 执行代码（传入context）
        result = self.executor.execute(code, context=context)
        
        # 3. 监控记录
        if self.monitor:
            self.monitor.record_execution(result, code, user_id)
        
        # 4. 审计日志
        if self.audit_logger:
            self.audit_logger.log_execution(code, result, user_id, request_id)
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        stats = {
            'executor_type': self.executor_type,
            'monitoring_enabled': self.monitor is not None,
            'audit_enabled': self.audit_logger is not None,
            'rate_limit_enabled': self.rate_limiter is not None
        }
        
        # 添加监控统计
        if self.monitor:
            stats['monitor_stats'] = self.monitor.get_statistics()
        
        # 添加执行器配置
        if hasattr(self.executor, 'get_config'):
            stats['executor_config'] = self.executor.get_config()
        
        return stats
    
    def get_user_quota(self, user_id: str) -> Optional[Dict[str, int]]:
        """获取用户配额信息"""
        if self.rate_limiter:
            return self.rate_limiter.get_user_quota(user_id)
        return None
    
    def get_available_functions(self) -> Dict[str, Any]:
        """获取可用函数列表"""
        if hasattr(self.executor, 'get_available_functions'):
            return self.executor.get_available_functions()
        return {}


# 全局执行器实例
executor_wrapper = ExecutorWrapper()


# 便捷函数
def execute_python_code(
    code: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """执行Python代码（全局便捷函数）
    
    Args:
        code: 要执行的代码
        user_id: 用户ID
        request_id: 请求ID
        context: 可选的上下文字典（如 upload_dir）
        
    Returns:
        执行结果
    """
    return executor_wrapper.execute(code, user_id, request_id, context)


def get_executor_statistics() -> Dict[str, Any]:
    """获取执行器统计信息"""
    return executor_wrapper.get_statistics()


def get_user_quota(user_id: str) -> Optional[Dict[str, int]]:
    """获取用户配额"""
    return executor_wrapper.get_user_quota(user_id)


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("测试执行器工厂")
    print("=" * 60)
    
    # 测试执行
    print("\n测试1: 正常执行")
    result = execute_python_code("""
import math
result = math.sqrt(16)
print(f"sqrt(16) = {result}")
""", user_id='test_user_1')
    
    print(f"成功: {result['success']}")
    print(f"输出: {result['output']}")
    print(f"隔离模式: {result.get('isolation_mode', 'N/A')}")
    
    # 测试速率限制
    print("\n测试2: 速率限制")
    for i in range(25):
        result = execute_python_code(
            f"print('Request {i+1}')",
            user_id='test_user_2'
        )
        if not result['success']:
            print(f"请求 {i+1}: 失败 - {result['error']}")
            break
        print(f"请求 {i+1}: 成功")
    
    # 获取统计信息
    print("\n统计信息:")
    stats = get_executor_statistics()
    import json
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 获取用户配额
    print("\n用户配额:")
    quota = get_user_quota('test_user_2')
    if quota:
        print(json.dumps(quota, indent=2, ensure_ascii=False))

