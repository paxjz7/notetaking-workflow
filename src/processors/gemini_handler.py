"""
事件驱动的Gemini处理器
"""
import asyncio
from typing import List, Dict, Optional, Any
from loguru import logger

from ..core.event_system import EventHandler, Event, EventType
from ..core.circuit_breaker import ResilientExecutor, CircuitBreakerConfig, CircuitBreakerOpenError
from ..gemini_summarizer import GeminiSummarizer, VideoSummary
from ..youtube_processor import VideoInfo

class GeminiSummaryProcessor:
    """
    Gemini总结处理器 - 使用基础处理器模式
    """
    
    def __init__(self, gemini_summarizer: GeminiSummarizer):
        self.name = "GeminiSummaryProcessor"
        self.gemini_summarizer = gemini_summarizer
        
        # 创建弹性执行器
        circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=300,  # 5分钟恢复时间
            success_threshold=2,
            timeout=120.0  # 2分钟超时
        )
        self.resilient_executor = ResilientExecutor(circuit_config, max_retries=2)
    
    async def process_single(self, video: VideoInfo) -> VideoSummary:
        """处理单个视频总结"""
        logger.info(f"开始AI总结视频: {video.title}")
        
        # 使用弹性执行器进行总结
        async def summarize_operation():
            return await self.gemini_summarizer.summarize_video(video)
        
        async def fallback_operation():
            # 降级方案：使用简化的总结模板
            logger.warning(f"使用降级方案总结视频: {video.title}")
            return self._create_fallback_summary(video)
        
        try:
            summary = await self.resilient_executor.execute_with_retry(
                summarize_operation,
                fallback_operation
            )
            
            logger.success(f"视频总结完成: {video.title}")
            return summary
            
        except Exception as e:
            logger.error(f"视频总结失败: {video.title}, 错误: {e}")
            # 返回最基础的降级总结
            return self._create_minimal_summary(video)
    
    def _create_fallback_summary(self, video: VideoInfo) -> VideoSummary:
        """创建降级总结"""
        return VideoSummary(
            title=video.title,
            url=video.url,
            channel=video.channel,
            duration=video.duration,
            upload_date=video.upload_date,
            summary=f"[降级总结] 这是一个来自 {video.channel} 的视频，标题为：{video.title}。由于AI服务暂时不可用，暂时无法提供详细总结。",
            key_points=[
                f"视频标题：{video.title}",
                f"发布频道：{video.channel}",
                f"视频时长：{video.duration}",
                "详细内容需要AI服务恢复后重新处理"
            ],
            tags=["待处理", "降级模式", video.channel.replace(" ", "_")],
            video_id=video.video_id
        )
    
    def _create_minimal_summary(self, video: VideoInfo) -> VideoSummary:
        """创建最基础的总结"""
        return VideoSummary(
            title=video.title,
            url=video.url,
            channel=video.channel,
            duration=video.duration,
            upload_date=video.upload_date,
            summary=f"[基础信息] 视频标题：{video.title}，来源：{video.channel}",
            key_points=[f"来源：{video.url}"],
            tags=["未处理"],
            video_id=video.video_id
        )

class GeminiProcessingHandler(EventHandler):
    """
    Gemini AI处理事件处理器
    """
    
    def __init__(self, gemini_summarizer: GeminiSummarizer):
        self.processor = GeminiSummaryProcessor(gemini_summarizer)
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type == EventType.AI_PROCESSING_STARTED
    
    async def handle(self, event: Event) -> Optional[Event]:
        """处理AI总结事件"""
        try:
            extracted_content = event.data.get('extracted_content', [])
            if not extracted_content:
                logger.warning("没有提取到视频内容进行AI处理")
                return Event(
                    event_type=EventType.AI_PROCESSING_FAILED,
                    data={'error': 'No content to process'},
                    correlation_id=event.correlation_id
                )
            
            # 转换提取的内容为VideoInfo对象
            videos = []
            for content in extracted_content:
                video_info_data = content.get('video_info', {})
                transcript = content.get('transcript', '')
                
                # 创建增强的VideoInfo对象（包含transcript）
                video = VideoInfo(
                    title=video_info_data.get('title', ''),
                    url=video_info_data.get('url', ''),
                    description=video_info_data.get('description', ''),
                    duration=video_info_data.get('duration', ''),
                    view_count=video_info_data.get('view_count', ''),
                    upload_date=video_info_data.get('upload_date', ''),
                    channel=video_info_data.get('channel', ''),
                    video_id=video_info_data.get('video_id', ''),
                    transcript=transcript
                )
                videos.append(video)
            
            logger.info(f"开始AI处理 {len(videos)} 个视频")
            
            # 并行处理视频总结
            tasks = [self.processor.process_single(video) for video in videos]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 提取成功的总结
            successful_summaries = []
            failed_summaries = []
            
            for result in results:
                if isinstance(result, Exception):
                    failed_summaries.append({'error': str(result)})
                else:
                    successful_summaries.append(result)
            
            logger.info(f"AI处理完成: 成功 {len(successful_summaries)}, 失败 {len(failed_summaries)}")
            
            # 获取处理指标
            circuit_stats = self.processor.resilient_executor.get_circuit_stats()
            
            return Event(
                event_type=EventType.AI_PROCESSING_COMPLETED,
                data={
                    'summaries': [summary.__dict__ for summary in successful_summaries],
                    'circuit_breaker_stats': circuit_stats,
                    'success_count': len(successful_summaries),
                    'failure_count': len(failed_summaries),
                    'failed_items': failed_summaries
                },
                correlation_id=event.correlation_id,
                metadata={'handler': self.__class__.__name__}
            )
            
        except Exception as e:
            logger.error(f"AI处理事件处理失败: {e}")
            return Event(
                event_type=EventType.AI_PROCESSING_FAILED,
                data={'error': str(e)},
                correlation_id=event.correlation_id
            )

class GeminiHealthMonitor:
    """
    Gemini服务健康监控器
    """
    
    def __init__(self, processor: GeminiSummaryProcessor):
        self.processor = processor
        self.health_checks = []
    
    async def check_health(self) -> Dict[str, Any]:
        """检查Gemini服务健康状况"""
        circuit_stats = self.processor.resilient_executor.get_circuit_stats()
        processing_metrics = self.processor.get_metrics()
        
        # 计算健康评分
        health_score = self._calculate_health_score(circuit_stats, processing_metrics)
        
        return {
            'service': 'gemini',
            'health_score': health_score,
            'circuit_breaker': circuit_stats,
            'processing_metrics': processing_metrics,
            'recommendations': self._get_recommendations(health_score, circuit_stats)
        }
    
    def _calculate_health_score(self, circuit_stats: Dict, metrics: Dict) -> float:
        """计算健康评分 (0-100)"""
        score = 100.0
        
        # 熔断器状态影响
        if circuit_stats['state'] == 'open':
            score -= 50
        elif circuit_stats['state'] == 'half_open':
            score -= 25
        
        # 错误率影响
        total_processed = metrics.get('total_processed', 1)
        if total_processed > 0:
            error_rate = metrics.get('error_count', 0) / total_processed
            score -= error_rate * 30
        
        # 平均处理时间影响
        avg_time = metrics.get('average_processing_time', 0)
        if avg_time > 60:  # 超过1分钟认为较慢
            score -= min(20, (avg_time - 60) / 30)
        
        return max(0, min(100, score))
    
    def _get_recommendations(self, health_score: float, circuit_stats: Dict) -> List[str]:
        """获取改进建议"""
        recommendations = []
        
        if health_score < 50:
            recommendations.append("系统健康状况较差，建议检查Gemini API配额和网络连接")
        
        if circuit_stats['state'] == 'open':
            recommendations.append("熔断器已开启，建议等待恢复或检查API密钥")
        
        if circuit_stats['failure_count'] > 3:
            recommendations.append("失败次数较多，建议检查API调用参数和网络稳定性")
        
        return recommendations