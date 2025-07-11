"""
事件驱动的Obsidian处理器
"""
import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
from loguru import logger

from ..core.base_processor import BaseProcessor, ProcessingResult, RateLimitConfig
from ..core.event_system import EventHandler, Event, EventType
from ..obsidian_writer import ObsidianWriter
from ..gemini_summarizer import VideoSummary

class ObsidianDocumentProcessor(BaseProcessor[VideoSummary, str]):
    """
    Obsidian文档处理器 - 使用基础处理器模式
    """
    
    def __init__(self, obsidian_writer: ObsidianWriter):
        super().__init__(
            name="ObsidianDocumentProcessor",
            rate_limit_config=RateLimitConfig(
                max_requests_per_minute=30,  # 文件写入相对快速
                max_concurrent=5
            )
        )
        self.obsidian_writer = obsidian_writer
    
    async def _process_single(self, summary: VideoSummary) -> str:
        """处理单个视频总结，生成Obsidian文档"""
        logger.info(f"开始生成Obsidian文档: {summary.title}")
        
        # 模拟异步文件写入（实际上ObsidianWriter是同步的）
        def write_document():
            return self.obsidian_writer.write_video_summary(summary)
        
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, write_document)
        
        logger.success(f"Obsidian文档生成完成: {file_path}")
        return file_path

class ObsidianIndexProcessor:
    """
    Obsidian索引处理器 - 生成汇总索引
    """
    
    def __init__(self, obsidian_writer: ObsidianWriter):
        self.obsidian_writer = obsidian_writer
    
    async def create_index(self, summaries: List[VideoSummary], query: str) -> str:
        """创建索引文档"""
        logger.info(f"开始创建索引文档，包含 {len(summaries)} 个视频")
        
        def write_index():
            return self.obsidian_writer.create_index_document(summaries, query)
        
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        index_path = await loop.run_in_executor(None, write_index)
        
        logger.success(f"索引文档创建完成: {index_path}")
        return index_path

class ObsidianLinkProcessor:
    """
    Obsidian链接处理器 - 创建文档间链接
    """
    
    def __init__(self, obsidian_writer: ObsidianWriter):
        self.obsidian_writer = obsidian_writer
    
    async def create_cross_links(self, summaries: List[VideoSummary], created_files: List[str]) -> Dict[str, List[str]]:
        """创建文档间的交叉链接"""
        logger.info("开始创建文档间链接")
        
        # 分析标签相似性
        tag_relationships = self._analyze_tag_relationships(summaries)
        
        # 创建链接映射
        link_map = {}
        
        for i, summary in enumerate(summaries):
            current_file = created_files[i] if i < len(created_files) else None
            if not current_file:
                continue
            
            # 查找相关视频
            related_videos = self._find_related_videos(summary, summaries, tag_relationships)
            related_files = []
            
            for related_idx in related_videos:
                if related_idx < len(created_files):
                    related_files.append(created_files[related_idx])
            
            link_map[current_file] = related_files
        
        # 实际添加链接到文档中
        await self._update_documents_with_links(link_map)
        
        logger.success(f"链接创建完成，处理了 {len(link_map)} 个文档")
        return link_map
    
    def _analyze_tag_relationships(self, summaries: List[VideoSummary]) -> Dict[str, List[int]]:
        """分析标签关系"""
        tag_to_videos = {}
        
        for i, summary in enumerate(summaries):
            for tag in summary.tags:
                if tag not in tag_to_videos:
                    tag_to_videos[tag] = []
                tag_to_videos[tag].append(i)
        
        return tag_to_videos
    
    def _find_related_videos(self, current_summary: VideoSummary, 
                           all_summaries: List[VideoSummary],
                           tag_relationships: Dict[str, List[int]]) -> List[int]:
        """查找相关视频"""
        related_indices = set()
        
        # 基于共同标签查找相关视频
        for tag in current_summary.tags:
            if tag in tag_relationships:
                related_indices.update(tag_relationships[tag])
        
        # 移除自己
        current_index = next((i for i, s in enumerate(all_summaries) if s.video_id == current_summary.video_id), -1)
        if current_index in related_indices:
            related_indices.remove(current_index)
        
        # 限制相关视频数量
        return list(related_indices)[:3]
    
    async def _update_documents_with_links(self, link_map: Dict[str, List[str]]):
        """更新文档添加链接"""
        def update_single_document(file_path: str, related_files: List[str]):
            try:
                # 读取现有文档
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    return
                
                content = file_path_obj.read_text(encoding='utf-8')
                
                # 添加相关链接部分
                if related_files:
                    links_section = "\n\n## 相关视频\n\n"
                    for related_file in related_files:
                        # 提取文件名作为链接文本
                        link_name = Path(related_file).stem
                        links_section += f"- [[{link_name}]]\n"
                    
                    # 添加到文档末尾
                    content += links_section
                    
                    # 写回文件
                    file_path_obj.write_text(content, encoding='utf-8')
                    logger.debug(f"为文档 {file_path} 添加了 {len(related_files)} 个链接")
                
            except Exception as e:
                logger.error(f"更新文档链接失败 {file_path}: {e}")
        
        # 并发更新所有文档
        loop = asyncio.get_event_loop()
        tasks = []
        
        for file_path, related_files in link_map.items():
            task = loop.run_in_executor(None, update_single_document, file_path, related_files)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)

class ObsidianOutputHandler(EventHandler):
    """
    Obsidian输出事件处理器
    """
    
    def __init__(self, obsidian_writer: ObsidianWriter):
        self.document_processor = ObsidianDocumentProcessor(obsidian_writer)
        self.index_processor = ObsidianIndexProcessor(obsidian_writer)
        self.link_processor = ObsidianLinkProcessor(obsidian_writer)
    
    def can_handle(self, event_type: EventType) -> bool:
        return event_type == EventType.OUTPUT_GENERATION_STARTED
    
    async def handle(self, event: Event) -> Optional[Event]:
        """处理输出生成事件"""
        try:
            summaries_data = event.data.get('summaries', [])
            if not summaries_data:
                logger.warning("没有总结数据需要生成输出")
                return Event(
                    event_type=EventType.OUTPUT_GENERATION_FAILED,
                    data={'error': 'No summaries to generate output'},
                    correlation_id=event.correlation_id
                )
            
            # 转换为VideoSummary对象
            summaries = []
            for summary_data in summaries_data:
                summary = VideoSummary(
                    title=summary_data.get('title', ''),
                    url=summary_data.get('url', ''),
                    channel=summary_data.get('channel', ''),
                    duration=summary_data.get('duration', ''),
                    upload_date=summary_data.get('upload_date', ''),
                    summary=summary_data.get('summary', ''),
                    key_points=summary_data.get('key_points', []),
                    tags=summary_data.get('tags', []),
                    video_id=summary_data.get('video_id', '')
                )
                summaries.append(summary)
            
            logger.info(f"开始生成 {len(summaries)} 个Obsidian文档")
            
            # 1. 并行生成所有视频文档
            document_results = await self.document_processor.process_batch(
                summaries, 
                max_concurrent=3
            )
            
            # 提取成功创建的文件路径
            created_files = []
            failed_files = []
            
            for result in document_results:
                if result.status.value == 'completed' and result.data:
                    created_files.append(result.data)
                else:
                    failed_files.append({
                        'error': result.error,
                        'processing_time': result.processing_time
                    })
            
            logger.info(f"文档生成完成: 成功 {len(created_files)}, 失败 {len(failed_files)}")
            
            # 2. 创建索引文档
            query = event.data.get('input_data', {}).get('query', 'Unknown Query')
            try:
                index_file = await self.index_processor.create_index(summaries, query)
                created_files.append(index_file)
            except Exception as e:
                logger.error(f"创建索引文档失败: {e}")
                failed_files.append({'error': f"Index creation failed: {e}"})
            
            # 3. 创建文档间链接
            try:
                link_map = await self.link_processor.create_cross_links(summaries, created_files[:-1])  # 排除索引文件
            except Exception as e:
                logger.error(f"创建文档链接失败: {e}")
                link_map = {}
            
            # 获取处理指标
            metrics = self.document_processor.get_metrics()
            
            logger.success(f"Obsidian输出生成完成: {len(created_files)} 个文件")
            
            return Event(
                event_type=EventType.OUTPUT_GENERATED,
                data={
                    'created_files': created_files,
                    'failed_files': failed_files,
                    'link_map': link_map,
                    'processing_metrics': metrics,
                    'success_count': len(created_files),
                    'failure_count': len(failed_files),
                    'index_file': created_files[-1] if created_files else None
                },
                correlation_id=event.correlation_id,
                metadata={'handler': self.__class__.__name__}
            )
            
        except Exception as e:
            logger.error(f"输出生成事件处理失败: {e}")
            return Event(
                event_type=EventType.OUTPUT_GENERATION_FAILED,
                data={'error': str(e)},
                correlation_id=event.correlation_id
            )

class ObsidianSystemHealthChecker:
    """
    Obsidian系统健康检查器
    """
    
    def __init__(self, processor: ObsidianDocumentProcessor):
        self.processor = processor
    
    async def check_health(self) -> Dict[str, Any]:
        """检查Obsidian系统健康状况"""
        metrics = self.processor.get_metrics()
        
        # 检查文件系统权限
        vault_accessible = await self._check_vault_accessibility()
        
        # 计算健康评分
        health_score = self._calculate_health_score(metrics, vault_accessible)
        
        return {
            'service': 'obsidian',
            'health_score': health_score,
            'vault_accessible': vault_accessible,
            'processing_metrics': metrics,
            'recommendations': self._get_recommendations(health_score, vault_accessible)
        }
    
    async def _check_vault_accessibility(self) -> bool:
        """检查Obsidian vault是否可访问"""
        try:
            from ..config import Config
            vault_path = Path(Config.OBSIDIAN_VAULT_PATH)
            
            # 检查路径存在且可写
            if not vault_path.exists():
                return False
            
            # 尝试创建测试文件
            test_file = vault_path / ".health_check_test"
            test_file.write_text("test", encoding='utf-8')
            test_file.unlink()  # 删除测试文件
            
            return True
            
        except Exception as e:
            logger.error(f"Vault可访问性检查失败: {e}")
            return False
    
    def _calculate_health_score(self, metrics: Dict, vault_accessible: bool) -> float:
        """计算健康评分"""
        score = 100.0
        
        # Vault可访问性影响
        if not vault_accessible:
            score -= 70
        
        # 错误率影响
        total_processed = metrics.get('total_processed', 1)
        if total_processed > 0:
            error_rate = metrics.get('error_count', 0) / total_processed
            score -= error_rate * 20
        
        # 平均处理时间影响
        avg_time = metrics.get('average_processing_time', 0)
        if avg_time > 10:  # 文件写入超过10秒认为较慢
            score -= min(10, (avg_time - 10) / 5)
        
        return max(0, min(100, score))
    
    def _get_recommendations(self, health_score: float, vault_accessible: bool) -> List[str]:
        """获取改进建议"""
        recommendations = []
        
        if not vault_accessible:
            recommendations.append("Obsidian vault不可访问，请检查路径配置和文件权限")
        
        if health_score < 70:
            recommendations.append("文档生成系统健康状况较差，建议检查磁盘空间和文件权限")
        
        return recommendations