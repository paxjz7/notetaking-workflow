"""
事件驱动系统 - 解决系统架构和扩展性问题
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger
import json

T = TypeVar('T')

class EventType(Enum):
    """系统事件类型"""
    # 内容发现事件
    CONTENT_SEARCH_STARTED = "content.search.started"
    CONTENT_FOUND = "content.found"
    CONTENT_SEARCH_FAILED = "content.search.failed"
    
    # 内容提取事件
    CONTENT_EXTRACTION_STARTED = "content.extraction.started"
    CONTENT_EXTRACTED = "content.extracted"
    CONTENT_EXTRACTION_FAILED = "content.extraction.failed"
    
    # AI处理事件
    AI_PROCESSING_STARTED = "ai.processing.started"
    AI_PROCESSING_COMPLETED = "ai.processing.completed"
    AI_PROCESSING_FAILED = "ai.processing.failed"
    
    # 输出生成事件
    OUTPUT_GENERATION_STARTED = "output.generation.started"
    OUTPUT_GENERATED = "output.generated"
    OUTPUT_GENERATION_FAILED = "output.generation.failed"
    
    # 系统事件
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # 错误处理事件
    ERROR_OCCURRED = "error.occurred"
    RETRY_ATTEMPTED = "retry.attempted"

@dataclass
class Event(Generic[T]):
    """通用事件数据结构"""
    event_type: EventType
    data: T
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'event_type': self.event_type.value,
            'data': self.data if isinstance(self.data, (dict, list, str, int, float, bool)) else str(self.data),
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id
        }

class EventHandler(ABC):
    """事件处理器抽象基类"""
    
    @abstractmethod
    async def handle(self, event: Event) -> Optional[Event]:
        """处理事件，可能产生新事件"""
        pass
    
    @abstractmethod
    def can_handle(self, event_type: EventType) -> bool:
        """判断是否能处理指定类型的事件"""
        pass

class EventBus:
    """
    事件总线 - 系统的核心协调器
    解决组件间耦合问题，实现真正的系统架构
    """
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._event_history: List[Event] = []
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
        
    def register_handler(self, handler: EventHandler):
        """注册事件处理器"""
        for event_type in EventType:
            if handler.can_handle(event_type):
                if event_type not in self._handlers:
                    self._handlers[event_type] = []
                self._handlers[event_type].append(handler)
                logger.debug(f"注册处理器 {handler.__class__.__name__} 处理事件 {event_type.value}")
    
    async def publish(self, event: Event) -> List[Event]:
        """
        发布事件并处理
        返回处理过程中产生的新事件
        """
        logger.debug(f"发布事件: {event.event_type.value}")
        
        # 记录事件历史
        self._event_history.append(event)
        
        # 更新工作流状态
        if event.correlation_id:
            self._update_workflow_state(event)
        
        # 处理事件
        new_events = []
        handlers = self._handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                result_event = await handler.handle(event)
                if result_event:
                    new_events.append(result_event)
            except Exception as e:
                logger.error(f"处理器 {handler.__class__.__name__} 处理事件失败: {e}")
                # 发布错误事件
                error_event = Event(
                    event_type=EventType.ERROR_OCCURRED,
                    data={'error': str(e), 'handler': handler.__class__.__name__},
                    correlation_id=event.correlation_id
                )
                new_events.append(error_event)
        
        return new_events
    
    async def publish_and_wait(self, event: Event, max_depth: int = 10) -> List[Event]:
        """
        发布事件并递归处理产生的新事件
        """
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
        
        if depth >= max_depth:
            logger.warning(f"事件处理达到最大深度 {max_depth}")
        
        return all_events
    
    def _update_workflow_state(self, event: Event):
        """更新工作流状态"""
        if event.correlation_id not in self._active_workflows:
            self._active_workflows[event.correlation_id] = {
                'start_time': datetime.now(),
                'events': [],
                'status': 'running'
            }
        
        workflow = self._active_workflows[event.correlation_id]
        workflow['events'].append(event.to_dict())
        
        # 更新工作流状态
        if event.event_type == EventType.WORKFLOW_COMPLETED:
            workflow['status'] = 'completed'
            workflow['end_time'] = datetime.now()
        elif event.event_type == EventType.WORKFLOW_FAILED:
            workflow['status'] = 'failed'
            workflow['end_time'] = datetime.now()
    
    def get_workflow_status(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        return self._active_workflows.get(correlation_id)
    
    def get_event_history(self, correlation_id: Optional[str] = None) -> List[Event]:
        """获取事件历史"""
        if correlation_id:
            return [e for e in self._event_history if e.correlation_id == correlation_id]
        return self._event_history.copy()

class WorkflowOrchestrator:
    """
    工作流编排器 - 定义和执行复杂的业务流程
    解决线性处理问题，支持分支、合并、条件执行
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._workflows: Dict[str, 'WorkflowDefinition'] = {}
    
    def register_workflow(self, workflow: 'WorkflowDefinition'):
        """注册工作流定义"""
        self._workflows[workflow.name] = workflow
        logger.info(f"注册工作流: {workflow.name}")
    
    async def execute_workflow(self, 
                             workflow_name: str, 
                             initial_data: Any,
                             correlation_id: Optional[str] = None) -> str:
        """执行工作流"""
        if workflow_name not in self._workflows:
            raise ValueError(f"未找到工作流: {workflow_name}")
        
        # 生成关联ID
        if not correlation_id:
            correlation_id = f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        workflow = self._workflows[workflow_name]
        
        # 发布工作流开始事件
        start_event = Event(
            event_type=EventType.WORKFLOW_STARTED,
            data={
                'workflow_name': workflow_name,
                'initial_data': initial_data
            },
            correlation_id=correlation_id
        )
        
        await self.event_bus.publish_and_wait(start_event)
        
        return correlation_id

@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    name: str
    event_type: EventType
    condition: Optional[Callable[[Any], bool]] = None
    next_steps: List[str] = field(default_factory=list)

@dataclass  
class WorkflowDefinition:
    """工作流定义"""
    name: str
    description: str
    steps: List[WorkflowStep]
    initial_step: str
    
    def validate(self) -> bool:
        """验证工作流定义"""
        step_names = {step.name for step in self.steps}
        
        # 检查初始步骤存在
        if self.initial_step not in step_names:
            return False
        
        # 检查所有next_steps都存在
        for step in self.steps:
            for next_step in step.next_steps:
                if next_step not in step_names:
                    return False
        
        return True

# 预定义的工作流
YOUTUBE_SUMMARY_WORKFLOW = WorkflowDefinition(
    name="youtube_summary",
    description="YouTube视频总结工作流",
    steps=[
        WorkflowStep(
            name="search_content",
            event_type=EventType.CONTENT_SEARCH_STARTED,
            next_steps=["extract_content"]
        ),
        WorkflowStep(
            name="extract_content", 
            event_type=EventType.CONTENT_EXTRACTION_STARTED,
            next_steps=["process_ai"]
        ),
        WorkflowStep(
            name="process_ai",
            event_type=EventType.AI_PROCESSING_STARTED,
            next_steps=["generate_output"]
        ),
        WorkflowStep(
            name="generate_output",
            event_type=EventType.OUTPUT_GENERATION_STARTED,
            next_steps=[]
        )
    ],
    initial_step="search_content"
)