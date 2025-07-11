"""
熔断器模式实现 - 提供容错和降级能力
"""
import time
import asyncio
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass
from loguru import logger

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 正常状态，允许请求通过
    OPEN = "open"           # 熔断状态，拒绝所有请求
    HALF_OPEN = "half_open" # 半开状态，允许少量请求测试

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5          # 失败阈值
    recovery_timeout: int = 60          # 恢复超时时间（秒）
    success_threshold: int = 3          # 半开状态成功阈值
    timeout: float = 30.0               # 操作超时时间

class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_request_time: Optional[float] = None
        
    def can_execute(self) -> bool:
        """检查是否可以执行操作"""
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # 检查是否到了尝试恢复的时间
            if (self.last_failure_time and 
                current_time - self.last_failure_time >= self.config.recovery_timeout):
                self._transition_to_half_open()
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """记录成功操作"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # 重置失败计数
            self.failure_count = 0
        
        self.last_request_time = time.time()
        logger.debug(f"熔断器记录成功，当前状态: {self.state.value}")
    
    def record_failure(self):
        """记录失败操作"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.last_request_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            # 半开状态下失败，直接回到开启状态
            self._transition_to_open()
        
        logger.warning(f"熔断器记录失败，失败次数: {self.failure_count}, 当前状态: {self.state.value}")
    
    def _transition_to_open(self):
        """转换到开启状态"""
        self.state = CircuitState.OPEN
        self.success_count = 0
        logger.warning(f"熔断器开启，失败次数: {self.failure_count}")
    
    def _transition_to_half_open(self):
        """转换到半开状态"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        logger.info("熔断器进入半开状态，开始测试恢复")
    
    def _transition_to_closed(self):
        """转换到关闭状态"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info("熔断器恢复正常状态")
    
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """
        执行操作，带有熔断器保护
        
        Args:
            operation: 要执行的操作
            *args, **kwargs: 操作参数
            
        Returns:
            操作结果
            
        Raises:
            CircuitBreakerOpenError: 熔断器开启时
            TimeoutError: 操作超时
            其他异常: 操作本身的异常
        """
        if not self.can_execute():
            raise CircuitBreakerOpenError("熔断器处于开启状态，拒绝执行操作")
        
        try:
            # 使用超时控制
            result = await asyncio.wait_for(
                operation(*args, **kwargs), 
                timeout=self.config.timeout
            )
            self.record_success()
            return result
            
        except asyncio.TimeoutError as e:
            self.record_failure()
            logger.error(f"操作超时: {e}")
            raise TimeoutError(f"操作超时 ({self.config.timeout}s)")
        except Exception as e:
            self.record_failure()
            logger.error(f"操作执行失败: {e}")
            raise
    
    def get_stats(self) -> dict:
        """获取熔断器统计信息"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
            'last_request_time': self.last_request_time,
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'recovery_timeout': self.config.recovery_timeout,
                'success_threshold': self.config.success_threshold,
                'timeout': self.config.timeout
            }
        }

class CircuitBreakerOpenError(Exception):
    """熔断器开启异常"""
    pass

class ResilientExecutor:
    """弹性执行器 - 结合熔断器和重试机制"""
    
    def __init__(self, 
                 circuit_config: CircuitBreakerConfig,
                 max_retries: int = 3,
                 backoff_factor: float = 2.0):
        self.circuit_breaker = CircuitBreaker(circuit_config)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    async def execute_with_retry(self, 
                               operation: Callable,
                               fallback: Optional[Callable] = None,
                               *args, **kwargs) -> Any:
        """
        执行操作，带有重试和降级机制
        
        Args:
            operation: 主要操作
            fallback: 降级操作
            *args, **kwargs: 操作参数
            
        Returns:
            操作结果
        """
        last_exception = None
        
        # 尝试主要操作（带重试）
        for attempt in range(self.max_retries + 1):
            try:
                return await self.circuit_breaker.execute(operation, *args, **kwargs)
            except CircuitBreakerOpenError:
                logger.warning("熔断器开启，跳过重试")
                break
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor ** attempt
                    logger.warning(f"操作失败，{wait_time}s后重试 (第{attempt + 1}次): {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"操作重试失败，达到最大重试次数: {e}")
        
        # 如果主要操作失败，尝试降级操作
        if fallback:
            try:
                logger.info("尝试执行降级操作")
                result = await fallback(*args, **kwargs)
                logger.info("降级操作执行成功")
                return result
            except Exception as e:
                logger.error(f"降级操作也失败: {e}")
                raise e
        
        # 如果没有降级操作，抛出最后的异常
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("操作执行失败，没有可用的降级方案")
    
    def get_circuit_stats(self) -> dict:
        """获取熔断器统计信息"""
        return self.circuit_breaker.get_stats()

# 便捷函数：为不同服务创建熔断器
def create_api_circuit_breaker() -> CircuitBreaker:
    """创建API调用熔断器"""
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=3,
        timeout=30.0
    )
    return CircuitBreaker(config)

def create_database_circuit_breaker() -> CircuitBreaker:
    """创建数据库调用熔断器"""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30,
        success_threshold=2,
        timeout=10.0
    )
    return CircuitBreaker(config)

def create_external_service_circuit_breaker() -> CircuitBreaker:
    """创建外部服务调用熔断器"""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120,
        success_threshold=5,
        timeout=60.0
    )
    return CircuitBreaker(config)