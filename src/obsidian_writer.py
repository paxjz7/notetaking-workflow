"""
Obsidian文档生成模块
"""
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from loguru import logger

from .config import Config
from .gemini_summarizer import VideoSummary

class ObsidianWriter:
    """Obsidian文档写入器"""
    
    def __init__(self):
        self.config = Config()
        self.vault_path = Path(self.config.OBSIDIAN_VAULT_PATH)
        
        # 创建YouTube视频文件夹
        self.youtube_folder = self.vault_path / "YouTube视频总结"
        self.youtube_folder.mkdir(exist_ok=True)
        
    def _sanitize_filename(self, title: str) -> str:
        """
        清理文件名，移除不合法字符
        
        Args:
            title: 原始标题
            
        Returns:
            清理后的文件名
        """
        # 移除或替换不合法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # 限制长度
        if len(sanitized) > 100:
            sanitized = sanitized[:100] + "..."
            
        return sanitized
    
    def _generate_markdown_content(self, summary: VideoSummary, related_videos: List[VideoSummary] = None) -> str:
        """
        生成Markdown内容
        
        Args:
            summary: 视频总结
            related_videos: 相关视频列表
            
        Returns:
            Markdown内容
        """
        content = f"""# {summary.title}

## 视频信息
- **频道**: {summary.channel}
- **时长**: {summary.duration}
- **上传时间**: {summary.upload_date}
- **视频链接**: [{summary.title}]({summary.url})
- **视频ID**: {summary.video_id}

## 内容总结
{summary.summary}

## 关键要点
"""
        
        # 添加关键要点
        for i, point in enumerate(summary.key_points, 1):
            content += f"{i}. {point}\n"
        
        # 添加标签
        if summary.tags:
            content += f"\n## 标签\n"
            for tag in summary.tags:
                content += f"#{tag} "
            content += "\n"
        
        # 添加相关视频链接
        if related_videos:
            content += f"\n## 相关视频\n"
            for related in related_videos:
                if related.video_id != summary.video_id:  # 排除自己
                    filename = self._sanitize_filename(related.title)
                    content += f"- [[{filename}]]\n"
        
        # 添加元数据
        content += f"""
## 元数据
- 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 来源: YouTube视频总结系统
- 原始链接: {summary.url}

---
*此文档由AI自动生成，基于YouTube视频内容总结*
"""
        
        return content
    
    def write_video_summary(self, summary: VideoSummary, related_videos: List[VideoSummary] = None) -> Path:
        """
        写入单个视频总结文档
        
        Args:
            summary: 视频总结
            related_videos: 相关视频列表
            
        Returns:
            生成的文件路径
        """
        # 生成文件名
        filename = self._sanitize_filename(summary.title)
        if not filename.endswith('.md'):
            filename += '.md'
        
        file_path = self.youtube_folder / filename
        
        # 生成内容
        content = self._generate_markdown_content(summary, related_videos)
        
        try:
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.success(f"成功写入文档: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"写入文档时发生错误: {e}")
            raise
    
    def write_all_summaries(self, summaries: List[VideoSummary]) -> List[Path]:
        """
        写入所有视频总结文档并创建互相连接
        
        Args:
            summaries: 视频总结列表
            
        Returns:
            生成的文件路径列表
        """
        if not summaries:
            logger.warning("没有视频总结需要写入")
            return []
        
        logger.info(f"开始写入 {len(summaries)} 个视频总结文档")
        
        created_files = []
        
        # 为每个视频创建文档
        for summary in summaries:
            try:
                file_path = self.write_video_summary(summary, summaries)
                created_files.append(file_path)
            except Exception as e:
                logger.error(f"写入视频总结失败 {summary.title}: {e}")
                continue
        
        # 创建索引文档
        if created_files:
            index_path = self._create_index_document(summaries)
            if index_path:
                created_files.append(index_path)
        
        logger.success(f"成功创建 {len(created_files)} 个文档")
        return created_files
    
    def _create_index_document(self, summaries: List[VideoSummary]) -> Path:
        """
        创建索引文档
        
        Args:
            summaries: 视频总结列表
            
        Returns:
            索引文档路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        index_filename = f"YouTube视频总结索引_{timestamp}.md"
        index_path = self.youtube_folder / index_filename
        
        # 生成索引内容
        content = f"""# YouTube视频总结索引

> 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 视频数量: {len(summaries)}

## 视频列表

"""
        
        for i, summary in enumerate(summaries, 1):
            filename = self._sanitize_filename(summary.title)
            content += f"{i}. [[{filename}]] - {summary.channel} ({summary.duration})\n"
        
        # 按频道分组
        channel_groups = {}
        for summary in summaries:
            channel = summary.channel
            if channel not in channel_groups:
                channel_groups[channel] = []
            channel_groups[channel].append(summary)
        
        if len(channel_groups) > 1:
            content += f"\n## 按频道分组\n\n"
            for channel, videos in channel_groups.items():
                content += f"### {channel}\n"
                for video in videos:
                    filename = self._sanitize_filename(video.title)
                    content += f"- [[{filename}]]\n"
                content += "\n"
        
        # 添加所有标签
        all_tags = set()
        for summary in summaries:
            all_tags.update(summary.tags)
        
        if all_tags:
            content += f"## 所有标签\n\n"
            for tag in sorted(all_tags):
                content += f"#{tag} "
            content += "\n"
        
        content += f"""
---
*此索引由YouTube视频总结系统自动生成*
"""
        
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.success(f"成功创建索引文档: {index_path}")
            return index_path
            
        except Exception as e:
            logger.error(f"创建索引文档时发生错误: {e}")
            return None
    
    def create_connection_map(self, summaries: List[VideoSummary]) -> Dict[str, List[str]]:
        """
        创建视频之间的连接映射
        
        Args:
            summaries: 视频总结列表
            
        Returns:
            连接映射字典
        """
        connections = {}
        
        for summary in summaries:
            filename = self._sanitize_filename(summary.title)
            related = []
            
            # 基于标签找相关视频
            for other in summaries:
                if other.video_id == summary.video_id:
                    continue
                    
                # 计算标签重叠度
                common_tags = set(summary.tags) & set(other.tags)
                if len(common_tags) >= 1:  # 至少有一个共同标签
                    other_filename = self._sanitize_filename(other.title)
                    related.append(other_filename)
            
            connections[filename] = related
        
        return connections