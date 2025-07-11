"""
基础处理器 - 解决DRY原则违反问题
"""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from loguru import logger

T = TypeVar('T')
R = TypeVar('R')

class ProcessingStatus(Enum):
    """处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ProcessingResult(Generic[T]):
    """通用处理结果"""
    data: Optional[T]
    status: ProcessingStatus
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass 
class RateLimitConfig:
    """速率限制配置"""
    max_requests_per_minute: int
    max_concurrent: int = 1
    retry_attempts: int = 3
    backoff_factor: float = 2.0

class BaseRateLimiter:
    """通用速率限制器 - 解决重复实现问题"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = []
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        
    async def acquire(self) -> bool:
        """获取处理许可"""
        async with self.semaphore:
            now = time.time()
            # 清理过期请求
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            # 检查是否达到限制
            if len(self.requests) >= self.config.max_requests_per_minute:
                wait_time = 60 - (now - self.requests[0])
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            self.requests.append(now)
            return True

class BaseProcessor(ABC, Generic[T, R]):
    """
    基础处理器抽象类 - 统一所有处理器的通用逻辑
    解决重复代码问题：错误处理、重试、日志、指标收集
    """
    
    def __init__(self, 
                 name: str,
                 rate_limit_config: Optional[RateLimitConfig] = None):
        self.name = name
        self.rate_limiter = BaseRateLimiter(rate_limit_config) if rate_limit_config else None
        self._metrics = {
            'total_processed': 0,
            'success_count': 0,
            'error_count': 0,
            'average_processing_time': 0.0
        }
    
    @abstractmethod
    async def _process_single(self, item: T) -> R:
        """子类必须实现的单项处理逻辑"""
        pass
    
    async def process(self, item: T) -> ProcessingResult[R]:
        """
        统一的处理入口 - 包含通用逻辑
        """
        start_time = time.time()
        
        try:
            # 速率限制
            if self.rate_limiter:
                await self.rate_limiter.acquire()
            
            logger.debug(f"{self.name}: 开始处理项目")
            
            # 执行具体处理逻辑
            result = await self._process_single(item)
            
            processing_time = time.time() - start_time
            self._update_metrics(True, processing_time)
            
            logger.success(f"{self.name}: 处理完成，耗时 {processing_time:.2f}s")
            
            return ProcessingResult(
                data=result,
                status=ProcessingStatus.COMPLETED,
                processing_time=processing_time,
                metadata={'processor': self.name}
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_metrics(False, processing_time)
            
            logger.error(f"{self.name}: 处理失败 - {e}")
            
            return ProcessingResult(
                data=None,
                status=ProcessingStatus.FAILED,
                error=str(e),
                processing_time=processing_time,
                metadata={'processor': self.name}
            )
    
    async def process_batch(self, 
                          items: List[T], 
                          max_concurrent: int = None) -> List[ProcessingResult[R]]:
        """
        批量处理 - 统一的并发控制逻辑
        """
        if not items:
            return []
        
        logger.info(f"{self.name}: 开始批量处理 {len(items)} 个项目")
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent or 3)
        
        async def limited_process(item):
            async with semaphore:
                return await self.process(item)
        
        # 并发执行
        tasks = [limited_process(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ProcessingResult(
                    data=None,
                    status=ProcessingStatus.FAILED,
                    error=str(result),
                    metadata={'processor': self.name, 'item_index': i}
                ))
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.status == ProcessingStatus.COMPLETED)
        logger.info(f"{self.name}: 批量处理完成 {success_count}/{len(items)}")
        
        return processed_results
    
    def _update_metrics(self, success: bool, processing_time: float):
        """更新处理指标"""
        self._metrics['total_processed'] += 1
        if success:
            self._metrics['success_count'] += 1
        else:
            self._metrics['error_count'] += 1
        
        # 计算平均处理时间
        total = self._metrics['total_processed']
        current_avg = self._metrics['average_processing_time']
        self._metrics['average_processing_time'] = (current_avg * (total - 1) + processing_time) / total
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取处理指标"""
        return self._metrics.copy()
    
    async def health_check(self) -> bool:
        """健康检查"""
        return True

class RetryMixin:
    """重试混入类 - 统一重试逻辑"""
    
    async def with_retry(self, 
                        operation,
                        max_attempts: int = 3,
                        backoff_factor: float = 2.0,
                        exceptions: tuple = (Exception,)):
        """
        通用重试装饰器逻辑
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return await operation()
            except exceptions as e:
                last_exception = e
                if attempt == max_attempts - 1:
                    break
                
                wait_time = backoff_factor ** attempt
                logger.warning(f"重试第 {attempt + 1} 次，等待 {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
        
        raise last_exception