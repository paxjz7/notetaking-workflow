"""
事件驱动的YouTube视频总结系统主程序
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import Config
from src.core.event_system import EventBus, Event, EventType
from src.core.workflow_engine import WorkflowEngine, YOUTUBE_SUMMARY_WORKFLOW
from src.processors.gemini_handler import GeminiProcessingHandler
from src.processors.obsidian_handler import ObsidianOutputHandler

# Legacy组件（重用现有逻辑）
from src.youtube_processor import YouTubeProcessor
from src.gemini_summarizer import GeminiSummarizer
from src.obsidian_writer import ObsidianWriter

class EventDrivenYouTubeSystem:
    """
    事件驱动的YouTube视频总结系统
    """
    
    def __init__(self):
        """初始化系统组件"""
        try:
            # 验证配置
            Config.validate()
            Config.create_directories()
            
            # 创建核心组件
            self.event_bus = EventBus()
            self.workflow_engine = WorkflowEngine(self.event_bus)
            
            # 创建Legacy组件实例
            self.youtube_processor = YouTubeProcessor()
            self.gemini_summarizer = GeminiSummarizer()
            self.obsidian_writer = ObsidianWriter()
            
            # 注册事件处理器
            self._register_handlers()
            
            # 注册工作流
            self.workflow_engine.register_workflow(YOUTUBE_SUMMARY_WORKFLOW)
            
            logger.info("事件驱动YouTube视频总结系统初始化完成")
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            raise
    
    def _register_handlers(self):
        """注册所有事件处理器"""
        # Gemini处理器
        gemini_handler = GeminiProcessingHandler(self.gemini_summarizer)
        
        # Obsidian处理器
        obsidian_handler = ObsidianOutputHandler(self.obsidian_writer)
        
        # 注册到事件总线
        handlers = [
            gemini_handler,
            obsidian_handler,
            self.workflow_engine  # 工作流引擎本身也是一个处理器
        ]
        
        for handler in handlers:
            self.event_bus.register_handler(handler)
        
        logger.info(f"注册了 {len(handlers)} 个事件处理器")
    
    async def process_query(self, query: str) -> dict:
        """
        处理搜索查询
        
        Args:
            query: 搜索关键词
            
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"开始事件驱动处理查询: {query}")
            
            # 执行工作流
            workflow_id = await self.workflow_engine.execute_workflow(
                "youtube_summary",
                {"query": query, "max_results": 3}
            )
            
            logger.info(f"工作流启动成功，ID: {workflow_id}")
            
            # 等待工作流完成
            result = await self._wait_for_workflow_completion(workflow_id)
            
            return result
            
        except Exception as e:
            logger.error(f"处理查询时发生错误: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }
    
    async def _wait_for_workflow_completion(self, workflow_id: str, timeout: int = 600) -> dict:
        """
        等待工作流完成
        
        Args:
            workflow_id: 工作流ID
            timeout: 超时时间（秒）
            
        Returns:
            工作流执行结果
        """
        start_time = datetime.now()
        
        while True:
            # 检查工作流状态
            status = self.workflow_engine.get_workflow_status(workflow_id)
            
            if not status:
                return {
                    'success': False,
                    'error': 'Workflow not found',
                    'workflow_id': workflow_id
                }
            
            if status['state'] == 'completed':
                # 获取最终结果
                instance = self.workflow_engine.active_instances.get(workflow_id)
                if instance:
                    return {
                        'success': True,
                        'workflow_id': workflow_id,
                        'results': instance.step_results,
                        'execution_time': (datetime.now() - start_time).total_seconds(),
                        'created_files': self._extract_created_files(instance.step_results)
                    }
            
            elif status['state'] == 'failed':
                return {
                    'success': False,
                    'workflow_id': workflow_id,
                    'error': 'Workflow execution failed',
                    'step_states': status['step_states'],
                    'execution_time': (datetime.now() - start_time).total_seconds()
                }
            
            # 检查超时
            if (datetime.now() - start_time).total_seconds() > timeout:
                return {
                    'success': False,
                    'workflow_id': workflow_id,
                    'error': f'Workflow timeout after {timeout} seconds',
                    'step_states': status['step_states']
                }
            
            # 打印进度
            logger.info(f"工作流进度: {status['progress']} ({status['progress_percentage']:.1f}%)")
            
            # 等待一段时间再检查
            await asyncio.sleep(2)
    
    def _extract_created_files(self, step_results: dict) -> list:
        """从步骤结果中提取创建的文件列表"""
        created_files = []
        
        # 从输出生成步骤中提取文件
        output_result = step_results.get('generate_output')
        if output_result and isinstance(output_result, dict):
            files = output_result.get('created_files', [])
            created_files.extend(files)
        
        return created_files
    
    async def get_system_health(self) -> dict:
        """获取系统健康状况"""
        try:
            # 获取事件总线统计
            event_history = self.event_bus.get_event_history()
            
            # 获取活跃工作流统计
            active_workflows = len(self.workflow_engine.active_instances)
            
            # 计算系统健康评分
            health_score = self._calculate_system_health_score(event_history, active_workflows)
            
            return {
                'overall_health_score': health_score,
                'active_workflows': active_workflows,
                'total_events_processed': len(event_history),
                'registered_handlers': len(self.event_bus._handlers),
                'system_status': 'healthy' if health_score > 80 else 'warning' if health_score > 60 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"获取系统健康状况失败: {e}")
            return {
                'overall_health_score': 0,
                'error': str(e),
                'system_status': 'critical'
            }
    
    def _calculate_system_health_score(self, event_history: list, active_workflows: int) -> float:
        """计算系统健康评分"""
        score = 100.0
        
        # 检查事件处理是否正常
        if len(event_history) > 0:
            recent_events = event_history[-20:]  # 最近20个事件
            error_events = [e for e in recent_events if 'ERROR' in e.event_type.value.upper()]
            if error_events:
                error_rate = len(error_events) / len(recent_events)
                score -= error_rate * 30
        
        # 检查工作流积压
        if active_workflows > 10:
            score -= min(20, (active_workflows - 10) * 2)
        
        return max(0, min(100, score))

async def main():
    """主函数"""
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)
    
    # 检查命令行参数
    if len(sys.argv) != 2:
        logger.error("使用方法: python src/integration/event_driven_main.py <搜索关键词>")
        logger.error("示例: python src/integration/event_driven_main.py '人工智能教程'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    try:
        # 初始化系统
        system = EventDrivenYouTubeSystem()
        
        # 检查系统健康状况
        health = await system.get_system_health()
        logger.info(f"系统健康评分: {health['overall_health_score']:.1f}")
        
        # 处理查询
        result = await system.process_query(query)
        
        if result['success']:
            logger.success("事件驱动处理完成！")
            
            # 打印结果摘要
            print("\n" + "="*60)
            print("事件驱动处理结果摘要")
            print("="*60)
            print(f"搜索关键词: {query}")
            print(f"工作流ID: {result['workflow_id']}")
            print(f"执行时间: {result['execution_time']:.2f} 秒")
            
            created_files = result.get('created_files', [])
            if created_files:
                print(f"创建文档数量: {len(created_files)}")
                print("\n创建的文档:")
                for file_path in created_files:
                    print(f"- {file_path}")
            
            print("="*60)
            
            sys.exit(0)
        else:
            logger.error("事件驱动处理失败！")
            print(f"错误信息: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("程序被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())