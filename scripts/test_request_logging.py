#!/usr/bin/env python3
"""
测试按请求分组的日志记录
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.io_logger import enable_io_logging, disable_io_logging, get_logger
from app.services.v2_agent import v2_agent
from app.models.database import DatabaseManager

def main():
    print("=" * 80)
    print("测试按请求分组的日志记录")
    print("=" * 80)
    
    # 启用日志记录
    log_file = "logs/test_request_grouped.jsonl"
    enable_io_logging(log_file)
    
    # 获取logger
    io_logger = get_logger()
    
    # 获取知识库
    db_manager = DatabaseManager()
    all_kbs = db_manager.get_knowledge_bases()
    kb_ids = [kb['id'] for kb in all_kbs]
    kb_names = {kb['id']: kb['name'] for kb in all_kbs}
    
    # 测试请求1
    print("\n📝 请求 #1: 简单数学计算")
    query1 = "100的阶乘是多少？"
    request_id1 = io_logger.start_request(query1, metadata={'kb_ids': kb_ids})
    print(f"   Request ID: {request_id1}")
    
    result1 = v2_agent.run(query1, kb_ids, kb_names)
    io_logger.end_request(request_id1, result1)
    print(f"   ✅ 完成")
    
    # 测试请求2
    print("\n📝 请求 #2: 复合问题")
    query2 = "50!+100!=？【原神】向着太空出发什么时候播出？"
    request_id2 = io_logger.start_request(query2, metadata={'kb_ids': kb_ids})
    print(f"   Request ID: {request_id2}")
    
    result2 = v2_agent.run(query2, kb_ids, kb_names)
    io_logger.end_request(request_id2, result2)
    print(f"   ✅ 完成")
    
    # 禁用日志记录
    disable_io_logging()
    
    print("\n" + "=" * 80)
    print(f"✅ 测试完成！日志已保存到: {log_file}")
    print(f"💡 运行以下命令格式化日志:")
    print(f"   python scripts/format_io_logs.py {log_file}")
    print("=" * 80)

if __name__ == '__main__':
    main()

