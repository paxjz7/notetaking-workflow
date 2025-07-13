#!/usr/bin/env python3
"""
AI研究工作流测试脚本
用于测试各个模块的功能
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock
from config import Config
from llm_client import LLMClient, ResearchWorkflow
from search_client import SearchManager, SearchResult

class MockTest:
    """模拟测试类，用于在没有真实API的情况下测试程序逻辑"""
    
    def __init__(self):
        self.config = Config()
    
    async def test_llm_client(self):
        """测试LLM客户端"""
        print("🧪 测试LLM客户端...")
        
        # 模拟OpenAI响应
        mock_response = """1. 核心概念：机器学习算法
2. 历史：1950年代起源
3. 现状：广泛应用于各行业
4. 技术基础：数学统计和计算机科学
5. 应用：图像识别、自然语言处理
6. 争议：数据隐私和算法偏见
7. 未来：AGI和更强大的AI系统
8. 人物：图灵、麦卡锡、辛顿
9. 交叉领域和影响：心理学、神经科学、经济学"""
        
        client = LLMClient()
        
        # 模拟聊天完成
        if hasattr(client, 'client') and client.client:
            print("✅ OpenAI客户端初始化成功")
        else:
            print("⚠️  OpenAI客户端未配置，使用模拟数据")
        
        return mock_response
    
    async def test_workflow(self):
        """测试研究工作流"""
        print("🧪 测试研究工作流...")
        
        workflow = ResearchWorkflow()
        
        # 模拟工作流步骤
        keyword = "人工智能"
        mock_content = """1. 核心概念：机器学习和深度学习
2. 历史：从1950年代的图灵测试开始
3. 现状：AI技术快速发展，应用广泛
4. 技术基础：神经网络、大数据、云计算
5. 应用：自动驾驶、医疗诊断、金融分析
6. 争议：就业替代、隐私安全、算法偏见
7. 未来：通用人工智能、人机协作
8. 人物：图灵、麦卡锡、辛顿、李飞飞
9. 交叉领域和影响：认知科学、伦理学、社会学"""
        
        # 提取搜索查询
        search_queries = workflow.extract_search_queries(mock_content)
        print(f"✅ 提取到 {len(search_queries)} 个搜索查询")
        
        for i, query in enumerate(search_queries[:3], 1):
            print(f"  {i}. {query}")
        
        return mock_content, search_queries
    
    async def test_search_manager(self):
        """测试搜索管理器"""
        print("🧪 测试搜索管理器...")
        
        manager = SearchManager()
        
        # 模拟搜索结果
        mock_results = {
            "机器学习": {
                "web": [
                    SearchResult(
                        title="机器学习入门指南",
                        url="https://example.com/ml-guide",
                        snippet="机器学习是人工智能的核心分支...",
                        source="duckduckgo"
                    ),
                    SearchResult(
                        title="机器学习算法详解",
                        url="https://example.com/ml-algorithms",
                        snippet="常见的机器学习算法包括...",
                        source="duckduckgo"
                    )
                ],
                "pubmed": [
                    SearchResult(
                        title="Machine Learning in Healthcare",
                        url="https://pubmed.ncbi.nlm.nih.gov/12345",
                        snippet="Machine learning applications in medical diagnosis...",
                        source="pubmed"
                    )
                ]
            }
        }
        
        # 测试结果格式化
        formatted = manager.format_search_results(mock_results)
        print("✅ 搜索结果格式化成功")
        print(f"格式化结果长度: {len(formatted)} 字符")
        
        return mock_results
    
    async def run_mock_workflow(self):
        """运行模拟工作流"""
        print("🚀 运行模拟工作流测试...")
        print("=" * 50)
        
        # 测试各个组件
        llm_result = await self.test_llm_client()
        print()
        
        workflow_result, queries = await self.test_workflow()
        print()
        
        search_result = await self.test_search_manager()
        print()
        
        print("=" * 50)
        print("✅ 所有模拟测试完成！")
        
        return {
            "llm_result": llm_result,
            "workflow_result": workflow_result,
            "search_queries": queries,
            "search_result": search_result
        }

async def test_config():
    """测试配置"""
    print("🧪 测试配置...")
    
    try:
        config = Config()
        print(f"OpenAI API密钥: {'已配置' if config.OPENAI_API_KEY else '未配置'}")
        print(f"本地LLM URL: {'已配置' if config.LOCAL_LLM_URL else '未配置'}")
        print(f"PubMed邮箱: {config.PUBMED_EMAIL}")
        print(f"搜索延迟: {config.SEARCH_DELAY}秒")
        print(f"最大搜索结果: {config.MAX_SEARCH_RESULTS}")
        
        # 验证配置
        config.validate()
        print("✅ 配置验证成功")
        
    except Exception as e:
        print(f"❌ 配置错误: {e}")
        return False
    
    return True

async def main():
    """主测试函数"""
    print("🧪 AI研究工作流测试")
    print("=" * 50)
    
    # 测试配置
    config_ok = await test_config()
    print()
    
    if not config_ok:
        print("❌ 配置测试失败，请检查.env文件")
        sys.exit(1)
    
    # 运行模拟测试
    mock_test = MockTest()
    results = await mock_test.run_mock_workflow()
    
    print("\n📊 测试结果摘要:")
    print(f"- LLM结果长度: {len(results['llm_result'])} 字符")
    print(f"- 工作流结果长度: {len(results['workflow_result'])} 字符")
    print(f"- 搜索查询数量: {len(results['search_queries'])}")
    print(f"- 搜索结果源数量: {len(results['search_result'])}")
    
    print("\n✅ 测试完成！程序结构正常。")
    print("💡 提示：运行真实测试请使用: python3 main.py \"测试关键词\"")

if __name__ == "__main__":
    asyncio.run(main())