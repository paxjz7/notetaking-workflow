"""
事件驱动系统简化测试
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from loguru import logger

# 配置简单的日志
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

class MockConfig:
    """模拟配置类"""
    OBSIDIAN_VAULT_PATH = "/workspace/test_vault"
    
    @classmethod
    def validate(cls):
        return True
    
    @classmethod
    def create_directories(cls):
        Path(cls.OBSIDIAN_VAULT_PATH).mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)

# 导入事件系统核心组件
from src.core.event_system import EventBus, Event, EventType
from src.core.workflow_engine import WorkflowEngine, YOUTUBE_SUMMARY_WORKFLOW

# 创建简化的处理器
class MockGeminiHandler:
    """模拟Gemini处理器"""
    
    def can_handle(self, event_type):
        return event_type == EventType.AI_PROCESSING_STARTED
    
    async def handle(self, event):
        """模拟AI处理"""
        logger.info("🤖 开始AI处理...")
        await asyncio.sleep(1)  # 模拟处理时间
        
        extracted_content = event.data.get('extracted_content', [])
        summaries = []
        
        for content in extracted_content:
            video_info = content.get('video_info', {})
            summary = {
                'title': video_info.get('title', 'Mock Title'),
                'url': video_info.get('url', 'Mock URL'),
                'channel': video_info.get('channel', 'Mock Channel'),
                'duration': video_info.get('duration', '10:00'),
                'upload_date': video_info.get('upload_date', '2024-01-01'),
                'summary': f"这是对 {video_info.get('title', 'Mock Video')} 的模拟总结。",
                'key_points': [
                    "模拟要点1：介绍了基本概念",
                    "模拟要点2：提供了实际案例", 
                    "模拟要点3：总结了关键技术"
                ],
                'tags': ["AI", "教程", "技术"],
                'video_id': video_info.get('video_id', 'mock_id')
            }
            summaries.append(summary)
        
        logger.success(f"✅ AI处理完成，生成了 {len(summaries)} 个总结")
        
        return Event(
            event_type=EventType.AI_PROCESSING_COMPLETED,
            data={
                'summaries': summaries,
                'success_count': len(summaries),
                'failure_count': 0
            },
            correlation_id=event.correlation_id
        )

class MockObsidianHandler:
    """模拟Obsidian处理器"""
    
    def can_handle(self, event_type):
        return event_type == EventType.OUTPUT_GENERATION_STARTED
    
    async def handle(self, event):
        """模拟文档生成"""
        logger.info("📝 开始生成Obsidian文档...")
        await asyncio.sleep(0.5)  # 模拟写入时间
        
        summaries = event.data.get('summaries', [])
        created_files = []
        
        # 模拟创建文档
        vault_path = Path(MockConfig.OBSIDIAN_VAULT_PATH)
        
        for i, summary in enumerate(summaries):
            file_name = f"视频总结_{i+1}_{summary['title'][:10]}.md"
            file_path = vault_path / file_name
            
            # 创建简单的markdown内容
            content = f"""# {summary['title']}

## 基本信息
- **频道**: {summary['channel']}
- **时长**: {summary['duration']}
- **链接**: {summary['url']}

## 内容总结
{summary['summary']}

## 关键要点
"""
            for point in summary['key_points']:
                content += f"- {point}\n"
            
            content += f"\n## 标签\n"
            for tag in summary['tags']:
                content += f"#{tag} "
            
            # 写入文件
            file_path.write_text(content, encoding='utf-8')
            created_files.append(str(file_path))
            logger.info(f"📄 创建文档: {file_name}")
        
        # 创建索引文档
        index_path = vault_path / "视频总结索引.md"
        index_content = f"""# 视频总结索引

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 总结列表
"""
        for i, summary in enumerate(summaries):
            index_content += f"{i+1}. [[视频总结_{i+1}_{summary['title'][:10]}]] - {summary['title']}\n"
        
        index_path.write_text(index_content, encoding='utf-8')
        created_files.append(str(index_path))
        
        logger.success(f"✅ 文档生成完成，创建了 {len(created_files)} 个文件")
        
        return Event(
            event_type=EventType.OUTPUT_GENERATED,
            data={
                'created_files': created_files,
                'success_count': len(created_files),
                'failure_count': 0
            },
            correlation_id=event.correlation_id
        )

class SimpleEventDrivenSystem:
    """简化的事件驱动系统"""
    
    def __init__(self):
        """初始化系统"""
        MockConfig.validate()
        MockConfig.create_directories()
        
        # 创建核心组件
        self.event_bus = EventBus()
        self.workflow_engine = WorkflowEngine(self.event_bus)
        
        # 注册处理器
        self._register_handlers()
        
        # 注册工作流
        self.workflow_engine.register_workflow(YOUTUBE_SUMMARY_WORKFLOW)
        
        logger.info("🚀 简化事件驱动系统初始化完成")
    
    def _register_handlers(self):
        """注册事件处理器"""
        handlers = [
            MockGeminiHandler(),
            MockObsidianHandler(),
            self.workflow_engine
        ]
        
        for handler in handlers:
            self.event_bus.register_handler(handler)
        
        logger.info(f"📋 注册了 {len(handlers)} 个事件处理器")
    
    async def process_query(self, query: str):
        """处理查询"""
        logger.info(f"🔍 开始处理查询: {query}")
        
        # 执行工作流
        workflow_id = await self.workflow_engine.execute_workflow(
            "youtube_summary",
            {"query": query, "max_results": 3}
        )
        
        logger.info(f"⚡ 工作流启动，ID: {workflow_id}")
        
        # 等待完成
        return await self._wait_for_completion(workflow_id)
    
    async def _wait_for_completion(self, workflow_id: str):
        """等待工作流完成"""
        for i in range(30):  # 最多等待30秒
            status = self.workflow_engine.get_workflow_status(workflow_id)
            
            if not status:
                return {'success': False, 'error': 'Workflow not found'}
            
            logger.info(f"⏳ 工作流进度: {status['progress']} ({status['progress_percentage']:.1f}%)")
            
            if status['state'] == 'completed':
                instance = self.workflow_engine.active_instances[workflow_id]
                created_files = []
                
                # 提取创建的文件
                output_result = instance.step_results.get('generate_output', {})
                if isinstance(output_result, dict):
                    created_files = output_result.get('created_files', [])
                
                return {
                    'success': True,
                    'workflow_id': workflow_id,
                    'created_files': created_files,
                    'results': instance.step_results
                }
            elif status['state'] == 'failed':
                return {
                    'success': False,
                    'error': 'Workflow failed',
                    'workflow_id': workflow_id
                }
            
            await asyncio.sleep(1)
        
        return {'success': False, 'error': 'Timeout'}

async def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python simple_test.py <搜索关键词>")
        print("示例: python simple_test.py '人工智能教程'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    try:
        # 初始化系统
        system = SimpleEventDrivenSystem()
        
        # 处理查询
        result = await system.process_query(query)
        
        if result['success']:
            logger.success("🎉 事件驱动处理完成！")
            
            print("\n" + "="*50)
            print("📊 处理结果摘要")
            print("="*50)
            print(f"🔍 搜索关键词: {query}")
            print(f"🆔 工作流ID: {result['workflow_id']}")
            
            created_files = result.get('created_files', [])
            if created_files:
                print(f"📁 创建文档数量: {len(created_files)}")
                print("\n📄 创建的文档:")
                for file_path in created_files:
                    file_name = Path(file_path).name
                    print(f"  • {file_name}")
                    
                print(f"\n📂 文档位置: {MockConfig.OBSIDIAN_VAULT_PATH}")
            
            print("="*50)
            return 0
        else:
            logger.error("❌ 处理失败")
            print(f"错误: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        logger.error(f"💥 系统错误: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)