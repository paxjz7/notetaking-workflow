"""
YouTube视频总结系统主程序
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout, 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="1 day",
    retention="7 days"
)

from .config import Config
from .youtube_processor import YouTubeProcessor
from .gemini_summarizer import GeminiSummarizer
from .obsidian_writer import ObsidianWriter

class YouTubeSummarySystem:
    """YouTube视频总结系统"""
    
    def __init__(self):
        """初始化系统组件"""
        try:
            # 验证配置
            Config.validate()
            Config.create_directories()
            
            # 初始化组件
            self.youtube_processor = YouTubeProcessor()
            self.gemini_summarizer = GeminiSummarizer()
            self.obsidian_writer = ObsidianWriter()
            
            logger.info("YouTube视频总结系统初始化完成")
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            raise
    
    async def process_query(self, query: str) -> bool:
        """
        处理搜索查询的完整流程
        
        Args:
            query: 搜索关键词
            
        Returns:
            是否处理成功
        """
        try:
            logger.info(f"开始处理查询: {query}")
            
            # 步骤1: 搜索和下载YouTube视频信息
            logger.info("步骤1: 搜索YouTube视频...")
            videos = await self.youtube_processor.process_videos(query)
            
            if not videos:
                logger.warning("未找到任何视频，停止处理")
                return False
            
            logger.info(f"成功获取 {len(videos)} 个视频信息")
            
            # 步骤2: 使用Gemini总结视频内容
            logger.info("步骤2: 使用Gemini总结视频...")
            summaries = await self.gemini_summarizer.summarize_videos(videos)
            
            if not summaries:
                logger.warning("未生成任何视频总结，停止处理")
                return False
            
            logger.info(f"成功生成 {len(summaries)} 个视频总结")
            
            # 步骤3: 在Obsidian中创建文档
            logger.info("步骤3: 在Obsidian中创建文档...")
            created_files = self.obsidian_writer.write_all_summaries(summaries)
            
            if not created_files:
                logger.warning("未创建任何文档")
                return False
            
            logger.success(f"成功创建 {len(created_files)} 个Obsidian文档")
            
            # 输出结果摘要
            self._print_summary(query, videos, summaries, created_files)
            
            return True
            
        except Exception as e:
            logger.error(f"处理查询时发生错误: {e}")
            return False
    
    def _print_summary(self, query, videos, summaries, created_files):
        """打印处理结果摘要"""
        logger.info("=" * 60)
        logger.info("处理完成摘要")
        logger.info("=" * 60)
        logger.info(f"搜索关键词: {query}")
        logger.info(f"找到视频数量: {len(videos)}")
        logger.info(f"成功总结数量: {len(summaries)}")
        logger.info(f"创建文档数量: {len(created_files)}")
        
        logger.info("\n视频列表:")
        for i, summary in enumerate(summaries, 1):
            logger.info(f"{i}. {summary.title} - {summary.channel}")
        
        logger.info(f"\n创建的文档:")
        for file_path in created_files:
            logger.info(f"- {file_path}")
        
        logger.info("=" * 60)

async def main():
    """主函数"""
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    # 检查命令行参数
    if len(sys.argv) != 2:
        logger.error("使用方法: python -m src.main <搜索关键词>")
        logger.error("示例: python -m src.main '人工智能教程'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    try:
        # 初始化系统
        system = YouTubeSummarySystem()
        
        # 处理查询
        success = await system.process_query(query)
        
        if success:
            logger.success("程序执行完成！")
            sys.exit(0)
        else:
            logger.error("程序执行失败！")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())