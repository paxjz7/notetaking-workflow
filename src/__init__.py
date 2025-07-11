"""
YouTube视频总结系统
"""

__version__ = "1.0.0"
__author__ = "YouTube Summary System"
__description__ = "基于YouTube搜索、Gemini AI总结和Obsidian文档生成的自动化系统"

from .config import Config
from .youtube_processor import YouTubeProcessor, VideoInfo
from .gemini_summarizer import GeminiSummarizer, VideoSummary
from .obsidian_writer import ObsidianWriter
from .main import YouTubeSummarySystem

__all__ = [
    "Config",
    "YouTubeProcessor",
    "VideoInfo", 
    "GeminiSummarizer",
    "VideoSummary",
    "ObsidianWriter",
    "YouTubeSummarySystem"
]