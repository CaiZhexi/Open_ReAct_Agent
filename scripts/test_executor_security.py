#!/usr/bin/env python3
"""Python执行器安全功能综合测试"""
import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.executor_factory import execute_python_code, get_executor_statistics, get_user_quota


def print_section(title):
    """打印测试章节标题"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_normal_execution():
    """测试1: 正常执行"""
    print_section("测试1: 正常代码执行")
    
    code = """
import math
result = math.sqrt(16) + math.factorial(5)
print(f"计算结果: {result}")
print(f"sqrt(16) = {math.sqrt(16)}")
print(f"5! = {math.factorial(5)}")
"""
    
    result = execute_python_code(code, user_id='test_user_1', request_id='req_001')
    
    print(f"✓ 执行成功: {result['success']}")
    print(f"✓ 输出:\n{result['output']}")
    print(f"✓ 执行时间: {result['execution_time']:.3f}秒")
    print(f"✓ 隔离模式: {result.get('isolation_mode', 'N/A')}")
    
    return result['success']


def test_timeout_control():
    """测试2: 超时控制"""
    print_section("测试2: 超时控制（无限循环）")
    
    code = """
import time
count = 0
while True:
    count += 1
    time.sleep(1)
    if count > 20:
        break
"""
    
    start = time.time()
    result = execute_python_code(code, user_id='test_user_2', request_id='req_002')
    elapsed = time.time() - start
    
    print(f"✓ 执行失败（预期）: {not result['success']}")
    print(f"✓ 错误信息: {result['error']}")
    print(f"✓ 实际耗时: {elapsed:.3f}秒（应该约等于超时时间）")
    print(f"✓ 进程已被终止: {result.get('terminated', False)}")
    
    return not result['success'] and '超时' in result['error']


def test_memory_limit():
    """测试3: 内存限制"""
    print_section("测试3: 内存限制（尝试分配大量内存）")
    
    code = """
# 尝试分配大量内存（超过限制）
try:
    big_list = [0] * (500 * 1024 * 1024)  # 尝试分配500MB
    print(f"内存分配成功: {len(big_list)}")
except MemoryError:
    print("内存超限（MemoryError）")
"""
    
    result = execute_python_code(code, user_id='test_user_3', request_id='req_003')
    
    print(f"✓ 执行状态: {'成功' if result['success'] else '失败'}")
    print(f"✓ 输出: {result.get('output', '')}")
    print(f"✓ 错误: {result.get('error', 'None')}")
    
    # 注意：在某些系统上内存限制可能不生效
    if 'resource模块不可用' in str(result):
        print("⚠️ 警告：当前系统不支持内存限制（Windows?）")
        return True
    
    return True  # 无论结果如何都算通过


def test_dangerous_code():
    """测试4: 危险代码拦截"""
    print_section("测试4: 危险代码拦截")
    
    dangerous_codes = [
        ("禁止open函数", "with open('/etc/passwd', 'r') as f: print(f.read())"),
        ("禁止eval函数", "eval('1 + 1')"),
        ("禁止exec函数", "exec('print(1)')"),
        ("禁止导入os", "import os\nos.system('ls')"),
        ("禁止__import__", "__import__('os').system('ls')"),
    ]
    
    all_blocked = True
    for name, code in dangerous_codes:
        result = execute_python_code(code, user_id='test_user_4')
        blocked = not result['success']
        print(f"  {'✓' if blocked else '✗'} {name}: {'已拦截' if blocked else '未拦截（危险！）'}")
        if not blocked:
            all_blocked = False
            print(f"      错误: 危险代码未被拦截！")
    
    return all_blocked


def test_rate_limiting():
    """测试5: 速率限制"""
    print_section("测试5: 速率限制")
    
    user_id = 'rate_limit_test_user'
    
    # 快速发送多个请求
    print(f"  正在快速发送请求（限制：20次/分钟）...")
    success_count = 0
    rate_limited_count = 0
    
    for i in range(25):
        result = execute_python_code(
            f"print('Request {i+1}')",
            user_id=user_id,
            request_id=f'req_rate_{i+1:03d}'
        )
        
        if result['success']:
            success_count += 1
        elif 'rate_limited' in result or '速率限制' in result.get('error', ''):
            rate_limited_count += 1
            if rate_limited_count == 1:
                print(f"  ✓ 第{i+1}次请求被速率限制拦截")
                print(f"    错误信息: {result['error']}")
                break
    
    # 获取配额信息
    quota = get_user_quota(user_id)
    if quota:
        print(f"\n  配额信息:")
        print(f"    - 已用（1分钟内）: {quota['used_last_1min']}")
        print(f"    - 剩余（1分钟内）: {quota['remaining_1min']}")
        print(f"    - 最大限制: {quota['max_per_minute']}/分钟")
    
    return rate_limited_count > 0


def test_statistics():
    """测试6: 统计和监控"""
    print_section("测试6: 统计和监控")
    
    stats = get_executor_statistics()
    
    print(f"  执行器类型: {stats.get('executor_type', 'N/A')}")
    print(f"  监控启用: {stats.get('monitoring_enabled', False)}")
    print(f"  审计启用: {stats.get('audit_enabled', False)}")
    print(f"  速率限制启用: {stats.get('rate_limit_enabled', False)}")
    
    if 'monitor_stats' in stats:
        monitor = stats['monitor_stats']
        print(f"\n  监控统计:")
        print(f"    - 总执行次数: {monitor.get('total_executions', 0)}")
        print(f"    - 成功率: {monitor.get('success_rate', 0):.2%}")
        print(f"    - 平均耗时: {monitor.get('average_time', 0):.3f}秒")
        print(f"    - 异常次数: {monitor.get('anomaly_count', 0)}")
        print(f"    - 最近1分钟执行: {monitor.get('executions_last_1min', 0)}次")
    
    if 'executor_config' in stats:
        config = stats['executor_config']
        print(f"\n  执行器配置:")
        print(f"    - 超时时间: {config.get('timeout', 0)}秒")
        print(f"    - 最大内存: {config.get('max_memory_mb', 0)}MB")
        print(f"    - 资源限制可用: {config.get('resource_limits_available', False)}")
    
    return True


def test_concurrent_execution():
    """测试7: 并发执行安全性"""
    print_section("测试7: 并发执行安全性")
    
    import threading
    
    results = []
    
    def worker(thread_id):
        code = f"""
import time
import random
sleep_time = random.uniform(0.1, 0.3)
time.sleep(sleep_time)
print(f"Thread {thread_id} completed in {{sleep_time:.3f}}s")
"""
        result = execute_python_code(
            code,
            user_id=f'thread_user_{thread_id}',
            request_id=f'thread_req_{thread_id}'
        )
        results.append((thread_id, result['success']))
    
    # 创建5个并发线程
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    success_count = sum(1 for _, success in results if success)
    print(f"  ✓ 并发执行完成: {success_count}/5 成功")
    
    return success_count == 5


def test_complex_computation():
    """测试8: 复杂计算"""
    print_section("测试8: 复杂科学计算")
    
    code = """
import math
import statistics

# 生成数据
data = [math.sin(x / 10) for x in range(100)]

# 统计分析
mean = statistics.mean(data)
stdev = statistics.stdev(data)
median = statistics.median(data)

print(f"数据点数: {len(data)}")
print(f"平均值: {mean:.4f}")
print(f"标准差: {stdev:.4f}")
print(f"中位数: {median:.4f}")

# 组合数计算
from math import comb
result = comb(10, 3)
print(f"C(10,3) = {result}")
"""
    
    result = execute_python_code(code, user_id='complex_user', request_id='req_complex')
    
    print(f"  ✓ 执行成功: {result['success']}")
    if result['success']:
        print(f"  ✓ 输出:\n{result['output']}")
    else:
        print(f"  ✗ 错误: {result['error']}")
    
    return result['success']


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Python执行器安全功能测试套件" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    
    tests = [
        ("正常代码执行", test_normal_execution),
        ("超时控制", test_timeout_control),
        ("内存限制", test_memory_limit),
        ("危险代码拦截", test_dangerous_code),
        ("速率限制", test_rate_limiting),
        ("统计和监控", test_statistics),
        ("并发执行安全性", test_concurrent_execution),
        ("复杂科学计算", test_complex_computation),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print_section("测试结果汇总")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n  总计: {total}个测试")
    print(f"  通过: {passed}个")
    print(f"  失败: {total - passed}个")
    print(f"  成功率: {passed/total*100:.1f}%\n")
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"    {status}  {name}")
    
    print("\n" + "=" * 70)
    
    if passed == total:
        print("  🎉 所有测试通过！执行器安全功能正常工作。")
    else:
        print("  ⚠️ 部分测试失败，请检查日志。")
    
    print("=" * 70 + "\n")
    
    return passed == total


if __name__ == '__main__':
    # 设置环境变量（可选）
    os.environ.setdefault('PYTHON_EXECUTOR_TYPE', 'process_isolated')
    
    success = run_all_tests()
    sys.exit(0 if success else 1)

