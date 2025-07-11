"""
Gemini API总结模块
"""
import asyncio
import time
from typing import Dict, List, Optional
from loguru import logger
import google.generativeai as genai
from dataclasses import dataclass

from .config import Config
from .youtube_processor import VideoInfo

@dataclass
class VideoSummary:
    """视频总结数据类"""
    title: str
    url: str
    channel: str
    duration: str
    upload_date: str
    summary: str
    key_points: List[str]
    tags: List[str]
    video_id: str

class RateLimiter:
    """API速率限制器"""
    
    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.requests = []
        
    async def acquire(self):
        """获取API调用许可"""
        now = time.time()
        # 清理1分钟前的请求记录
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        # 如果请求数量达到限制，等待
        if len(self.requests) >= self.max_requests:
            wait_time = 60 - (now - self.requests[0])
            if wait_time > 0:
                logger.info(f"达到速率限制，等待 {wait_time:.1f} 秒")
                await asyncio.sleep(wait_time)
                return await self.acquire()
        
        # 记录新请求
        self.requests.append(now)

class GeminiSummarizer:
    """Gemini API总结器"""
    
    def __init__(self):
        self.config = Config()
        
        # 配置Gemini API
        genai.configure(api_key=self.config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # 速率限制器
        self.rate_limiter = RateLimiter(self.config.GEMINI_RPM_LIMIT)
        
        # 总结提示词模板
        self.summary_prompt = """
请对以下YouTube视频内容进行详细总结。

视频标题: {title}
频道: {channel}
时长: {duration}
上传时间: {upload_date}
视频链接: {url}

视频内容/字幕:
{content}

请按以下格式提供总结:

## 内容概要
[用2-3段话概括视频的主要内容]

## 关键要点
[列出3-5个主要观点，每个要点用一行]

## 推荐标签
[基于内容提供5-8个相关标签，用逗号分隔]

请确保总结准确、简洁且有价值。如果内容是中文，请用中文回答；如果是英文，请用中文总结。
"""
    
    async def summarize_video(self, video_info: VideoInfo) -> Optional[VideoSummary]:
        """
        总结单个视频
        
        Args:
            video_info: 视频信息
            
        Returns:
            视频总结
        """
        await self.rate_limiter.acquire()
        
        logger.info(f"正在总结视频: {video_info.title}")
        
        try:
            # 准备输入内容
            content = video_info.transcript if video_info.transcript else video_info.description
            if not content:
                logger.warning(f"视频无可用内容进行总结: {video_info.title}")
                return None
            
            # 生成提示词
            prompt = self.summary_prompt.format(
                title=video_info.title,
                channel=video_info.channel,
                duration=video_info.duration,
                upload_date=video_info.upload_date,
                url=video_info.url,
                content=content[:8000]  # 限制内容长度避免超出token限制
            )
            
            # 调用Gemini API
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt
            )
            
            if not response.text:
                logger.error(f"Gemini API未返回有效响应: {video_info.title}")
                return None
            
            # 解析响应
            summary_data = self._parse_summary(response.text, video_info)
            
            logger.success(f"成功总结视频: {video_info.title}")
            return summary_data
            
        except Exception as e:
            logger.error(f"总结视频时发生错误 {video_info.title}: {e}")
            return None
    
    def _parse_summary(self, response_text: str, video_info: VideoInfo) -> VideoSummary:
        """
        解析Gemini响应文本
        
        Args:
            response_text: Gemini响应文本
            video_info: 原始视频信息
            
        Returns:
            解析后的视频总结
        """
        lines = response_text.strip().split('\n')
        
        summary = ""
        key_points = []
        tags = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 识别段落标题
            if line.startswith('## 内容概要'):
                current_section = 'summary'
                continue
            elif line.startswith('## 关键要点'):
                current_section = 'key_points'
                continue
            elif line.startswith('## 推荐标签'):
                current_section = 'tags'
                continue
            
            # 根据当前段落处理内容
            if current_section == 'summary':
                if not line.startswith('##'):
                    summary += line + ' '
            elif current_section == 'key_points':
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    key_points.append(line[1:].strip())
                elif line and not line.startswith('##'):
                    key_points.append(line)
            elif current_section == 'tags':
                if line and not line.startswith('##'):
                    # 解析标签，可能用逗号、空格或其他分隔符
                    tag_list = [tag.strip() for tag in line.replace('，', ',').split(',')]
                    tags.extend([tag for tag in tag_list if tag])
        
        # 清理和去重
        summary = summary.strip()
        key_points = [point for point in key_points if point][:5]  # 最多5个要点
        tags = list(set([tag for tag in tags if tag]))[:8]  # 最多8个标签，去重
        
        return VideoSummary(
            title=video_info.title,
            url=video_info.url,
            channel=video_info.channel,
            duration=video_info.duration,
            upload_date=video_info.upload_date,
            summary=summary,
            key_points=key_points,
            tags=tags,
            video_id=video_info.video_id
        )
    
    async def summarize_videos(self, videos: List[VideoInfo]) -> List[VideoSummary]:
        """
        批量总结视频
        
        Args:
            videos: 视频信息列表
            
        Returns:
            视频总结列表
        """
        if not videos:
            return []
        
        logger.info(f"开始总结 {len(videos)} 个视频")
        
        # 顺序处理以遵守速率限制
        summaries = []
        for i, video in enumerate(videos, 1):
            logger.info(f"处理进度: {i}/{len(videos)}")
            summary = await self.summarize_video(video)
            if summary:
                summaries.append(summary)
        
        logger.success(f"成功总结 {len(summaries)} 个视频")
        return summaries