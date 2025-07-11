"""
YouTube视频搜索和处理模块
"""
import json
import asyncio
from typing import List, Dict, Optional
from pathlib import Path
from loguru import logger
from youtubesearchpython import VideosSearch
import yt_dlp
from dataclasses import dataclass
from datetime import datetime

from .config import Config

@dataclass
class VideoInfo:
    """视频信息数据类"""
    title: str
    url: str
    description: str
    duration: str
    view_count: str
    upload_date: str
    channel: str
    video_id: str
    transcript: Optional[str] = None

class YouTubeProcessor:
    """YouTube视频处理器"""
    
    def __init__(self):
        self.config = Config()
        
    async def search_videos(self, query: str, max_results: int = None) -> List[VideoInfo]:
        """
        搜索YouTube视频
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数量
            
        Returns:
            视频信息列表
        """
        if max_results is None:
            max_results = self.config.MAX_SEARCH_RESULTS
            
        logger.info(f"正在搜索YouTube视频: {query}")
        
        try:
            videos_search = VideosSearch(query, limit=max_results)
            results = videos_search.result()
            
            video_list = []
            for video in results['result']:
                video_info = VideoInfo(
                    title=video.get('title', ''),
                    url=video.get('link', ''),
                    description=video.get('descriptionSnippet', [{}])[0].get('text', '') if video.get('descriptionSnippet') else '',
                    duration=video.get('duration', ''),
                    view_count=video.get('viewCount', {}).get('text', ''),
                    upload_date=video.get('publishedTime', ''),
                    channel=video.get('channel', {}).get('name', ''),
                    video_id=video.get('id', '')
                )
                video_list.append(video_info)
                
            logger.success(f"成功搜索到 {len(video_list)} 个视频")
            return video_list
            
        except Exception as e:
            logger.error(f"搜索视频时发生错误: {e}")
            return []
    
    async def download_transcript(self, video_info: VideoInfo) -> str:
        """
        下载视频字幕/转录文本
        
        Args:
            video_info: 视频信息
            
        Returns:
            转录文本
        """
        logger.info(f"正在下载视频字幕: {video_info.title}")
        
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh-Hans', 'zh', 'en'],
            'skip_download': True,
            'outtmpl': str(self.config.TEMP_DIR / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(video_info.url, download=False)
                
                # 尝试下载字幕
                if info.get('subtitles') or info.get('automatic_captions'):
                    ydl_opts['skip_download'] = False
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                        ydl_download.download([video_info.url])
                    
                    # 查找下载的字幕文件
                    subtitle_files = list(self.config.TEMP_DIR.glob(f"*{video_info.video_id}*"))
                    for file in subtitle_files:
                        if file.suffix in ['.vtt', '.srt']:
                            transcript = self._parse_subtitle_file(file)
                            file.unlink()  # 删除临时文件
                            return transcript
                
                # 如果没有字幕，返回视频描述
                logger.warning(f"未找到字幕文件，使用视频描述: {video_info.title}")
                return info.get('description', video_info.description)
                
        except Exception as e:
            logger.error(f"下载字幕时发生错误: {e}")
            return video_info.description
    
    def _parse_subtitle_file(self, file_path: Path) -> str:
        """
        解析字幕文件
        
        Args:
            file_path: 字幕文件路径
            
        Returns:
            解析后的文本
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单的VTT/SRT解析
            lines = content.split('\n')
            text_lines = []
            
            for line in lines:
                line = line.strip()
                # 跳过时间戳和空行
                if (not line or 
                    line.startswith('WEBVTT') or 
                    '-->' in line or 
                    line.isdigit() or
                    line.startswith('NOTE')):
                    continue
                text_lines.append(line)
            
            return ' '.join(text_lines)
            
        except Exception as e:
            logger.error(f"解析字幕文件时发生错误: {e}")
            return ""
    
    async def process_videos(self, query: str) -> List[VideoInfo]:
        """
        完整的视频处理流程：搜索 -> 下载字幕
        
        Args:
            query: 搜索关键词
            
        Returns:
            处理完成的视频信息列表
        """
        # 1. 搜索视频
        videos = await self.search_videos(query)
        
        if not videos:
            logger.warning("未找到任何视频")
            return []
        
        # 2. 并发下载字幕
        logger.info("开始下载视频字幕...")
        
        async def download_single_transcript(video):
            transcript = await self.download_transcript(video)
            video.transcript = transcript
            return video
        
        # 使用信号量限制并发数量
        semaphore = asyncio.Semaphore(2)  # 最多同时下载2个视频的字幕
        
        async def limited_download(video):
            async with semaphore:
                return await download_single_transcript(video)
        
        tasks = [limited_download(video) for video in videos]
        processed_videos = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤掉异常结果
        valid_videos = [v for v in processed_videos if isinstance(v, VideoInfo)]
        
        logger.success(f"成功处理 {len(valid_videos)} 个视频")
        return valid_videos