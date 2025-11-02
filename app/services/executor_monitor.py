"""Python执行器监控、审计和速率限制"""
import time
import logging
import hashlib
import json
from collections import deque, defaultdict
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import threading


# ==================== 数据结构 ====================

@dataclass
class ExecutionRecord:
    """执行记录"""
    timestamp: float
    user_id: Optional[str]
    code_hash: str
    code_length: int
    success: bool
    execution_time: float
    error: Optional[str]
    isolation_mode: str
    memory_peak_mb: float = 0.0


# ==================== 执行监控器 ====================

class ExecutorMonitor:
    """执行器监控器
    
    功能：
    1. 记录执行历史
    2. 统计成功率、平均耗时
    3. 检测异常执行（超时、内存超限等）
    4. 提供实时监控数据
    """
    
    def __init__(self, max_history: int = 1000):
        """初始化监控器
        
        Args:
            max_history: 保留的最大历史记录数
        """
        self.max_history = max_history
        self.execution_history: deque[ExecutionRecord] = deque(maxlen=max_history)
        self.anomaly_count = 0
        self.total_executions = 0
        self.lock = threading.Lock()
        
        # 异常阈值
        self.slow_execution_threshold = 5.0  # 秒
        self.high_memory_threshold = 200  # MB
    
    def record_execution(
        self,
        result: Dict[str, Any],
        code: str,
        user_id: Optional[str] = None
    ):
        """记录执行结果
        
        Args:
            result: 执行结果字典
            code: 执行的代码
            user_id: 用户ID（可选）
        """
        with self.lock:
            # 计算代码哈希
            code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
            
            # 创建执行记录
            record = ExecutionRecord(
                timestamp=time.time(),
                user_id=user_id,
                code_hash=code_hash,
                code_length=len(code),
                success=result.get('success', False),
                execution_time=result.get('execution_time', 0.0),
                error=result.get('error'),
                isolation_mode=result.get('isolation_mode', 'unknown')
            )
            
            # 添加到历史记录
            self.execution_history.append(record)
            self.total_executions += 1
            
            # 异常检测
            self._detect_anomalies(record, code)
    
    def _detect_anomalies(self, record: ExecutionRecord, code: str):
        """检测异常执行"""
        # 检测慢执行
        if record.execution_time > self.slow_execution_threshold:
            self.anomaly_count += 1
            self._alert_slow_execution(record)
        
        # 检测失败
        if not record.success:
            self._alert_execution_failure(record, code)
    
    def _alert_slow_execution(self, record: ExecutionRecord):
        """告警：执行缓慢"""
        print(f"⚠️ 警告：代码执行缓慢 - {record.execution_time:.2f}秒 "
              f"(用户: {record.user_id}, 代码哈希: {record.code_hash})")
    
    def _alert_execution_failure(self, record: ExecutionRecord, code: str):
        """告警：执行失败"""
        # 只记录，不打印（避免日志过多）
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计数据字典
        """
        with self.lock:
            if not self.execution_history:
                return {
                    'total_executions': 0,
                    'success_rate': 0.0,
                    'average_time': 0.0,
                    'anomaly_count': 0,
                    'recent_history_size': 0
                }
            
            # 计算统计数据
            success_count = sum(1 for r in self.execution_history if r.success)
            total_time = sum(r.execution_time for r in self.execution_history)
            avg_time = total_time / len(self.execution_history) if self.execution_history else 0.0
            
            # 最近1分钟的执行次数
            now = time.time()
            recent_1min = sum(
                1 for r in self.execution_history
                if now - r.timestamp < 60
            )
            
            return {
                'total_executions': self.total_executions,
                'recent_history_size': len(self.execution_history),
                'success_rate': success_count / len(self.execution_history),
                'failure_rate': 1 - (success_count / len(self.execution_history)),
                'average_time': avg_time,
                'anomaly_count': self.anomaly_count,
                'executions_last_1min': recent_1min,
                'isolation_modes': self._get_isolation_mode_distribution()
            }
    
    def _get_isolation_mode_distribution(self) -> Dict[str, int]:
        """获取隔离模式分布"""
        distribution = defaultdict(int)
        for record in self.execution_history:
            distribution[record.isolation_mode] += 1
        return dict(distribution)
    
    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的失败记录
        
        Args:
            limit: 返回的最大记录数
            
        Returns:
            失败记录列表
        """
        with self.lock:
            failures = [
                asdict(record) for record in reversed(self.execution_history)
                if not record.success
            ]
            return failures[:limit]


# ==================== 审计日志 ====================

class ExecutorAuditLogger:
    """代码执行审计日志
    
    功能：
    1. 记录所有执行请求
    2. 记录失败的代码（用于安全审查）
    3. 记录异常行为
    4. 支持日志查询和分析
    """
    
    def __init__(self, log_dir: str = 'logs'):
        """初始化审计日志
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = log_dir
        
        # 创建logger
        self.logger = logging.getLogger('executor_audit')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件handler
            import os
            os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(
                f'{log_dir}/executor_audit.log',
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(file_handler)
            
            # 失败代码专用日志
            self.failure_logger = logging.getLogger('executor_failures')
            self.failure_logger.setLevel(logging.WARNING)
            
            failure_handler = logging.FileHandler(
                f'{log_dir}/executor_failures.log',
                encoding='utf-8'
            )
            failure_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.failure_logger.addHandler(failure_handler)
    
    def log_execution(
        self,
        code: str,
        result: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """记录执行日志
        
        Args:
            code: 执行的代码
            result: 执行结果
            user_id: 用户ID
            request_id: 请求ID
        """
        # 计算代码哈希
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        
        # 构建日志条目
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'user_id': user_id,
            'code_hash': code_hash,
            'code_length': len(code),
            'success': result.get('success', False),
            'execution_time': result.get('execution_time', 0.0),
            'isolation_mode': result.get('isolation_mode', 'unknown'),
            'error': result.get('error')
        }
        
        # 记录到审计日志
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
        
        # 如果失败，记录详细信息
        if not result.get('success', False):
            self._log_failure(code, result, user_id, code_hash)
    
    def _log_failure(
        self,
        code: str,
        result: Dict[str, Any],
        user_id: Optional[str],
        code_hash: str
    ):
        """记录失败的执行"""
        failure_entry = {
            'user_id': user_id,
            'code_hash': code_hash,
            'error': result.get('error'),
            'code_preview': code[:200] + ('...' if len(code) > 200 else '')
        }
        
        self.failure_logger.warning(json.dumps(failure_entry, ensure_ascii=False))
    
    def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        severity: str = 'WARNING'
    ):
        """记录安全事件
        
        Args:
            event_type: 事件类型（如：'rate_limit_exceeded', 'dangerous_code_blocked'）
            details: 事件详情
            severity: 严重程度（INFO, WARNING, ERROR）
        """
        event_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'details': details
        }
        
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method(f"SECURITY_EVENT | {json.dumps(event_entry, ensure_ascii=False)}")


# ==================== 速率限制器 ====================

class ExecutorRateLimiter:
    """执行速率限制器
    
    功能：
    1. 防止滥用（限制每个用户的执行频率）
    2. 保护系统资源
    3. 支持全局和用户级别的速率限制
    """
    
    def __init__(
        self,
        max_requests_per_minute: int = 20,
        max_requests_per_hour: int = 100,
        global_max_per_minute: int = 100
    ):
        """初始化速率限制器
        
        Args:
            max_requests_per_minute: 每用户每分钟最大请求数
            max_requests_per_hour: 每用户每小时最大请求数
            global_max_per_minute: 全局每分钟最大请求数
        """
        self.max_per_minute = max_requests_per_minute
        self.max_per_hour = max_requests_per_hour
        self.global_max_per_minute = global_max_per_minute
        
        # 用户请求记录
        self.user_requests: Dict[str, List[float]] = defaultdict(list)
        
        # 全局请求记录
        self.global_requests: List[float] = []
        
        self.lock = threading.Lock()
    
    def check_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """检查速率限制
        
        Args:
            user_id: 用户ID
            
        Returns:
            速率限制检查结果，包含：
            - allowed: 是否允许执行
            - reason: 拒绝原因（如果被拒绝）
            - remaining_quota: 剩余配额
        """
        with self.lock:
            now = time.time()
            
            # 清理过期记录
            self._cleanup_expired_requests(now)
            
            # 检查全局速率限制
            global_1min = self._count_recent_requests(self.global_requests, now, 60)
            if global_1min >= self.global_max_per_minute:
                return {
                    'allowed': False,
                    'reason': f'系统繁忙，请稍后再试（全局速率限制：{self.global_max_per_minute}次/分钟）',
                    'remaining_quota': 0
                }
            
            # 检查用户级别速率限制
            user_reqs = self.user_requests[user_id]
            
            # 1分钟内的请求数
            user_1min = self._count_recent_requests(user_reqs, now, 60)
            if user_1min >= self.max_per_minute:
                return {
                    'allowed': False,
                    'reason': f'请求过于频繁，请稍后再试（限制：{self.max_per_minute}次/分钟）',
                    'remaining_quota': 0
                }
            
            # 1小时内的请求数
            user_1hour = self._count_recent_requests(user_reqs, now, 3600)
            if user_1hour >= self.max_per_hour:
                return {
                    'allowed': False,
                    'reason': f'已达每小时请求上限（限制：{self.max_per_hour}次/小时）',
                    'remaining_quota': 0
                }
            
            # 允许执行，记录请求
            user_reqs.append(now)
            self.global_requests.append(now)
            
            # 计算剩余配额
            remaining = min(
                self.max_per_minute - user_1min - 1,
                self.max_per_hour - user_1hour - 1
            )
            
            return {
                'allowed': True,
                'reason': None,
                'remaining_quota': max(0, remaining)
            }
    
    def _cleanup_expired_requests(self, now: float):
        """清理过期的请求记录（1小时前）"""
        cutoff_time = now - 3600
        
        # 清理用户请求记录
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if req_time > cutoff_time
            ]
            # 删除空记录
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
        
        # 清理全局请求记录
        self.global_requests = [
            req_time for req_time in self.global_requests
            if req_time > cutoff_time
        ]
    
    def _count_recent_requests(
        self,
        requests: List[float],
        now: float,
        window: int
    ) -> int:
        """统计最近时间窗口内的请求数
        
        Args:
            requests: 请求时间列表
            now: 当前时间
            window: 时间窗口（秒）
            
        Returns:
            请求数
        """
        cutoff = now - window
        return sum(1 for req_time in requests if req_time > cutoff)
    
    def get_user_quota(self, user_id: str) -> Dict[str, int]:
        """获取用户的配额信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            配额信息字典
        """
        with self.lock:
            now = time.time()
            user_reqs = self.user_requests.get(user_id, [])
            
            # 统计最近的请求数
            count_1min = self._count_recent_requests(user_reqs, now, 60)
            count_1hour = self._count_recent_requests(user_reqs, now, 3600)
            
            return {
                'used_last_1min': count_1min,
                'remaining_1min': max(0, self.max_per_minute - count_1min),
                'used_last_1hour': count_1hour,
                'remaining_1hour': max(0, self.max_per_hour - count_1hour),
                'max_per_minute': self.max_per_minute,
                'max_per_hour': self.max_per_hour
            }


# ==================== 全局实例 ====================

# 监控器
executor_monitor = ExecutorMonitor(max_history=1000)

# 审计日志
executor_audit_logger = ExecutorAuditLogger()

# 速率限制器
executor_rate_limiter = ExecutorRateLimiter(
    max_requests_per_minute=20,
    max_requests_per_hour=100,
    global_max_per_minute=100
)


# ==================== 便捷函数 ====================

def record_execution(
    code: str,
    result: Dict[str, Any],
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
):
    """记录执行（监控 + 审计）
    
    Args:
        code: 执行的代码
        result: 执行结果
        user_id: 用户ID
        request_id: 请求ID
    """
    # 记录到监控器
    executor_monitor.record_execution(result, code, user_id)
    
    # 记录到审计日志
    executor_audit_logger.log_execution(code, result, user_id, request_id)


def check_rate_limit(user_id: str) -> Dict[str, Any]:
    """检查速率限制
    
    Args:
        user_id: 用户ID
        
    Returns:
        速率限制检查结果
    """
    return executor_rate_limiter.check_rate_limit(user_id)


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("测试监控器")
    print("=" * 60)
    
    # 模拟执行记录
    for i in range(10):
        result = {
            'success': i % 3 != 0,
            'execution_time': 0.1 * (i + 1),
            'error': f'测试错误 {i}' if i % 3 == 0 else None,
            'isolation_mode': 'process_isolated'
        }
        executor_monitor.record_execution(result, f'test code {i}', f'user_{i % 3}')
    
    # 获取统计信息
    stats = executor_monitor.get_statistics()
    print("\n统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试速率限制")
    print("=" * 60)
    
    user_id = 'test_user'
    
    # 尝试多次请求
    for i in range(25):
        result = check_rate_limit(user_id)
        if not result['allowed']:
            print(f"\n请求 {i+1}: 被拒绝 - {result['reason']}")
            break
        else:
            print(f"请求 {i+1}: 允许 (剩余配额: {result['remaining_quota']})")
        
        time.sleep(0.1)
    
    # 获取配额信息
    print("\n配额信息:")
    quota = executor_rate_limiter.get_user_quota(user_id)
    for key, value in quota.items():
        print(f"  {key}: {value}")

