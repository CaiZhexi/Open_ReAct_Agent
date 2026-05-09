"""安全检查模块 - 识别和拦截危险请求"""
import re
from typing import Dict, List, Tuple


class SecurityChecker:
    """安全检查器 - 在请求执行前识别危险操作"""
    
    # 危险关键词模式
    DANGEROUS_PATTERNS = [
        # 系统敏感文件
        (r'/etc/passwd', '尝试访问系统密码文件'),
        (r'/etc/shadow', '尝试访问系统密码影子文件'),
        (r'/etc/hosts', '尝试访问系统hosts文件'),
        (r'/etc/.*', '尝试访问系统配置文件'),
        (r'~/\.ssh', '尝试访问SSH密钥'),
        (r'\.ssh/id_rsa', '尝试访问SSH私钥'),
        
        # 路径逃逸
        (r'\.\./\.\./\.\./.*', '尝试路径逃逸攻击'),
        (r'\.\.[\\/]\.\.[\\/]', '尝试目录穿越'),
        
        # 危险模块和函数
        (r'\bsubprocess\b', '尝试使用subprocess模块执行系统命令'),
        (r'\bos\.system\b', '尝试使用os.system执行系统命令'),
        (r'\bexec\s*\(', '尝试使用exec执行动态代码'),
        (r'\beval\s*\(', '尝试使用eval执行动态代码'),
        (r'\b__import__\s*\(', '尝试动态导入模块'),
        (r'\bcompile\s*\(', '尝试编译动态代码'),
        
        # 系统命令
        (r'\brm\s+-rf\b', '尝试删除文件（rm -rf）'),
        (r'\bchmod\b.*777', '尝试修改文件权限'),
        (r'\bsudo\b', '尝试使用管理员权限'),
        (r'\bcurl\b.*\|\s*bash', '尝试下载并执行远程脚本'),
        (r'\bwget\b.*\|\s*sh', '尝试下载并执行远程脚本'),
        
        # 网络相关
        (r'\bsocket\b', '尝试使用socket进行网络操作'),
        (r'\burllib\b', '尝试进行网络请求'),
        (r'\brequests\b', '尝试进行HTTP请求'),
        
        # 文件系统危险操作
        (r'读取.*密码', '尝试读取密码相关信息'),
        (r'查看.*密码', '尝试查看密码'),
        (r'获取.*密码', '尝试获取密码'),
        (r'读取.*私钥', '尝试读取私钥'),
        (r'删除.*文件', '尝试删除文件（中文）'),
    ]
    
    # 高危操作关键词（中文）
    # 说明：仅保留明确指向"系统管理/密码/密钥"的短语，
    # 移除"配置文件/密钥/ssh/用户账户/进程列表"等泛用词以降低正常问答的误报率。
    # 真正的拦截仍由 DANGEROUS_PATTERNS、AST 审计和沙箱执行层负责。
    DANGEROUS_KEYWORDS_CN = [
        '系统密码', '系统私钥', 'ssh 私钥',
        '系统命令执行', '修改系统权限', '提升权限',
        '远程执行', '下载并执行脚本',
        '系统用户列表', '查看系统用户', '获取系统用户',
        '系统进程列表', '系统服务列表'
    ]
    
    @classmethod
    def check_request_safety(cls, user_query: str) -> Tuple[bool, str]:
        """检查用户请求是否安全
        
        Args:
            user_query: 用户输入的问题
            
        Returns:
            (is_safe, reason): 是否安全，如果不安全则返回原因
        """
        # 转换为小写便于匹配
        query_lower = user_query.lower()
        
        # 检查危险模式
        for pattern, description in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, user_query, re.IGNORECASE):
                return False, f"🛡️ 安全拒绝：{description}"
        
        # 检查中文危险关键词
        for keyword in cls.DANGEROUS_KEYWORDS_CN:
            if keyword in user_query:
                return False, f"🛡️ 安全拒绝：检测到潜在危险操作（{keyword}）"
        
        return True, ""
    
    @classmethod
    def get_safe_code_generation_guidelines(cls) -> str:
        """获取代码生成安全指南"""
        return """
【重要安全规则】
你正在为一个受限的沙箱环境生成Python代码。必须遵守以下规则：

🚫 严格禁止：
1. 不得导入 subprocess, os.system, commands 等系统命令模块
2. 不得使用 exec(), eval(), compile(), __import__() 等动态执行函数
3. 不得尝试访问系统文件（如 /etc/passwd, /etc/hosts 等）
4. 不得使用路径逃逸（如 ../../../）
5. 不得导入网络相关模块（socket, urllib, requests）

✅ 允许使用：
- 数学计算：math, numpy, scipy
- 数据处理：pandas, json, collections
- 统计分析：statistics, statsmodels
- 字符串操作：re, string
- 日期时间：datetime
- 文件访问：可以使用 pandas.read_csv(), pandas.read_excel() 读取数据文件

📁 文件访问说明：
- 如果上下文中提供了 upload_dir 变量，你可以使用 pandas 读取该目录中的 CSV/XLSX 文件
- 使用 os.path.join(upload_dir, 'filename.csv') 构建文件路径
- 示例: df = pandas.read_csv(os.path.join(upload_dir, 'data.csv'))
- 注意：pandas 模块已预先导入，直接使用 pandas（不是 pd），不要写 import 语句
- 不要使用 open() 直接读取文件，使用 pandas 的读取函数

🔍 安全优先：
- 只访问 upload_dir 中的文件，不要访问系统文件
- 优先使用纯计算和数据处理的方式
- 避免任何可能的副作用
"""
    
    @classmethod
    def validate_generated_code(cls, code: str) -> Tuple[bool, str]:
        """验证生成的代码是否安全
        
        Args:
            code: 生成的Python代码
            
        Returns:
            (is_safe, reason): 是否安全，如果不安全则返回原因
        """
        # 检查禁用的函数（注意：open() 现在在沙箱中是允许的，由沙箱限制访问范围）
        forbidden_patterns = [
            (r'\bexec\s*\(', 'exec()'),
            (r'\beval\s*\(', 'eval()'),
            (r'\bcompile\s*\(', 'compile()'),
            (r'\b__import__\s*\(', '__import__()'),
            (r'\bsubprocess\b', 'subprocess模块'),
            (r'\bos\.system\b', 'os.system()'),
        ]
        
        for pattern, func_name in forbidden_patterns:
            if re.search(pattern, code):
                return False, f"🛡️ 代码生成被拒绝：尝试使用被禁止的{func_name}"
        
        # 检查危险导入
        forbidden_imports = [
            'subprocess', 'os.system', 'commands', 'socket',
            'urllib', 'requests', 'httplib', 'http.client'
        ]
        
        import_pattern = r'^\s*import\s+(\w+)|^\s*from\s+(\w+)\s+import'
        for line in code.split('\n'):
            match = re.search(import_pattern, line)
            if match:
                module = match.group(1) or match.group(2)
                if module in forbidden_imports:
                    return False, f"🛡️ 代码生成被拒绝：尝试导入被禁止的模块 {module}"
        
        return True, ""


# 全局实例
security_checker = SecurityChecker()

