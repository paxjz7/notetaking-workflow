#!/usr/bin/env python3
"""
YouTube视频总结系统使用示例
"""
import asyncio
import os
from pathlib import Path

# 添加项目根目录到Python路径
import sys
sys.path.append(str(Path(__file__).parent))

from src import YouTubeSummarySystem

async def main():
    """演示如何使用YouTube视频总结系统"""
    
    # 检查环境变量
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ 错误: 请先设置 GEMINI_API_KEY 环境变量")
        print("💡 提示: 在 .env 文件中添加您的Gemini API密钥")
        return
    
    if not os.getenv("OBSIDIAN_VAULT_PATH"):
        print("❌ 错误: 请先设置 OBSIDIAN_VAULT_PATH 环境变量")
        print("💡 提示: 在 .env 文件中添加您的Obsidian vault路径")
        return
    
    # 创建系统实例
    try:
        system = YouTubeSummarySystem()
        print("✅ 系统初始化成功")
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return
    
    # 示例查询列表
    example_queries = [
        "Python编程入门教程",
        "机器学习基础知识",
        "数据科学实战案例",
        "人工智能最新进展",
        "深度学习框架对比"
    ]
    
    print("\n📋 可用的示例查询:")
    for i, query in enumerate(example_queries, 1):
        print(f"  {i}. {query}")
    
    # 让用户选择查询
    print("\n" + "="*50)
    print("请选择一个查询进行演示:")
    print("1. 使用预设查询")
    print("2. 输入自定义查询")
    print("3. 退出")
    
    choice = input("\n请输入选择 (1-3): ").strip()
    
    if choice == "1":
        print("\n请选择预设查询:")
        for i, query in enumerate(example_queries, 1):
            print(f"  {i}. {query}")
        
        try:
            query_index = int(input(f"\n请输入数字 (1-{len(example_queries)}): ").strip()) - 1
            if 0 <= query_index < len(example_queries):
                selected_query = example_queries[query_index]
            else:
                print("❌ 无效选择，使用默认查询")
                selected_query = example_queries[0]
        except ValueError:
            print("❌ 无效输入，使用默认查询")
            selected_query = example_queries[0]
            
    elif choice == "2":
        selected_query = input("\n请输入您的搜索查询: ").strip()
        if not selected_query:
            print("❌ 查询不能为空，使用默认查询")
            selected_query = example_queries[0]
            
    elif choice == "3":
        print("👋 再见!")
        return
        
    else:
        print("❌ 无效选择，使用默认查询")
        selected_query = example_queries[0]
    
    # 执行查询
    print(f"\n🚀 开始处理查询: {selected_query}")
    print("⏳ 这可能需要几分钟时间，请耐心等待...")
    print("-" * 50)
    
    try:
        success = await system.process_query(selected_query)
        
        if success:
            print("\n🎉 处理完成！")
            print("📁 请检查您的Obsidian vault中的 'YouTube视频总结' 文件夹")
            print("🔗 文档已自动创建了相互链接")
        else:
            print("\n❌ 处理失败，请检查日志文件了解详情")
            
    except KeyboardInterrupt:
        print("\n⏹️ 处理被用户中断")
    except Exception as e:
        print(f"\n❌ 处理过程中发生错误: {e}")

if __name__ == "__main__":
    print("🎬 YouTube视频总结系统演示")
    print("=" * 50)
    
    # 检查配置文件
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  警告: 未找到 .env 文件")
        print("💡 请复制 .env.example 到 .env 并填写配置")
        print()
        
        create_env = input("是否创建示例 .env 文件? (y/N): ").strip().lower()
        if create_env in ['y', 'yes']:
            try:
                import shutil
                shutil.copy('.env.example', '.env')
                print("✅ 已创建 .env 文件，请编辑并填写您的配置")
                print("📝 需要设置:")
                print("   - GEMINI_API_KEY: 您的Gemini API密钥")
                print("   - OBSIDIAN_VAULT_PATH: 您的Obsidian vault路径")
                sys.exit(0)
            except Exception as e:
                print(f"❌ 创建 .env 文件失败: {e}")
                sys.exit(1)
    
    # 运行主程序
    asyncio.run(main())