"""
运行 V2 Agent 并启用完整的 IO 日志记录
"""
import sys
from datetime import datetime
from app.services.io_logger import enable_io_logging, disable_io_logging, get_logger
from app.services.v2_agent import V2Agent, AgentContext
from app.services import api_clients
from app.services.api_clients_with_logging import (
    chat_client_with_logging,
    embedding_client_with_logging,
    rerank_client_with_logging,
    search_client_with_logging
)


def run_with_logging(query: str, kb_ids: list = None, kb_names: dict = None):
    """运行 Agent 并记录所有 IO"""
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/io_trace_{timestamp}.jsonl"
    
    # 启用日志记录
    enable_io_logging(log_file)
    
    try:
        # 替换全局客户端为带日志的版本
        original_chat_client = api_clients.chat_client
        api_clients.chat_client = chat_client_with_logging
        
        # 重新导入 v2_agent 模块以使用新的客户端
        import importlib
        from app.services import v2_agent as v2_agent_module
        importlib.reload(v2_agent_module)
        
        print(f"\n{'='*80}")
        print(f"开始运行查询: {query}")
        print(f"日志文件: {log_file}")
        print(f"{'='*80}\n")
        
        # 创建 Agent 并运行
        agent = v2_agent_module.V2Agent()
        
        # 使用非流式方式运行
        result = agent.run(query, kb_ids, kb_names)
        
        print(f"\n{'='*80}")
        print("执行完成")
        print(f"{'='*80}")
        print(f"\n最终答案:\n{result['answer']}\n")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"理由: {result['confidence_reason']}")
        
        # 恢复原始客户端
        api_clients.chat_client = original_chat_client
        
        return result
        
    finally:
        # 禁用日志记录并输出统计
        disable_io_logging()
        logger = get_logger()
        print(logger.get_summary())
        
        print(f"\n💡 查看详细日志:")
        print(f"   cat {log_file}")
        print(f"\n💡 分析日志:")
        print(f"   python analyze_io_log.py {log_file}")


if __name__ == '__main__':
    # 测试查询
    test_queries = [
        "100的阶乘是多少？",
        "今天佛山天气怎么样？",
        "100的阶乘是多少？今天佛山天气怎么样？",  # 多任务
        "计算 sqrt(256) + log(100) 的值",
    ]
    
    # 选择测试查询
    query_index = 0 if len(sys.argv) <= 1 else int(sys.argv[1])
    if query_index >= len(test_queries):
        query_index = 0
    
    query = test_queries[query_index]
    
    print(f"\n使用测试查询 #{query_index}: {query}\n")
    
    # 运行
    result = run_with_logging(query)

