"""Python代码安全执行器 - 白名单模式"""
import math
import statistics
import datetime
import json
import re
import random
from collections import Counter, defaultdict, OrderedDict, deque, namedtuple
from itertools import combinations, permutations, product, combinations_with_replacement, count, cycle, repeat, chain, islice, groupby, accumulate, compress, dropwhile, takewhile, filterfalse
from decimal import Decimal, getcontext
from fractions import Fraction
import time
import io
import sys
from typing import Dict, Any, List
from config import Config


class PythonExecutor:
    """
    安全的Python代码执行器 - 白名单模式
    
    ⚠️ 安全策略：
    1. 只允许执行白名单内的预定义函数
    2. 禁止所有import语句
    3. 禁止pip/uv等包管理器
    4. 在受限的命名空间中执行
    5. 不提供文件、网络、系统访问
    """
    
    def __init__(self, timeout: int = None, max_output_length: int = None):
        """
        初始化执行器
        
        Args:
            timeout: 执行超时时间（秒），默认从Config读取
            max_output_length: 最大输出长度，默认从Config读取
        """
        self.timeout = timeout or Config.PYTHON_EXECUTOR_TIMEOUT
        self.max_output_length = max_output_length or Config.PYTHON_EXECUTOR_MAX_OUTPUT
        self.max_code_length = Config.PYTHON_EXECUTOR_MAX_CODE_LENGTH
        
        # 构建白名单命名空间
        self.safe_namespace = self._build_safe_namespace()
    
    def _build_safe_namespace(self) -> Dict[str, Any]:
        """
        构建安全的白名单命名空间
        从Config读取配置，支持模块对象和单独函数两种方式
        """
        namespace = {}
        
        # 1. 添加内置函数（从Config读取）
        builtins_map = {
            'int': int, 'float': float, 'str': str, 'bool': bool,
            'list': list, 'tuple': tuple, 'dict': dict, 'set': set, 'frozenset': frozenset,
            'abs': abs, 'round': round, 'sum': sum, 'min': min, 'max': max, 
            'pow': pow, 'divmod': divmod,
            'len': len, 'range': range, 'enumerate': enumerate, 'zip': zip,
            'map': map, 'filter': filter, 'sorted': sorted, 'reversed': reversed,
            'all': all, 'any': any,
            'type': type, 'isinstance': isinstance, 'issubclass': issubclass,
            'hasattr': hasattr, 'getattr': getattr, 'setattr': setattr,
            'print': print, 'format': format, 'hex': hex, 'oct': oct, 'bin': bin,
            'ord': ord, 'chr': chr, 'callable': callable, 'hash': hash,
            'id': id, 'repr': repr, 'ascii': ascii
        }
        
        for builtin_name in Config.PYTHON_ALLOWED_BUILTINS:
            if builtin_name in builtins_map:
                namespace[builtin_name] = builtins_map[builtin_name]
        
        # 2. 添加模块（从Config读取）
        for module_name, allowed_attrs in Config.PYTHON_ALLOWED_MODULES.items():
            try:
                # 动态导入模块
                if '.' in module_name:
                    # 处理子模块，如 matplotlib.pyplot
                    parent_name = module_name.rsplit('.', 1)[0]
                    __import__(module_name)
                    module = sys.modules[module_name]
                else:
                    module = __import__(module_name)
                
                # 如果允许全部属性 (*)
                if allowed_attrs == ['*']:
                    namespace[module_name.split('.')[-1]] = module
                else:
                    # 方式1：暴露整个模块对象
                    namespace[module_name.split('.')[-1]] = module
                    
                    # 方式2：同时暴露单独的函数
                    for attr_name in allowed_attrs:
                        if hasattr(module, attr_name) and attr_name != module_name:
                            namespace[attr_name] = getattr(module, attr_name)
            
            except ImportError as e:
                # 如果模块未安装，跳过（不影响其他模块）
                print(f"⚠️ 模块 {module_name} 未安装，跳过: {e}")
                continue
        
        return namespace
    
    def execute(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        在白名单命名空间中安全执行Python代码
        
        Args:
            code: 要执行的Python代码（不允许import语句）
            context: 可选的上下文字典，会被注入到执行命名空间中（如 upload_dir）
            
        Returns:
            包含执行结果的字典
        """
        # 严格的安全检查
        safety_check = self._check_code_safety(code)
        if not safety_check['safe']:
            return {
                'success': False,
                'error': f"🛡️ 安全检查失败: {safety_check['reason']}",
                'output': '',
                'execution_time': 0
            }
        
        # 在受限命名空间中执行
        start_time = time.time()
        
        # 重定向输出
        stdout_buffer = io.StringIO()
        old_stdout = sys.stdout
        
        try:
            sys.stdout = stdout_buffer
            
            # 创建隔离的命名空间（深拷贝白名单）
            exec_namespace = dict(self.safe_namespace)
            
            # 注入上下文变量（如果有）
            if context:
                exec_namespace.update(context)
            
            # 创建受限的__import__函数（只允许导入白名单中的模块）
            original_import = __import__
            def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
                """受限的import函数，只允许导入白名单中的模块"""
                base_module = name.split('.')[0]
                allowed_modules = Config.PYTHON_ALLOWED_MODULES.keys()
                
                if base_module not in allowed_modules and name not in allowed_modules:
                    raise ImportError(f"禁止导入模块: {name}")
                
                # 使用内置的__import__
                return original_import(name, globals, locals, fromlist, level)
            
            # 添加受限的builtins
            exec_namespace['__import__'] = safe_import
            exec_namespace['__name__'] = '__main__'
            exec_namespace['__builtins__'] = {'__import__': safe_import}
            
            # 在受限命名空间中执行代码
            exec(code, exec_namespace)
            
            execution_time = time.time() - start_time
            output = stdout_buffer.getvalue()[:self.max_output_length]
            
            return {
                'success': True,
                'output': output,
                'error': None,
                'execution_time': execution_time
            }
            
        except TimeoutError:
            return {
                'success': False,
                'error': f'⏱️ 代码执行超时（超过{self.timeout}秒）',
                'output': stdout_buffer.getvalue()[:self.max_output_length],
                'execution_time': self.timeout
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'error': f'❌ 执行错误: {type(e).__name__}: {str(e)}',
                'output': stdout_buffer.getvalue()[:self.max_output_length],
                'execution_time': execution_time
            }
            
        finally:
            sys.stdout = old_stdout
            stdout_buffer.close()
    
    def _check_code_safety(self, code: str) -> Dict[str, Any]:
        """
        白名单模式的安全检查
        
        Args:
            code: 要检查的代码
            
        Returns:
            安全检查结果
        """
        # 检查代码长度
        if len(code) > self.max_code_length:
            return {
                'safe': False,
                'reason': f'代码长度超过限制（最大{self.max_code_length}字符）'
            }
        
        # 检查import语句（允许导入白名单中的模块）
        if 'import ' in code or 'from ' in code:
            # 提取所有import的模块名
            # 先匹配 from ... import ...，再匹配 import ...
            from_pattern = r'from\s+([\w.]+)\s+import'
            import_pattern = r'(?:^|;|\n)\s*import\s+([\w.]+(?:\s*,\s*[\w.]+)*)'
            
            from_imports = re.findall(from_pattern, code)
            standalone_imports = re.findall(import_pattern, code)
            
            # 获取白名单模块
            allowed_modules = set(Config.PYTHON_ALLOWED_MODULES.keys())
            
            # 检查 from xxx import yyy
            for from_module in from_imports:
                base_module = from_module.split('.')[0]
                if base_module not in allowed_modules and from_module not in allowed_modules:
                    return {
                        'safe': False,
                        'reason': f'禁止导入模块: {from_module}。仅允许导入：{", ".join(sorted(allowed_modules))}'
                    }
            
            # 检查 import xxx
            for import_modules in standalone_imports:
                for module in import_modules.split(','):
                    module = module.strip().split()[0]  # 移除 'as xxx'
                    base_module = module.split('.')[0]
                    if base_module not in allowed_modules and module not in allowed_modules:
                        return {
                            'safe': False,
                            'reason': f'禁止导入模块: {module}。仅允许导入：{", ".join(sorted(allowed_modules))}'
                        }
        
        # 禁止__开头的特殊方法（防止访问内部对象）
        # 但允许常见的双下划线语法如 __name__
        dangerous_dunders = ['__import__', '__builtins__', '__globals__', '__locals__',
                            '__code__', '__class__', '__base__', '__subclasses__']
        for dunder in dangerous_dunders:
            if dunder in code:
                return {
                    'safe': False,
                    'reason': f'禁止使用危险的魔术方法: {dunder}'
                }
        
        # 禁止eval/exec/compile等危险函数
        dangerous_builtins = ['eval', 'exec', 'compile', 
                             'open', 'file', 'input', 'raw_input',
                             'globals', 'locals', 'vars', 'dir', 'delattr']
        for builtin in dangerous_builtins:
            # 使用单词边界检查，避免误判（如 opened）
            if re.search(rf'\b{builtin}\b', code):
                return {
                    'safe': False,
                    'reason': f'禁止使用危险函数: {builtin}'
                }
        
        # 禁止pip/uv等包管理器
        package_managers = ['pip', 'pip3', 'uv', 'conda', 'poetry', 'pipenv']
        for pm in package_managers:
            if re.search(rf'\b{pm}\b', code.lower()):
                return {
                    'safe': False,
                    'reason': f'禁止使用包管理器: {pm}。不允许安装新依赖。'
                }
        
        return {'safe': True, 'reason': ''}
    
    def get_available_functions(self) -> Dict[str, List[str]]:
        """
        获取可用函数列表（用于向Agent展示）
        从Config动态读取
        
        Returns:
            按模块组织的可用函数列表
        """
        result = {}
        
        # 按模块组织
        module_chinese_names = {
            'math': '数学运算 (math模块)',
            'statistics': '统计分析 (statistics模块)',
            'random': '随机数生成 (random模块)',
            'datetime': '日期时间 (datetime模块)',
            'decimal': '高精度计算 (decimal模块)',
            'fractions': '分数运算 (fractions模块)',
            'collections': '数据结构 (collections模块)',
            'itertools': '迭代工具 (itertools模块)',
            're': '正则表达式 (re模块)',
            'json': 'JSON处理 (json模块)',
        }
        
        for module_name, functions in Config.PYTHON_ALLOWED_MODULES.items():
            chinese_name = module_chinese_names.get(module_name, module_name)
            # 添加模块使用说明
            func_list = [f"使用方式：{module_name}.{func}() 或直接 {func}()" for func in functions[:3]]
            func_list.extend([f"{func}" for func in functions[3:]])
            result[chinese_name] = func_list
        
        # 添加内置函数
        result["内置函数"] = [
            "类型转换: int(), float(), str(), bool(), list(), dict(), set()",
            "数学运算: abs(), round(), sum(), min(), max(), pow(), divmod()",
            "序列操作: len(), range(), enumerate(), zip(), sorted(), reversed()",
            "逻辑判断: all(), any(), isinstance(), hasattr()",
            "输出调试: print(), format(), repr()"
        ]
        
        return result


# 全局执行器实例
python_executor = PythonExecutor()
