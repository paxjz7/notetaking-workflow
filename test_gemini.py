#!/usr/bin/env python3
"""
Google Gemini API 测试脚本
用于验证Gemini API配置是否正确
"""

import asyncio
import sys
from config import Config
from llm_client import LLMClient

async def test_gemini_api():
    """测试Gemini API配置"""
    print("🧪 测试Google Gemini API配置...")
    print("=" * 50)
    
    try:
        # 检查配置
        config = Config()
        print(f"📋 配置检查:")
        print(f"  - Gemini API密钥: {'✅ 已配置' if config.GEMINI_API_KEY else '❌ 未配置'}")
        print(f"  - Gemini模型: {config.GEMINI_MODEL}")
        print()
        
        if not config.GEMINI_API_KEY:
            print("❌ 错误: 未配置GEMINI_API_KEY")
            print("请在.env文件中添加:")
            print("GEMINI_API_KEY=your_gemini_api_key_here")
            return False
        
        # 创建LLM客户端
        print("🔧 创建LLM客户端...")
        client = LLMClient()
        
        if not client.use_gemini:
            print("❌ 错误: Gemini客户端未初始化")
            return False
        
        print("✅ Gemini客户端初始化成功")
        print()
        
        # 测试简单对话
        print("💬 测试简单对话...")
        test_prompt = "请用一句话介绍什么是人工智能"
        
        response = await client.chat_completion(
            prompt=test_prompt,
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"📝 提示词: {test_prompt}")
        print(f"🤖 Gemini回应: {response}")
        print()
        
        # 检查响应是否有效
        if "API调用失败" in response:
            print("❌ API调用失败")
            return False
        
        print("✅ Gemini API测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("🚀 Google Gemini API 测试")
    print("=" * 50)
    
    success = await test_gemini_api()
    
    print("=" * 50)
    if success:
        print("✅ 测试完成！Gemini API配置正确。")
        print("💡 现在可以运行: python3 main.py \"人工智能\"")
    else:
        print("❌ 测试失败！请检查Gemini API配置。")
        print("📚 查看帮助文档: GEMINI_QUICKSTART.md")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())