"""
重构的YouTube处理器 - 基于事件驱动架构
解决原有代码的DRY违反和架构问题
"""
from typing import List, Dict, Optional
from loguru import logger

from ..core.base_processor import BaseProcessor, ProcessingResult, RateLimitConfig, RetryMixin
from ..core.event_system import EventHandler, Event, EventType
from ..youtube_processor import VideoInfo, YouTubeProcessor as OriginalYouTubeProcessor

class YouTubeSearchHandler(EventHandler, RetryMixin):
    """
    YouTube搜索事件处理器
    基于事件驱动架构，解耦搜索逻辑
    """
    
    def __init__(self, processor: OriginalYouTubeProcessor):
        self.processor = processor
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type == EventType.CONTENT_SEARCH_STARTED
    
    async def handle(self, event: Event) -> Optional[Event]:
        """处理内容搜索事件"""
        try:
            search_query = event.data.get('query') if isinstance(event.data, dict) else event.data
            max_results = event.data.get('max_results', 3) if isinstance(event.data, dict) else 3
            
            logger.info(f"开始搜索YouTube视频: {search_query}")
            
            # 使用重试机制搜索视频
            videos = await self.with_retry(
                lambda: self.processor.search_videos(search_query, max_results),
                max_attempts=3
            )
            
            # 发布内容发现事件
            return Event(
                event_type=EventType.CONTENT_FOUND,
                data={
                    'videos': [video.__dict__ for video in videos],
                    'search_query': search_query,
                    'count': len(videos)
                },
                correlation_id=event.correlation_id,
                metadata={'source': 'youtube', 'handler': self.__class__.__name__}
            )
            
        except Exception as e:
            logger.error(f"YouTube搜索失败: {e}")
            return Event(
                event_type=EventType.CONTENT_SEARCH_FAILED,
                data={'error': str(e), 'query': search_query},
                correlation_id=event.correlation_id
            )

class YouTubeContentExtractor(BaseProcessor[VideoInfo, Dict]):
    """
    YouTube内容提取器
    使用基础处理器模式，统一错误处理和指标收集
    """
    
    def __init__(self, processor: OriginalYouTubeProcessor):
        super().__init__(
            name="YouTubeContentExtractor",
            rate_limit_config=RateLimitConfig(
                max_requests_per_minute=10,
                max_concurrent=3
            )
        )
        self.processor = processor
    
    async def _process_single(self, video: VideoInfo) -> Dict:
        """提取单个视频的详细内容"""
        logger.info(f"提取视频内容: {video.title}")
        
        # 获取详细信息
        detailed_info = await self.processor.get_video_details(video.url)
        
        # 尝试获取字幕
        transcript = await self.processor.extract_transcript(video.url)
        
        return {
            'video_info': detailed_info.__dict__,
            'transcript': transcript,
            'extraction_method': 'transcript' if transcript else 'description'
        }

class YouTubeExtractionHandler(EventHandler):
    """
    YouTube内容提取事件处理器
    连接事件系统和内容提取器
    """
    
    def __init__(self, extractor: YouTubeContentExtractor):
        self.extractor = extractor
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type == EventType.CONTENT_EXTRACTION_STARTED
    
    async def handle(self, event: Event) -> Optional[Event]:
        """处理内容提取事件"""
        try:
            videos_data = event.data.get('videos', [])
            if not videos_data:
                return Event(
                    event_type=EventType.CONTENT_EXTRACTION_FAILED,
                    data={'error': 'No videos to extract'},
                    correlation_id=event.correlation_id
                )
            
            # 转换为VideoInfo对象
            videos = []
            for video_data in videos_data:
                video = VideoInfo(
                    title=video_data['title'],
                    url=video_data['url'],
                    description=video_data['description'],
                    duration=video_data['duration'],
                    view_count=video_data['view_count'],
                    upload_date=video_data['upload_date'],
                    channel=video_data['channel'],
                    video_id=video_data['video_id']
                )
                videos.append(video)
            
            # 批量提取内容
            results = await self.extractor.process_batch(videos, max_concurrent=3)
            
            # 统计成功和失败的数量
            successful_extractions = [r for r in results if r.status.value == 'completed']
            failed_extractions = [r for r in results if r.status.value == 'failed']
            
            logger.info(f"内容提取完成: 成功 {len(successful_extractions)}, 失败 {len(failed_extractions)}")
            
            return Event(
                event_type=EventType.CONTENT_EXTRACTED,
                data={
                    'extracted_content': [r.data for r in successful_extractions],
                    'extraction_metrics': self.extractor.get_metrics(),
                    'success_count': len(successful_extractions),
                    'failure_count': len(failed_extractions)
                },
                correlation_id=event.correlation_id,
                metadata={'handler': self.__class__.__name__}
            )
            
        except Exception as e:
            logger.error(f"内容提取处理失败: {e}")
            return Event(
                event_type=EventType.CONTENT_EXTRACTION_FAILED,
                data={'error': str(e)},
                correlation_id=event.correlation_id
            )

# 工厂函数 - 创建YouTube处理器组件
def create_youtube_handlers(original_processor: OriginalYouTubeProcessor) -> List[EventHandler]:
    """
    创建YouTube相关的事件处理器
    
    Returns:
        List[EventHandler]: YouTube处理器列表
    """
    extractor = YouTubeContentExtractor(original_processor)
    
    return [
        YouTubeSearchHandler(original_processor),
        YouTubeExtractionHandler(extractor)
    ]

# 系统集成示例
class YouTubeSystemIntegration:
    """
    YouTube系统集成类
    展示如何将新架构与现有系统集成
    """
    
    def __init__(self, event_bus, original_processor: OriginalYouTubeProcessor):
        self.event_bus = event_bus
        self.original_processor = original_processor
        
        # 注册所有处理器
        handlers = create_youtube_handlers(original_processor)
        for handler in handlers:
            event_bus.register_handler(handler)
        
        logger.info("YouTube系统集成完成")
    
    async def search_and_extract(self, query: str, correlation_id: str = None) -> str:
        """
        便捷方法：搜索并提取YouTube内容
        """
        # 发布搜索事件
        search_event = Event(
            event_type=EventType.CONTENT_SEARCH_STARTED,
            data={'query': query, 'max_results': 3},
            correlation_id=correlation_id
        )
        
        await self.event_bus.publish_and_wait(search_event)
        return search_event.correlation_id