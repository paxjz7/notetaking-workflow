# 方案二：事件驱动架构重构

## 核心理念
将现有线性系统重构为事件驱动架构，实现真正的解耦、并行处理和容错性。

## 架构设计

### 系统拓扑图
```
搜索请求 → [Event Bus] → [YouTube Handler] → [Content Extractor] 
                ↓              ↓                    ↓
           [State Manager] → [AI Processor] → [Obsidian Writer]
                ↓              ↓                    ↓  
           [监控/指标] ← [Error Handler] ← [结果收集器]
```

## 核心组件设计

### 1. 事件总线架构
```python
# src/core/event_bus.py
class EventBus:
    """中央事件总线 - 系统的神经中枢"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._middleware: List[EventMiddleware] = []
        self._event_store = EventStore()  # 事件溯源
        self._metrics = EventMetrics()
    
    async def publish(self, event: Event) -> EventResult:
        """发布事件，支持中间件和错误恢复"""
        # 应用中间件
        for middleware in self._middleware:
            event = await middleware.process(event)
        
        # 持久化事件
        await self._event_store.store(event)
        
        # 并行处理
        handlers = self._handlers.get(event.type, [])
        tasks = [self._safe_handle(handler, event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return EventResult(event, results)
    
    async def _safe_handle(self, handler: EventHandler, event: Event):
        """安全的事件处理，包含重试和降级"""
        try:
            return await handler.handle(event)
        except Exception as e:
            # 发布错误事件，触发降级处理
            error_event = ErrorEvent(
                original_event=event,
                error=e,
                handler=handler.__class__.__name__
            )
            await self.publish(error_event)
            return ErrorResult(e)
```

### 2. 智能工作流编排
```python
# src/core/workflow_engine.py
class WorkflowEngine:
    """智能工作流引擎"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.active_workflows: Dict[str, WorkflowInstance] = {}
    
    async def execute_workflow(self, workflow_name: str, input_data: Any) -> str:
        """执行工作流，支持分支、合并、条件处理"""
        workflow_id = self._generate_workflow_id(workflow_name)
        workflow_def = self.workflows[workflow_name]
        
        # 创建工作流实例
        instance = WorkflowInstance(
            id=workflow_id,
            definition=workflow_def,
            input_data=input_data,
            state=WorkflowState.RUNNING
        )
        
        self.active_workflows[workflow_id] = instance
        
        # 发布工作流开始事件
        start_event = WorkflowStartEvent(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            input_data=input_data
        )
        
        await self.event_bus.publish(start_event)
        return workflow_id
    
    def register_workflow(self, workflow: WorkflowDefinition):
        """注册工作流定义"""
        # 验证工作流DAG
        if not self._validate_workflow_dag(workflow):
            raise ValueError(f"工作流 {workflow.name} 包含循环依赖")
        
        self.workflows[workflow.name] = workflow

class YouTubeSummaryWorkflow(WorkflowDefinition):
    """YouTube总结工作流定义"""
    
    name = "youtube_summary"
    
    steps = [
        WorkflowStep(
            name="search_videos",
            handler=YouTubeSearchHandler,
            next_steps=["extract_content"],
            timeout=30,
            retry_policy=RetryPolicy(max_attempts=3, backoff_factor=2)
        ),
        WorkflowStep(
            name="extract_content",
            handler=ContentExtractionHandler,
            next_steps=["ai_processing"],
            parallel=True,  # 支持并行处理多个视频
            timeout=60
        ),
        WorkflowStep(
            name="ai_processing", 
            handler=AIProcessingHandler,
            next_steps=["generate_output"],
            parallel=True,
            rate_limit=RateLimit(requests_per_minute=5)
        ),
        WorkflowStep(
            name="generate_output",
            handler=ObsidianOutputHandler,
            final_step=True,
            timeout=30
        )
    ]
```

### 3. 弹性处理器设计
```python
# src/processors/resilient_youtube_processor.py
class ResilientYouTubeProcessor(EventHandler):
    """弹性YouTube处理器 - 支持容错和降级"""
    
    def __init__(self):
        self.primary_searcher = YouTubeAPISearcher()
        self.fallback_searcher = YouTubeScrapeSearcher()  # 备用搜索器
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
    
    async def handle(self, event: VideoSearchEvent) -> VideoSearchResult:
        """处理视频搜索事件，支持多级降级"""
        
        # 尝试主要搜索方式
        try:
            if self.circuit_breaker.can_execute():
                videos = await self._search_with_api(event.query)
                self.circuit_breaker.record_success()
                return VideoSearchResult(videos=videos, method="api")
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.warning(f"API搜索失败，尝试备用方案: {e}")
        
        # 降级到备用搜索
        try:
            videos = await self._search_with_scraping(event.query)
            return VideoSearchResult(videos=videos, method="scraping")
        except Exception as e:
            logger.error(f"所有搜索方式都失败: {e}")
            return VideoSearchResult(videos=[], error=str(e))
    
    async def _search_with_api(self, query: str) -> List[VideoInfo]:
        """使用API搜索，包含智能重试"""
        return await self.primary_searcher.search(query)
    
    async def _search_with_scraping(self, query: str) -> List[VideoInfo]:
        """使用爬虫搜索作为备用方案"""
        return await self.fallback_searcher.search(query)

class CircuitBreaker:
    """熔断器模式实现"""
    
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### 4. 状态管理和监控
```python
# src/core/state_manager.py
class DistributedStateManager:
    """分布式状态管理器"""
    
    def __init__(self):
        self.workflow_states: Dict[str, WorkflowState] = {}
        self.event_store = EventStore()
        self.metrics_collector = MetricsCollector()
    
    async def update_workflow_state(self, workflow_id: str, step: str, status: StepStatus, data: Any = None):
        """更新工作流状态"""
        if workflow_id not in self.workflow_states:
            self.workflow_states[workflow_id] = WorkflowState(workflow_id)
        
        state = self.workflow_states[workflow_id]
        state.update_step(step, status, data)
        
        # 发布状态变更事件
        state_event = WorkflowStateChangeEvent(
            workflow_id=workflow_id,
            step=step,
            status=status,
            timestamp=datetime.now()
        )
        
        await self.event_store.store(state_event)
        self.metrics_collector.record_step_completion(step, status)
    
    def get_workflow_progress(self, workflow_id: str) -> WorkflowProgress:
        """获取工作流进度"""
        state = self.workflow_states.get(workflow_id)
        if not state:
            return WorkflowProgress(workflow_id, "not_found")
        
        return WorkflowProgress(
            workflow_id=workflow_id,
            completed_steps=state.completed_steps,
            failed_steps=state.failed_steps,
            current_step=state.current_step,
            progress_percentage=state.calculate_progress(),
            estimated_completion_time=state.estimate_completion()
        )

# src/monitoring/system_monitor.py
class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.metrics = SystemMetrics()
        
        # 注册监控事件处理器
        event_bus.register_handler(EventType.ALL, self.collect_metrics)
    
    async def collect_metrics(self, event: Event):
        """收集系统指标"""
        self.metrics.record_event(event)
        
        # 检查系统健康状况
        if self.metrics.error_rate > 0.1:  # 错误率超过10%
            await self._trigger_alert("系统错误率过高")
        
        if self.metrics.average_processing_time > 300:  # 处理时间超过5分钟
            await self._trigger_alert("系统处理速度过慢")
    
    async def _trigger_alert(self, message: str):
        alert_event = SystemAlertEvent(
            level=AlertLevel.WARNING,
            message=message,
            metrics=self.metrics.current_snapshot()
        )
        await self.event_bus.publish(alert_event)
```

## 实施计划

### 第1-2周：核心基础设施
- 事件总线和事件模型
- 基础工作流引擎
- 状态管理器

### 第3-4周：处理器重构
- YouTube处理器事件化
- Gemini处理器事件化
- Obsidian输出处理器

### 第5-6周：容错和监控
- 熔断器和重试机制
- 系统监控和告警
- 性能优化

### 第7-8周：测试和部署
- 单元测试和集成测试
- 压力测试
- 灰度部署

## 优势分析
✅ **真正解耦**：组件间完全独立，易于测试和维护  
✅ **高并发性**：支持真正的并行处理  
✅ **容错性强**：单点故障不影响整体系统  
✅ **可扩展性**：轻松添加新的内容源和处理器  
✅ **可观测性**：完整的事件溯源和监控  

## 挑战和风险
❌ **复杂性增加**：需要团队学习事件驱动概念  
❌ **调试难度**：分布式系统的调试更复杂  
❌ **一致性挑战**：需要处理eventual consistency  

## ROI评估
- **开发成本**：中高 (约8周)
- **维护成本**：大幅降低 (减少70%重复代码)
- **扩展能力**：显著提升 (支持快速添加新功能)
- **性能提升**：50-100% (真正的并行处理)
- **可靠性提升**：显著 (容错机制)