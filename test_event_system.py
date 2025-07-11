"""
独立的事件驱动系统测试
不依赖外部包，专注测试架构本身
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 设置基本日志
def log(level, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{timestamp} | {level:8} | {message}")

def info(msg): log("INFO", msg)
def success(msg): log("SUCCESS", msg) 
def error(msg): log("ERROR", msg)
def debug(msg): log("DEBUG", msg)

# ==== 复制核心事件系统代码 ====

class EventType(Enum):
    """系统事件类型"""
    CONTENT_SEARCH_STARTED = "content.search.started"
    CONTENT_FOUND = "content.found"
    CONTENT_SEARCH_FAILED = "content.search.failed"
    
    CONTENT_EXTRACTION_STARTED = "content.extraction.started"
    CONTENT_EXTRACTED = "content.extracted"
    CONTENT_EXTRACTION_FAILED = "content.extraction.failed"
    
    AI_PROCESSING_STARTED = "ai.processing.started"
    AI_PROCESSING_COMPLETED = "ai.processing.completed"
    AI_PROCESSING_FAILED = "ai.processing.failed"
    
    OUTPUT_GENERATION_STARTED = "output.generation.started"
    OUTPUT_GENERATED = "output.generated"
    OUTPUT_GENERATION_FAILED = "output.generation.failed"
    
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    ERROR_OCCURRED = "error.occurred"

@dataclass
class Event:
    """通用事件数据结构"""
    event_type: EventType
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None

class EventHandler:
    """事件处理器抽象基类"""
    
    def can_handle(self, event_type: EventType) -> bool:
        """判断是否能处理指定类型的事件"""
        return False
    
    async def handle(self, event: Event) -> Optional[Event]:
        """处理事件，可能产生新事件"""
        return None

class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._event_history: List[Event] = []
    
    def register_handler(self, handler: EventHandler):
        """注册事件处理器"""
        for event_type in EventType:
            if handler.can_handle(event_type):
                if event_type not in self._handlers:
                    self._handlers[event_type] = []
                self._handlers[event_type].append(handler)
                debug(f"注册处理器 {handler.__class__.__name__} 处理事件 {event_type.value}")
    
    async def publish(self, event: Event) -> List[Event]:
        """发布事件并处理"""
        debug(f"发布事件: {event.event_type.value}")
        
        self._event_history.append(event)
        
        new_events = []
        handlers = self._handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                result_event = await handler.handle(event)
                if result_event:
                    new_events.append(result_event)
            except Exception as e:
                error(f"处理器 {handler.__class__.__name__} 处理事件失败: {e}")
        
        return new_events
    
    async def publish_and_wait(self, event: Event, max_depth: int = 10) -> List[Event]:
        """发布事件并递归处理产生的新事件"""
        all_events = [event]
        pending_events = [event]
        depth = 0
        
        while pending_events and depth < max_depth:
            current_events = pending_events.copy()
            pending_events.clear()
            
            for evt in current_events:
                new_events = await self.publish(evt)
                pending_events.extend(new_events)
                all_events.extend(new_events)
            
            depth += 1
        
        return all_events

# ==== 简化的工作流引擎 ====

class WorkflowState(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SimpleWorkflowEngine(EventHandler):
    """简化的工作流引擎"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.workflow_states = {}
    
    def can_handle(self, event_type: EventType) -> bool:
        workflow_events = {
            EventType.WORKFLOW_STARTED,
            EventType.CONTENT_SEARCH_STARTED,
            EventType.CONTENT_FOUND,
            EventType.CONTENT_EXTRACTION_STARTED,
            EventType.CONTENT_EXTRACTED,
            EventType.AI_PROCESSING_COMPLETED,
            EventType.OUTPUT_GENERATED
        }
        return event_type in workflow_events
    
    async def handle(self, event: Event) -> Optional[Event]:
        """处理工作流事件"""
        if not event.correlation_id:
            return None
        
        if event.event_type == EventType.CONTENT_SEARCH_STARTED:
            return await self._handle_search(event)
        elif event.event_type == EventType.CONTENT_FOUND:
            return await self._handle_found(event)
        elif event.event_type == EventType.CONTENT_EXTRACTED:
            return await self._handle_extracted(event)
        elif event.event_type == EventType.AI_PROCESSING_COMPLETED:
            return await self._handle_ai_completed(event)
        elif event.event_type == EventType.OUTPUT_GENERATED:
            return await self._handle_output_generated(event)
        
        return None
    
    async def start_workflow(self, query: str) -> str:
        """启动工作流"""
        import uuid
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        self.workflow_states[workflow_id] = {
            'state': WorkflowState.RUNNING,
            'steps': {},
            'results': {}
        }
        
        # 发布搜索开始事件
        search_event = Event(
            event_type=EventType.CONTENT_SEARCH_STARTED,
            data={'query': query, 'max_results': 3},
            correlation_id=workflow_id
        )
        
        # 使用publish_and_wait来确保事件级联执行
        await self.event_bus.publish_and_wait(search_event)
        return workflow_id
    
    async def _handle_search(self, event: Event) -> Optional[Event]:
        """处理搜索"""
        query = event.data.get('query', '')
        max_results = event.data.get('max_results', 3)
        
        # 模拟搜索结果
        mock_videos = [
            {
                'title': f'AI教程第{i+1}部分: {query}',
                'url': f'https://youtube.com/watch?v=mock{i+1}',
                'description': f'关于{query}的详细教程第{i+1}部分',
                'duration': f'{10+i*5}:00',
                'view_count': f'{1000*(i+1)}',
                'upload_date': '2024-01-01',
                'channel': f'AI教育频道{i+1}',
                'video_id': f'mock{i+1}'
            }
            for i in range(max_results)
        ]
        
        info(f"🔍 搜索完成，找到 {len(mock_videos)} 个视频")
        
        return Event(
            event_type=EventType.CONTENT_FOUND,
            data={'videos': mock_videos, 'search_query': query},
            correlation_id=event.correlation_id
        )
    
    async def _handle_found(self, event: Event) -> Optional[Event]:
        """处理找到的内容"""
        videos = event.data.get('videos', [])
        
        info(f"📥 开始内容提取，共 {len(videos)} 个视频")
        
        return Event(
            event_type=EventType.CONTENT_EXTRACTION_STARTED,
            data=event.data,
            correlation_id=event.correlation_id
        )
    
    async def _handle_extracted(self, event: Event) -> Optional[Event]:
        """处理提取的内容"""
        extracted_content = event.data.get('extracted_content', [])
        
        info(f"🤖 开始AI处理，共 {len(extracted_content)} 个内容")
        
        return Event(
            event_type=EventType.AI_PROCESSING_STARTED,
            data=event.data,
            correlation_id=event.correlation_id
        )
    
    async def _handle_ai_completed(self, event: Event) -> Optional[Event]:
        """处理AI完成"""
        summaries = event.data.get('summaries', [])
        
        info(f"📝 开始输出生成，共 {len(summaries)} 个总结")
        
        return Event(
            event_type=EventType.OUTPUT_GENERATION_STARTED,
            data=event.data,
            correlation_id=event.correlation_id
        )
    
    async def _handle_output_generated(self, event: Event) -> Optional[Event]:
        """处理输出生成完成"""
        workflow_id = event.correlation_id
        if workflow_id in self.workflow_states:
            self.workflow_states[workflow_id]['state'] = WorkflowState.COMPLETED
            self.workflow_states[workflow_id]['results'] = event.data
        
        success(f"✅ 工作流 {workflow_id} 完成")
        
        return Event(
            event_type=EventType.WORKFLOW_COMPLETED,
            data=event.data,
            correlation_id=event.correlation_id
        )
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """获取工作流状态"""
        if workflow_id not in self.workflow_states:
            return None
        
        state = self.workflow_states[workflow_id]
        return {
            'workflow_id': workflow_id,
            'state': state['state'].value,
            'results': state.get('results', {})
        }

# ==== 模拟处理器 ====

class MockContentExtractor(EventHandler):
    """模拟内容提取器"""
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type == EventType.CONTENT_EXTRACTION_STARTED
    
    async def handle(self, event: Event) -> Optional[Event]:
        videos = event.data.get('videos', [])
        
        # 模拟提取过程
        await asyncio.sleep(0.5)
        
        extracted_content = []
        for video in videos:
            extracted_content.append({
                'video_info': video,
                'transcript': f"模拟字幕内容：这是关于{video['title']}的详细解释...",
                'extraction_method': 'mock'
            })
        
        info(f"📥 内容提取完成，提取了 {len(extracted_content)} 个视频内容")
        
        return Event(
            event_type=EventType.CONTENT_EXTRACTED,
            data={'extracted_content': extracted_content},
            correlation_id=event.correlation_id
        )

class MockAIProcessor(EventHandler):
    """模拟AI处理器"""
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type == EventType.AI_PROCESSING_STARTED
    
    async def handle(self, event: Event) -> Optional[Event]:
        extracted_content = event.data.get('extracted_content', [])
        
        # 模拟AI处理
        await asyncio.sleep(1)
        
        summaries = []
        for content in extracted_content:
            video_info = content['video_info']
            summary = {
                'title': video_info['title'],
                'url': video_info['url'],
                'channel': video_info['channel'],
                'duration': video_info['duration'],
                'upload_date': video_info['upload_date'],
                'summary': f"这是对《{video_info['title']}》的AI总结。该视频详细介绍了相关概念和实践方法。",
                'key_points': [
                    "介绍了基础概念和原理",
                    "提供了实际应用案例",
                    "总结了关键技术要点",
                    "给出了学习建议和资源"
                ],
                'tags': ["AI", "教程", "技术", "学习"],
                'video_id': video_info['video_id']
            }
            summaries.append(summary)
        
        info(f"🤖 AI处理完成，生成了 {len(summaries)} 个总结")
        
        return Event(
            event_type=EventType.AI_PROCESSING_COMPLETED,
            data={'summaries': summaries},
            correlation_id=event.correlation_id
        )

class MockDocumentGenerator(EventHandler):
    """模拟文档生成器"""
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type == EventType.OUTPUT_GENERATION_STARTED
    
    async def handle(self, event: Event) -> Optional[Event]:
        summaries = event.data.get('summaries', [])
        
        # 模拟文档生成
        await asyncio.sleep(0.3)
        
        vault_path = Path("/workspace/test_vault")
        vault_path.mkdir(exist_ok=True)
        
        created_files = []
        
        for i, summary in enumerate(summaries):
            file_name = f"视频总结_{i+1}_{summary['title'][:20]}.md"
            file_path = vault_path / file_name
            
            content = f"""# {summary['title']}

## 基本信息
- **频道**: {summary['channel']}
- **时长**: {summary['duration']}
- **上传日期**: {summary['upload_date']}
- **链接**: {summary['url']}

## 内容总结
{summary['summary']}

## 关键要点
"""
            for point in summary['key_points']:
                content += f"- {point}\n"
            
            content += "\n## 标签\n"
            for tag in summary['tags']:
                content += f"#{tag} "
            
            file_path.write_text(content, encoding='utf-8')
            created_files.append(str(file_path))
            info(f"📄 创建文档: {file_name}")
        
        # 创建索引
        index_path = vault_path / "视频总结索引.md"
        index_content = f"""# 视频总结索引

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 总结列表
"""
        for i, summary in enumerate(summaries):
            index_content += f"{i+1}. [[视频总结_{i+1}_{summary['title'][:20]}]] - {summary['title']}\n"
        
        index_path.write_text(index_content, encoding='utf-8')
        created_files.append(str(index_path))
        
        info(f"📝 文档生成完成，创建了 {len(created_files)} 个文件")
        
        return Event(
            event_type=EventType.OUTPUT_GENERATED,
            data={'created_files': created_files},
            correlation_id=event.correlation_id
        )

# ==== 主测试系统 ====

class EventDrivenTestSystem:
    """事件驱动测试系统"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.workflow_engine = SimpleWorkflowEngine(self.event_bus)
        
        # 注册所有处理器
        handlers = [
            self.workflow_engine,
            MockContentExtractor(),
            MockAIProcessor(),
            MockDocumentGenerator()
        ]
        
        for handler in handlers:
            self.event_bus.register_handler(handler)
        
        info(f"🚀 系统初始化完成，注册了 {len(handlers)} 个处理器")
    
    async def process_query(self, query: str):
        """处理查询"""
        info(f"🔍 开始处理查询: {query}")
        
        # 启动工作流
        workflow_id = await self.workflow_engine.start_workflow(query)
        info(f"⚡ 工作流启动，ID: {workflow_id}")
        
        # 等待完成
        for i in range(20):  # 最多等待20秒
            await asyncio.sleep(1)
            
            status = self.workflow_engine.get_workflow_status(workflow_id)
            if status and status['state'] == 'completed':
                return {
                    'success': True,
                    'workflow_id': workflow_id,
                    'results': status['results']
                }
        
        return {'success': False, 'error': 'Timeout'}

async def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python test_event_system.py <搜索关键词>")
        print("示例: python test_event_system.py '人工智能教程'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    try:
        # 初始化系统
        system = EventDrivenTestSystem()
        
        # 处理查询
        result = await system.process_query(query)
        
        if result['success']:
            success("🎉 事件驱动处理成功完成！")
            
            print("\n" + "="*60)
            print("📊 处理结果摘要")
            print("="*60)
            print(f"🔍 搜索关键词: {query}")
            print(f"🆔 工作流ID: {result['workflow_id']}")
            
            created_files = result['results'].get('created_files', [])
            if created_files:
                print(f"📁 创建文档数量: {len(created_files)}")
                print("\n📄 创建的文档:")
                for file_path in created_files:
                    file_name = Path(file_path).name
                    print(f"  • {file_name}")
                
                print(f"\n📂 文档位置: /workspace/test_vault")
                
                # 显示第一个文档的内容示例
                if created_files:
                    first_file = Path(created_files[0])
                    if first_file.exists():
                        content = first_file.read_text(encoding='utf-8')
                        print(f"\n📖 文档内容示例 ({first_file.name}):")
                        print("-" * 40)
                        print(content[:300] + "..." if len(content) > 300 else content)
                        print("-" * 40)
            
            print("="*60)
            return 0
        else:
            error("❌ 处理失败")
            print(f"错误: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        error(f"💥 系统错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)