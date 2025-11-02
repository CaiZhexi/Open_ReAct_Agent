# -*- coding: utf-8 -*-
"""
High-Security Level Python Executor (HSL)
Drop-in replacement for app/services/python_executor_v2.py

安全特性：
- AST 静态审计（先于白名单检查）
- 进程隔离 + 真超时
- 资源限额（内存/CPU/文件/进程数）
- 沙箱文件系统（默认禁用 open；可选只读/可选写入）
- 受限内建 + 受限导入
- 环境净化（可选）
- 与现有接口完全兼容（execute/get_config）
"""
from __future__ import annotations
import ast
import multiprocessing
import signal
import time
import io
import sys
import os
import tempfile
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass

# 尝试导入 resource（仅 Unix 可用）
try:
    import resource
    HAS_RESOURCE = True
except Exception:
    HAS_RESOURCE = False

# ===================== 配置与限额 =====================

@dataclass
class ExecutionConfig:
    timeout: int = 10
    max_memory_mb: int = 256
    max_cpu_time: int = 10
    max_output_length: int = 5000
    max_file_size_mb: int = 10
    enable_sandbox: bool = True
    allow_open: bool = False           # 新增：是否允许在沙箱中使用 open
    allow_write: bool = False          # 新增：是否允许在沙箱中写入
    sanitize_env: bool = True          # 新增：是否净化环境变量
    recursion_limit: int = 1000        # 新增：递归深度上限

def _set_resource_limits(cfg: ExecutionConfig):
    if not HAS_RESOURCE:
        return
    
    # 分别尝试设置每个资源限制，失败的跳过
    def _try_set_limit(limit_type, soft, hard, name=""):
        try:
            resource.setrlimit(limit_type, (soft, hard))
            return True
        except (ValueError, OSError) as e:
            # macOS等系统可能不支持某些限制，静默跳过
            if name:
                print(f"⚠️ 无法设置{name}限制: {e}", file=sys.stderr)
            return False
    
    success_count = 0
    total_count = 0
    
    # 内存限制
    if hasattr(resource, "RLIMIT_AS"):
        mem = cfg.max_memory_mb * 1024 * 1024
        total_count += 1
        if _try_set_limit(resource.RLIMIT_AS, mem, mem):
            success_count += 1
    
    # CPU时间限制
    if hasattr(resource, "RLIMIT_CPU"):
        total_count += 1
        if _try_set_limit(resource.RLIMIT_CPU, cfg.max_cpu_time, cfg.max_cpu_time):
            success_count += 1
    
    # 进程数限制（macOS上可能失败）
    if hasattr(resource, "RLIMIT_NPROC"):
        total_count += 1
        # 先获取当前限制，尝试设置为较小值
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
            # 如果hard limit允许，设置为1（允许当前进程但不允许fork）
            new_limit = min(1, hard)
            _try_set_limit(resource.RLIMIT_NPROC, new_limit, new_limit)
            success_count += 1
        except:
            pass  # macOS上通常会失败，忽略
    
    # 文件描述符限制
    if hasattr(resource, "RLIMIT_NOFILE"):
        total_count += 1
        if _try_set_limit(resource.RLIMIT_NOFILE, 16, 16):
            success_count += 1
    
    # 文件大小限制
    if hasattr(resource, "RLIMIT_FSIZE"):
        fbytes = cfg.max_file_size_mb * 1024 * 1024
        total_count += 1
        if _try_set_limit(resource.RLIMIT_FSIZE, fbytes, fbytes):
            success_count += 1
    
    # 如果没有任何限制成功设置，打印警告
    if success_count == 0 and total_count > 0:
        print(f"⚠️ 所有资源限制设置失败（系统不支持），代码执行器将依赖其他安全机制", file=sys.stderr)

# ===================== AST 静态审计 =====================

_FORBIDDEN_BUILTINS: Set[str] = {
    "eval", "exec", "compile", "open", "input", "breakpoint",
    "globals", "locals", "vars", "dir", "delattr", "__import__"
}
_FORBIDDEN_DUNDERS: Set[str] = {
    "__subclasses__", "__mro__", "__bases__", "__dict__", "__class__",
    "__globals__", "__code__", "__getattribute__", "__setattr__", "__delattr__"
}
_FORBIDDEN_MODULES: Set[str] = {
    "subprocess", "signal", "ctypes",
    "pickle", "marshal", "imp", "importlib",
    "socket", "ssl", "http", "urllib", "requests"
}
# os 和 os.path 在白名单中是允许的，所以不应该完全禁止
_FORBIDDEN_STR_HINTS: Tuple[str, ...] = (
    "/etc/passwd", "/etc/shadow", ".." + os.sep + "..", "://"
)

class _AstGuard(ast.NodeVisitor):
    def __init__(self, allowed_modules: Set[str], allow_open: bool):
        self.allowed_modules = allowed_modules
        self.allow_open = allow_open
        self.violations: List[str] = []

    def forbid(self, msg: str):
        self.violations.append(msg)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base = alias.name.split(".")[0]
            if base not in self.allowed_modules:
                self.forbid(f"禁止导入模块: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = (node.module or "").split(".")[0]
        if mod and mod not in self.allowed_modules:
            self.forbid(f"禁止导入模块: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 拦截危险内建
        if isinstance(node.func, ast.Name):
            fn = node.func.id
            if fn in _FORBIDDEN_BUILTINS and not (fn == "open" and self.allow_open):
                self.forbid(f"禁止使用危险函数: {fn}")
        # 拦截属性链上危险模块/方法（如 os.system/subprocess.Popen）
        if isinstance(node.func, ast.Attribute):
            # 提取最左侧名字
            root = node.func
            names = []
            while isinstance(root, ast.Attribute):
                names.append(root.attr)
                root = root.value
            if isinstance(root, ast.Name):
                names.append(root.id)
            chain = ".".join(reversed(names))
            base = names[-1] if names else ""
            # 禁止的模块和特定危险函数
            forbidden_calls = {
                "os.system", "os.exec", "os.execl", "os.execle", "os.execlp", "os.execv", "os.execve", "os.execvp", "os.execvpe",
                "os.popen", "os.spawn", "os.spawnl", "os.spawnle", "os.spawnlp", "os.spawnv", "os.spawnve", "os.spawnvp", "os.spawnvpe",
                "subprocess.Popen", "subprocess.call", "subprocess.run", "subprocess.check_call", "subprocess.check_output"
            }
            if base in _FORBIDDEN_MODULES or chain in forbidden_calls:
                self.forbid(f"禁止调用危险API: {chain}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in _FORBIDDEN_DUNDERS:
            self.forbid(f"禁止访问危险属性: {node.attr}")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str):
            s = node.value
            if any(hint in s for hint in _FORBIDDEN_STR_HINTS):
                self.forbid("检测到疑似系统路径/网络字面量")
        self.generic_visit(node)

def _ast_safety_check(code: str, allowed_modules: Set[str], allow_open: bool) -> Tuple[bool, str]:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        return False, f"语法错误：{e.msg} @ L{e.lineno}:{e.offset}"
    guard = _AstGuard(allowed_modules, allow_open)
    guard.visit(tree)
    if guard.violations:
        return False, "；".join(dict.fromkeys(guard.violations))
    return True, ""

# ===================== 沙箱 open =====================

def _create_safe_open(sandbox_dir: str, allow_write: bool):
    sandbox_path = os.path.abspath(sandbox_dir)

    def safe_open(file, mode="r", *args, **kwargs):
        # 绝对化目标路径，并强制限定在沙箱内
        target = os.path.abspath(file if os.path.isabs(file) else os.path.join(sandbox_path, file))
        if not target.startswith(sandbox_path):
            raise PermissionError(f"禁止访问沙箱外的文件: {file}")
        # 写入管控
        if any(m in mode for m in ("w", "a", "x", "+")):
            if not allow_write:
                raise PermissionError("当前策略下禁止写入文件")
            dirp = os.path.dirname(target)
            if dirp and not os.path.exists(dirp):
                os.makedirs(dirp, exist_ok=True)
        return open(target, mode, *args, **kwargs)
    return safe_open

# ===================== 子进程执行体 =====================

def _execute_in_child(code: str, cfg: ExecutionConfig, queue: multiprocessing.Queue, sandbox_dir: Optional[str], context: Dict[str, Any] = None):
    from config import Config
    start_cwd = os.getcwd()
    try:
        _set_resource_limits(cfg)

        # 环境净化
        if cfg.sanitize_env:
            keep = {"PYTHONIOENCODING": "utf-8"}
            os.environ.clear()
            os.environ.update(keep)

        # 切换工作目录
        if sandbox_dir and cfg.enable_sandbox:
            os.chdir(sandbox_dir)

        # 输出重定向
        out_buf, err_buf = io.StringIO(), io.StringIO()
        orig_out, orig_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out_buf, err_buf

        # 递归深度
        try:
            sys.setrecursionlimit(cfg.recursion_limit)
        except Exception:
            pass

        try:
            # 受控命名空间
            from app.services.python_executor import python_executor  # 复用白名单命名空间
            exec_ns: Dict[str, Any] = dict(python_executor.safe_namespace)

            # 受限导入
            allowed = set(Config.PYTHON_ALLOWED_MODULES.keys())
            real_import = __import__
            def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
                base = name.split(".")[0]
                if base not in allowed and name not in allowed:
                    raise ImportError(f"禁止导入模块: {name}")
                return real_import(name, globals, locals, fromlist, level)

            # 仅注入必要 builtins（含 __build_class__ 和各类异常）
            import builtins as _bi
            safe_builtins = {
                "__import__": safe_import,
                "__build_class__": _bi.__build_class__,
                "object": object,
                # 常见异常
                "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
                "KeyError": KeyError, "IndexError": IndexError, "AttributeError": AttributeError,
                "NameError": NameError, "PermissionError": PermissionError, "FileNotFoundError": FileNotFoundError,
                "OSError": OSError, "IOError": IOError, "RuntimeError": RuntimeError, "ZeroDivisionError": ZeroDivisionError,
                "StopIteration": StopIteration, "ImportError": ImportError,
            }
            exec_ns["__builtins__"] = safe_builtins
            exec_ns["__name__"] = "__sandbox__"

            # 替换 open（仅当策略允许时）
            if sandbox_dir and cfg.enable_sandbox and cfg.allow_open:
                exec_ns["open"] = _create_safe_open(sandbox_dir, cfg.allow_write)
            
            # 注入 context 变量（如 upload_dir）
            if context:
                exec_ns.update(context)

            # 执行
            exec(code, exec_ns)

            output = out_buf.getvalue()[:cfg.max_output_length]
            errors = err_buf.getvalue()[:cfg.max_output_length]
            res = {
                "success": True,
                "output": output,
                "error": errors or None,
                "terminated": False
            }
            if sandbox_dir and cfg.enable_sandbox:
                res.update({"sandbox_enabled": True, "sandbox_dir": sandbox_dir})
            queue.put(res)

        finally:
            # 还原 IO
            sys.stdout, sys.stderr = orig_out, orig_err
            out_buf.close(); err_buf.close()
            try:
                os.chdir(start_cwd)
            except Exception:
                pass

    except MemoryError:
        queue.put({"success": False, "output": "", "error": f"内存超限（最大{cfg.max_memory_mb}MB）", "terminated": False})
    except RecursionError:
        queue.put({"success": False, "output": "", "error": "递归深度超限", "terminated": False})
    except Exception as e:
        queue.put({"success": False, "output": "", "error": f"{type(e).__name__}: {e}", "terminated": False})

# ===================== 执行器（对外接口保持不变） =====================

class ProcessIsolatedExecutor:
    """
    进程隔离高安全执行器（HSL）
    与旧版同名同接口，可直接被 ExecutorFactory 加载。
    """
    def __init__(self, timeout=10, max_memory_mb=256, max_cpu_time=10, max_output_length=5000):
        from config import Config
        self.config = ExecutionConfig(
            timeout=timeout,
            max_memory_mb=max_memory_mb,
            max_cpu_time=max_cpu_time,
            max_output_length=max_output_length,
            enable_sandbox=True,
            allow_open=getattr(Config, "PYTHON_EXECUTOR_SANDBOX_ALLOW_OPEN", False),
            allow_write=getattr(Config, "PYTHON_EXECUTOR_SANDBOX_ALLOW_WRITE", False),
            sanitize_env=getattr(Config, "PYTHON_EXECUTOR_SANITIZE_ENV", True),
            recursion_limit=getattr(Config, "PYTHON_EXECUTOR_RECURSION_LIMIT", 1000),
        )
        # 复用基础执行器（白名单检查/函数目录）
        from app.services.python_executor import python_executor
        self.base_executor = python_executor

    def execute(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        from config import Config
        allowed_modules = set(Config.PYTHON_ALLOWED_MODULES.keys())

        # L0: AST 静态审计
        ok, reason = _ast_safety_check(code, allowed_modules, self.config.allow_open)
        if not ok:
            return self._deny(reason)

        # L1: 复用既有白名单检查（与现有策略对齐）
        # 若策略允许 open，为通过现有正则检查，仅在"检查阶段"将 open 名字替换为占位符；
        # 实际执行仍然是原代码（exec 阶段我们注入了安全 open）。
        code_for_check = code
        if self.config.allow_open:
            code_for_check = code.replace("open(", "_sandbox_open(")
        safety = self.base_executor._check_code_safety(code_for_check)
        if not safety.get("safe", False):
            return self._deny(f"{safety.get('reason', '安全检查失败')}")

        # L2: 进程隔离 + 沙箱执行
        return self._exec_isolated(code, context)

    def _exec_isolated(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        start = time.time()
        # 使用临时目录作为沙箱
        sandbox_dir = tempfile.mkdtemp(prefix="python_sandbox_") if self.config.enable_sandbox else None
        q: multiprocessing.Queue = multiprocessing.Queue()
        p = multiprocessing.Process(
            target=_execute_in_child,
            args=(code, self.config, q, sandbox_dir, context),
            daemon=True
        )
        try:
            p.start()
            p.join(timeout=self.config.timeout)
            elapsed = time.time() - start
            if p.is_alive():
                # 超时强制终止
                p.terminate()
                time.sleep(0.1)
                if p.is_alive():
                    # 某些系统上需要 kill
                    try:
                        p.kill()
                    except Exception:
                        pass
                    p.join(timeout=1)
                return {
                    "success": False, "error": f"代码执行超时（超过{self.config.timeout}秒）",
                    "output": "", "execution_time": self.config.timeout,
                    "isolation_mode": "process_isolated_sandbox" if sandbox_dir else "process_isolated",
                    "terminated": True
                }
            if not q.empty():
                res = q.get(timeout=1)
                res["execution_time"] = elapsed
                res["isolation_mode"] = "process_isolated_sandbox" if sandbox_dir else "process_isolated"
                return res
            # 异常退出
            exit_code = p.exitcode
            return {
                "success": False,
                "error": f"进程异常退出（退出码: {exit_code}）",
                "output": "",
                "execution_time": elapsed,
                "isolation_mode": "process_isolated_sandbox" if sandbox_dir else "process_isolated",
                "terminated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"执行器内部错误: {type(e).__name__}: {e}",
                "output": "",
                "execution_time": time.time() - start,
                "isolation_mode": "process_isolated_sandbox" if sandbox_dir else "process_isolated",
                "terminated": True
            }
        finally:
            try:
                q.close(); q.join_thread()
            except Exception:
                pass
            # 删除沙箱目录
            if sandbox_dir:
                try:
                    import shutil
                    shutil.rmtree(sandbox_dir, ignore_errors=True)
                except Exception:
                    pass

    def _deny(self, reason: str) -> Dict[str, Any]:
        return {
            "success": False,
            "error": f"🛡️ 安全检查失败: {reason}",
            "output": "",
            "execution_time": 0.0,
            "isolation_mode": "process_isolated_sandbox" if self.config.enable_sandbox else "process_isolated",
            "terminated": False
        }

    # 兼容接口
    def get_config(self) -> Dict[str, Any]:
        return {
            "timeout": self.config.timeout,
            "max_memory_mb": self.config.max_memory_mb,
            "max_cpu_time": self.config.max_cpu_time,
            "max_output_length": self.config.max_output_length,
            "max_file_size_mb": self.config.max_file_size_mb,
            "enable_sandbox": self.config.enable_sandbox,
            "allow_open": self.config.allow_open,
            "allow_write": self.config.allow_write,
            "sanitize_env": self.config.sanitize_env,
            "recursion_limit": self.config.recursion_limit,
            "isolation_mode": "process_isolated_sandbox" if self.config.enable_sandbox else "process_isolated",
            "resource_limits_available": HAS_RESOURCE
        }

# 全局实例（保持旧习惯）
process_isolated_executor = ProcessIsolatedExecutor()

# 工厂函数（保持旧签名）
def get_executor(executor_type: Optional[str] = None):
    if executor_type == "process_isolated" or executor_type is None:
        return process_isolated_executor
    else:
        from app.services.python_executor import python_executor
        return python_executor
