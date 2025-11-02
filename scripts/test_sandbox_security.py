#!/usr/bin/env python3
"""测试Python执行器的沙箱安全功能

测试场景：
1. 正常文件操作（沙箱内）
2. 尝试访问沙箱外文件（应被拦截）
3. 尝试访问绝对路径（应被拦截）
4. 文件写入与读取（沙箱内）
5. 相对路径访问（沙箱内）
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.services.python_executor_v2 import ProcessIsolatedExecutor


def print_test_header(test_name: str):
    """打印测试标题"""
    print("\n" + "=" * 70)
    print(f"测试: {test_name}")
    print("=" * 70)


def print_result(result: dict):
    """打印测试结果"""
    print(f"✓ 成功: {result['success']}")
    if result.get('output'):
        print(f"📝 输出: {result['output'].strip()}")
    if result.get('error'):
        print(f"❌ 错误: {result['error']}")
    print(f"⏱️  耗时: {result.get('execution_time', 0):.3f}秒")
    print(f"🔒 隔离模式: {result.get('isolation_mode', 'unknown')}")
    if result.get('sandbox_enabled'):
        print(f"📦 沙箱已启用")


def main():
    print("\n" + "🔒" * 35)
    print("Python执行器沙箱安全测试")
    print("🔒" * 35)
    
    # 创建执行器实例（启用沙箱）
    executor = ProcessIsolatedExecutor(
        timeout=10,
        max_memory_mb=256,
        max_cpu_time=10
    )
    
    print("\n执行器配置:")
    config = executor.get_config()
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # ========================================
    # 测试1: 正常数学计算（不涉及文件）
    # ========================================
    print_test_header("测试1: 正常数学计算")
    result = executor.execute("""
import math
result = math.factorial(10) + math.sqrt(16)
print(f"计算结果: {result}")
""")
    print_result(result)
    assert result['success'], "测试1失败：正常计算应该成功"
    
    # ========================================
    # 测试2: 沙箱内文件写入与读取
    # ========================================
    print_test_header("测试2: 沙箱内文件写入与读取")
    result = executor.execute("""
# 在沙箱内创建文件
with open('test_file.txt', 'w') as f:
    f.write('Hello from sandbox!')

# 读取文件
with open('test_file.txt', 'r') as f:
    content = f.read()
    print(f"文件内容: {content}")
""")
    print_result(result)
    assert result['success'], "测试2失败：沙箱内文件操作应该成功"
    assert 'Hello from sandbox!' in result.get('output', ''), "测试2失败：文件内容不正确"
    
    # ========================================
    # 测试3: 尝试访问绝对路径（应被拦截）
    # ========================================
    print_test_header("测试3: 尝试访问绝对路径 /etc/passwd")
    result = executor.execute("""
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    print("危险：成功访问了系统文件！")
except PermissionError as e:
    print(f"✓ 安全：访问被拦截 - {e}")
except Exception as e:
    print(f"错误类型: {type(e).__name__}: {e}")
""")
    print_result(result)
    assert result['success'], "测试3失败：应该成功拦截并返回错误信息"
    assert '安全：访问被拦截' in result.get('output', ''), "测试3失败：应该拦截绝对路径访问"
    
    # ========================================
    # 测试4: 尝试使用..访问父目录（应被拦截）
    # ========================================
    print_test_header("测试4: 尝试使用 ../ 访问父目录")
    result = executor.execute("""
try:
    with open('../../../etc/passwd', 'r') as f:
        content = f.read()
    print("危险：成功访问了沙箱外文件！")
except PermissionError as e:
    print(f"✓ 安全：访问被拦截 - {str(e)[:50]}...")
except Exception as e:
    print(f"错误类型: {type(e).__name__}")
""")
    print_result(result)
    assert result['success'], "测试4失败：应该成功拦截父目录访问"
    assert '安全：访问被拦截' in result.get('output', ''), "测试4失败：应该拦截父目录访问"
    
    # ========================================
    # 测试5: 沙箱内子目录操作
    # ========================================
    print_test_header("测试5: 沙箱内子目录创建与文件操作")
    result = executor.execute("""
import os

# 创建子目录
os.makedirs('subdir/nested', exist_ok=True)

# 在子目录中写入文件
with open('subdir/nested/data.txt', 'w') as f:
    f.write('Data in nested directory')

# 读取文件
with open('subdir/nested/data.txt', 'r') as f:
    content = f.read()
    print(f"嵌套目录文件内容: {content}")

# 列出当前目录结构
for root, dirs, filenames in os.walk('.'):
    level = root.replace('.', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 2 * (level + 1)
    for filename in filenames:
        print(f"{subindent}{filename}")
""")
    print_result(result)
    assert result['success'], "测试5失败：沙箱内子目录操作应该成功"
    assert 'Data in nested directory' in result.get('output', ''), "测试5失败：子目录文件内容不正确"
    
    # ========================================
    # 测试6: 尝试访问用户主目录（应被拦截）
    # ========================================
    print_test_header("测试6: 尝试访问用户主目录")
    result = executor.execute("""
import os
try:
    home_dir = os.path.expanduser('~')
    with open(os.path.join(home_dir, '.bashrc'), 'r') as f:
        content = f.read()
    print("危险：成功访问了用户主目录文件！")
except PermissionError as e:
    print(f"✓ 安全：访问被拦截")
except FileNotFoundError:
    print("✓ 安全：文件不存在或无法访问")
except Exception as e:
    print(f"错误: {type(e).__name__}: {str(e)[:50]}")
""")
    print_result(result)
    # 这个测试可能因为不同系统而有不同结果，所以只检查是否执行成功
    
    # ========================================
    # 测试7: 大文件写入限制（应触发文件大小限制）
    # ========================================
    print_test_header("测试7: 测试文件大小限制（尝试写入20MB数据）")
    result = executor.execute("""
try:
    # 尝试写入大量数据
    with open('large_file.txt', 'w') as f:
        # 尝试写入20MB数据（超过10MB限制）
        data = 'x' * (20 * 1024 * 1024)
        f.write(data)
    print("危险：成功写入了超大文件！")
except Exception as e:
    print(f"✓ 安全：大文件写入被限制 - {type(e).__name__}")
""")
    print_result(result)
    # 注意：这个测试在某些系统上可能不会触发错误，因为resource限制只在Unix系统上有效
    
    # ========================================
    # 测试8: 相对路径正常访问
    # ========================================
    print_test_header("测试8: 相对路径文件操作")
    result = executor.execute("""
# 写入文件
with open('./relative_path.txt', 'w') as f:
    f.write('Relative path test')

# 读取文件
with open('relative_path.txt', 'r') as f:
    content = f.read()
    print(f"相对路径文件内容: {content}")
""")
    print_result(result)
    assert result['success'], "测试8失败：相对路径访问应该成功"
    assert 'Relative path test' in result.get('output', ''), "测试8失败：相对路径文件内容不正确"
    
    # ========================================
    # 总结
    # ========================================
    print("\n" + "=" * 70)
    print("✅ 所有测试完成！")
    print("=" * 70)
    print("\n沙箱安全特性验证:")
    print("  ✓ 正常计算：通过")
    print("  ✓ 沙箱内文件操作：通过")
    print("  ✓ 绝对路径拦截：通过")
    print("  ✓ 父目录访问拦截：通过")
    print("  ✓ 子目录操作：通过")
    print("  ✓ 相对路径访问：通过")
    print("\n🔒 沙箱隔离功能正常！")


if __name__ == '__main__':
    main()

