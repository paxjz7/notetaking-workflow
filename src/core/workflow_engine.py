"""
工作流引擎 - 支持DAG和并行处理
"""
import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from loguru import logger

from .event_system import Event, EventType, EventBus

class WorkflowState(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class RetryPolicy:
    """重试策略"""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    exceptions: tuple = (Exception,)

@dataclass
class RateLimit:
    """速率限制"""
    requests_per_minute: int = 10
    burst_size: int = 5

@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    name: str
    event_type: EventType
    next_steps: List[str] = field(default_factory=list)
    parallel: bool = False
    timeout: int = 300  # 5分钟超时
    retry_policy: Optional[RetryPolicy] = None
    rate_limit: Optional[RateLimit] = None
    condition: Optional[str] = None  # 条件表达式
    
    def __post_init__(self):
        if self.retry_policy is None:
            self.retry_policy = RetryPolicy()

@dataclass
class WorkflowDefinition:
    """工作流定义"""
    name: str
    description: str
    steps: List[WorkflowStep]
    initial_step: str
    version: str = "1.0"
    
    def validate(self) -> bool:
        """验证工作流定义"""
        step_names = {step.name for step in self.steps}
        
        # 检查初始步骤存在
        if self.initial_step not in step_names:
            logger.error(f"初始步骤 {self.initial_step} 不存在")
            return False
        
        # 检查所有next_steps都存在
        for step in self.steps:
            for next_step in step.next_steps:
                if next_step not in step_names:
                    logger.error(f"步骤 {step.name} 的下一步 {next_step} 不存在")
                    return False
        
        # 检查是否有循环依赖
        if self._has_cycle():
            logger.error("工作流包含循环依赖")
            return False
        
        return True
    
    def _has_cycle(self) -> bool:
        """检测是否有循环依赖"""
        visited = set()
        rec_stack = set()
        
        def dfs(step_name: str) -> bool:
            visited.add(step_name)
            rec_stack.add(step_name)
            
            step = next((s for s in self.steps if s.name == step_name), None)
            if step:
                for next_step in step.next_steps:
                    if next_step not in visited:
                        if dfs(next_step):
                            return True
                    elif next_step in rec_stack:
                        return True
            
            rec_stack.remove(step_name)
            return False
        
        return dfs(self.initial_step)

@dataclass
class WorkflowInstance:
    """工作流实例"""
    id: str
    definition: WorkflowDefinition
    input_data: Any
    state: WorkflowState = WorkflowState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    step_states: Dict[str, StepStatus] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    step_errors: Dict[str, str] = field(default_factory=dict)
    current_steps: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        # 初始化所有步骤状态
        for step in self.definition.steps:
            self.step_states[step.name] = StepStatus.PENDING

class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.active_instances: Dict[str, WorkflowInstance] = {}
        
        # 注册工作流事件处理器
        self.event_bus.register_handler(self)
    
    def can_handle(self, event_type: EventType) -> bool:
        """判断是否能处理工作流相关事件"""
        workflow_events = {
            EventType.WORKFLOW_STARTED,
            EventType.CONTENT_FOUND,
            EventType.CONTENT_EXTRACTED,
            EventType.AI_PROCESSING_COMPLETED,
            EventType.OUTPUT_GENERATED,
            EventType.ERROR_OCCURRED
        }
        return event_type in workflow_events
    
    async def handle(self, event: Event) -> Optional[Event]:
        """处理工作流事件"""
        if not event.correlation_id:
            return None
        
        instance = self.active_instances.get(event.correlation_id)
        if not instance:
            return None
        
        # 处理YouTube搜索
        if event.event_type == EventType.CONTENT_SEARCH_STARTED:
            await self._handle_youtube_search(instance, event)
        elif event.event_type == EventType.CONTENT_FOUND:
            await self._advance_workflow(instance, "search_videos", StepStatus.COMPLETED, event.data)
        elif event.event_type == EventType.CONTENT_EXTRACTION_STARTED:
            await self._handle_content_extraction(instance, event)
        elif event.event_type == EventType.CONTENT_EXTRACTED:
            await self._advance_workflow(instance, "extract_content", StepStatus.COMPLETED, event.data)
        elif event.event_type == EventType.AI_PROCESSING_COMPLETED:
            await self._advance_workflow(instance, "ai_processing", StepStatus.COMPLETED, event.data)
        elif event.event_type == EventType.OUTPUT_GENERATED:
            await self._advance_workflow(instance, "generate_output", StepStatus.COMPLETED, event.data)
        elif event.event_type == EventType.ERROR_OCCURRED:
            await self._handle_step_error(instance, event)
        
        return None
    
    def register_workflow(self, workflow: WorkflowDefinition):
        """注册工作流定义"""
        if not workflow.validate():
            raise ValueError(f"工作流 {workflow.name} 验证失败")
        
        self.workflows[workflow.name] = workflow
        logger.info(f"注册工作流: {workflow.name}")
    
    async def execute_workflow(self, workflow_name: str, input_data: Any, 
                             correlation_id: Optional[str] = None) -> str:
        """执行工作流"""
        if workflow_name not in self.workflows:
            raise ValueError(f"未找到工作流: {workflow_name}")
        
        # 生成或使用提供的关联ID
        if not correlation_id:
            correlation_id = f"{workflow_name}_{uuid.uuid4().hex[:8]}"
        
        workflow_def = self.workflows[workflow_name]
        
        # 创建工作流实例
        instance = WorkflowInstance(
            id=correlation_id,
            definition=workflow_def,
            input_data=input_data,
            state=WorkflowState.RUNNING
        )
        
        self.active_instances[correlation_id] = instance
        
        # 发布工作流开始事件
        start_event = Event(
            event_type=EventType.WORKFLOW_STARTED,
            data={
                'workflow_name': workflow_name,
                'input_data': input_data,
                'workflow_id': correlation_id
            },
            correlation_id=correlation_id
        )
        
        await self.event_bus.publish(start_event)
        
        # 启动初始步骤
        await self._start_next_steps(instance, [workflow_def.initial_step])
        
        return correlation_id
    
    async def _advance_workflow(self, instance: WorkflowInstance, step_name: str, 
                               status: StepStatus, result: Any = None):
        """推进工作流"""
        # 更新步骤状态
        instance.step_states[step_name] = status
        instance.current_steps.discard(step_name)
        instance.updated_at = datetime.now()
        
        if result:
            instance.step_results[step_name] = result
        
        logger.info(f"工作流 {instance.id} 步骤 {step_name} 状态: {status.value}")
        
        if status == StepStatus.COMPLETED:
            # 查找下一步骤
            step_def = next((s for s in instance.definition.steps if s.name == step_name), None)
            if step_def and step_def.next_steps:
                await self._start_next_steps(instance, step_def.next_steps)
            else:
                # 没有下一步，检查是否完成
                await self._check_workflow_completion(instance)
        elif status == StepStatus.FAILED:
            # 处理步骤失败
            await self._handle_workflow_failure(instance, step_name)
    
    async def _start_next_steps(self, instance: WorkflowInstance, step_names: List[str]):
        """启动下一批步骤"""
        for step_name in step_names:
            step_def = next((s for s in instance.definition.steps if s.name == step_name), None)
            if not step_def:
                continue
            
            # 检查是否满足执行条件
            if step_def.condition and not self._evaluate_condition(step_def.condition, instance):
                instance.step_states[step_name] = StepStatus.SKIPPED
                continue
            
            # 标记步骤为运行中
            instance.step_states[step_name] = StepStatus.RUNNING
            instance.current_steps.add(step_name)
            
            # 发布步骤开始事件
            step_event = Event(
                event_type=step_def.event_type,
                data=self._prepare_step_data(instance, step_def),
                correlation_id=instance.id,
                metadata={'step_name': step_name, 'timeout': step_def.timeout}
            )
            
            await self.event_bus.publish(step_event)
    
    def _prepare_step_data(self, instance: WorkflowInstance, step_def: WorkflowStep) -> Dict[str, Any]:
        """准备步骤数据"""
        data = {'input_data': instance.input_data}
        
        # 添加前面步骤的结果
        for step_name, result in instance.step_results.items():
            data[f"{step_name}_result"] = result
        
        return data
    
    def _evaluate_condition(self, condition: str, instance: WorkflowInstance) -> bool:
        """评估条件表达式"""
        # 简单的条件评估，实际应用中可以使用更复杂的表达式引擎
        context = {
            'step_states': instance.step_states,
            'step_results': instance.step_results
        }
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.error(f"条件评估失败: {condition}, 错误: {e}")
            return False
    
    async def _check_workflow_completion(self, instance: WorkflowInstance):
        """检查工作流是否完成"""
        # 检查是否还有运行中的步骤
        if instance.current_steps:
            return
        
        # 检查是否所有步骤都完成或跳过
        pending_steps = [name for name, status in instance.step_states.items() 
                        if status == StepStatus.PENDING]
        
        if not pending_steps:
            # 工作流完成
            instance.state = WorkflowState.COMPLETED
            instance.updated_at = datetime.now()
            
            completion_event = Event(
                event_type=EventType.WORKFLOW_COMPLETED,
                data={
                    'workflow_id': instance.id,
                    'results': instance.step_results,
                    'execution_time': (instance.updated_at - instance.created_at).total_seconds()
                },
                correlation_id=instance.id
            )
            
            await self.event_bus.publish(completion_event)
            logger.success(f"工作流 {instance.id} 执行完成")
    
    async def _handle_workflow_failure(self, instance: WorkflowInstance, failed_step: str):
        """处理工作流失败"""
        instance.state = WorkflowState.FAILED
        instance.updated_at = datetime.now()
        
        failure_event = Event(
            event_type=EventType.WORKFLOW_FAILED,
            data={
                'workflow_id': instance.id,
                'failed_step': failed_step,
                'error': instance.step_errors.get(failed_step, 'Unknown error')
            },
            correlation_id=instance.id
        )
        
        await self.event_bus.publish(failure_event)
        logger.error(f"工作流 {instance.id} 执行失败，失败步骤: {failed_step}")
    
    async def _handle_youtube_search(self, instance: WorkflowInstance, event: Event):
        """处理YouTube搜索"""
        try:
            query = event.data.get('query', '')
            max_results = event.data.get('max_results', 3)
            
            # 这里应该调用YouTube处理逻辑
            # 为了简化，我们直接模拟搜索结果
            mock_videos = [
                {
                    'title': f'Mock Video {i+1} for {query}',
                    'url': f'https://youtube.com/watch?v=mock{i+1}',
                    'description': f'Mock description for video {i+1}',
                    'duration': '10:00',
                    'view_count': '1000',
                    'upload_date': '2024-01-01',
                    'channel': 'Mock Channel',
                    'video_id': f'mock{i+1}'
                }
                for i in range(max_results)
            ]
            
            # 发布内容发现事件
            found_event = Event(
                event_type=EventType.CONTENT_FOUND,
                data={
                    'videos': mock_videos,
                    'search_query': query,
                    'count': len(mock_videos)
                },
                correlation_id=event.correlation_id,
                metadata={'source': 'youtube'}
            )
            
            await self.event_bus.publish(found_event)
            
        except Exception as e:
            logger.error(f"YouTube搜索失败: {e}")
            error_event = Event(
                event_type=EventType.CONTENT_SEARCH_FAILED,
                data={'error': str(e), 'query': event.data.get('query', '')},
                correlation_id=event.correlation_id
            )
            await self.event_bus.publish(error_event)
    
    async def _handle_content_extraction(self, instance: WorkflowInstance, event: Event):
        """处理内容提取"""
        try:
            videos_data = event.data.get('videos', [])
            if not videos_data:
                raise ValueError("没有视频数据需要提取")
            
            # 模拟内容提取
            extracted_content = []
            for video_data in videos_data:
                extracted_content.append({
                    'video_info': video_data,
                    'transcript': f"Mock transcript for {video_data.get('title', 'Unknown')}",
                    'extraction_method': 'mock'
                })
            
            # 发布内容提取完成事件
            extracted_event = Event(
                event_type=EventType.CONTENT_EXTRACTED,
                data={
                    'extracted_content': extracted_content,
                    'success_count': len(extracted_content),
                    'failure_count': 0
                },
                correlation_id=event.correlation_id,
                metadata={'handler': 'MockContentExtractor'}
            )
            
            await self.event_bus.publish(extracted_event)
            
        except Exception as e:
            logger.error(f"内容提取失败: {e}")
            error_event = Event(
                event_type=EventType.CONTENT_EXTRACTION_FAILED,
                data={'error': str(e)},
                correlation_id=event.correlation_id
            )
            await self.event_bus.publish(error_event)
    
    async def _handle_step_error(self, instance: WorkflowInstance, error_event: Event):
        """处理步骤错误"""
        step_name = error_event.metadata.get('step_name')
        if step_name:
            instance.step_errors[step_name] = error_event.data.get('error', 'Unknown error')
            await self._advance_workflow(instance, step_name, StepStatus.FAILED)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        instance = self.active_instances.get(workflow_id)
        if not instance:
            return None
        
        completed_steps = sum(1 for status in instance.step_states.values() 
                            if status in [StepStatus.COMPLETED, StepStatus.SKIPPED])
        total_steps = len(instance.step_states)
        
        return {
            'workflow_id': instance.id,
            'workflow_name': instance.definition.name,
            'state': instance.state.value,
            'progress': f"{completed_steps}/{total_steps}",
            'progress_percentage': (completed_steps / total_steps) * 100 if total_steps > 0 else 0,
            'current_steps': list(instance.current_steps),
            'step_states': {name: status.value for name, status in instance.step_states.items()},
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat()
        }

# 预定义的YouTube总结工作流
YOUTUBE_SUMMARY_WORKFLOW = WorkflowDefinition(
    name="youtube_summary",
    description="YouTube视频搜索、提取、总结和文档生成工作流",
    steps=[
        WorkflowStep(
            name="search_videos",
            event_type=EventType.CONTENT_SEARCH_STARTED,
            next_steps=["extract_content"],
            timeout=60,
            retry_policy=RetryPolicy(max_attempts=3, backoff_factor=2)
        ),
        WorkflowStep(
            name="extract_content",
            event_type=EventType.CONTENT_EXTRACTION_STARTED,
            next_steps=["ai_processing"],
            parallel=True,
            timeout=120
        ),
        WorkflowStep(
            name="ai_processing",
            event_type=EventType.AI_PROCESSING_STARTED,
            next_steps=["generate_output"],
            parallel=True,
            timeout=300,
            rate_limit=RateLimit(requests_per_minute=5)
        ),
        WorkflowStep(
            name="generate_output",
            event_type=EventType.OUTPUT_GENERATION_STARTED,
            next_steps=[],
            timeout=60
        )
    ],
    initial_step="search_videos"
)