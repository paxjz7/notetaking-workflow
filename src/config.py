"""
配置管理模块
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# 加载环境变量
load_dotenv()

class Config:
    """系统配置类"""
    
    # API配置
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_RPM_LIMIT: int = int(os.getenv("GEMINI_RPM_LIMIT", "5"))
    
    # Obsidian配置
    OBSIDIAN_VAULT_PATH: str = os.getenv("OBSIDIAN_VAULT_PATH", "")
    
    # YouTube配置
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "3"))
    VIDEO_QUALITY: str = os.getenv("VIDEO_QUALITY", "best[height<=720]")
    
    # 事件系统配置
    EVENT_STORE_TYPE: str = os.getenv("EVENT_STORE_TYPE", "file")  # file, memory, redis
    EVENT_STORE_PATH: str = os.getenv("EVENT_STORE_PATH", "data/events")
    MAX_CONCURRENT_WORKFLOWS: int = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "10"))
    WORKFLOW_TIMEOUT: int = int(os.getenv("WORKFLOW_TIMEOUT", "600"))  # 10分钟
    
    # 熔断器配置
    CIRCUIT_BREAKER_ENABLED: bool = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    API_FAILURE_THRESHOLD: int = int(os.getenv("API_FAILURE_THRESHOLD", "5"))
    API_RECOVERY_TIMEOUT: int = int(os.getenv("API_RECOVERY_TIMEOUT", "300"))  # 5分钟
    
    # 项目路径
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    OUTPUT_DIR: Path = PROJECT_ROOT / "output"
    TEMP_DIR: Path = PROJECT_ROOT / "temp"
    DATA_DIR: Path = PROJECT_ROOT / "data"
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要的配置项"""
        required_fields = [
            "GEMINI_API_KEY",
            "OBSIDIAN_VAULT_PATH"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"缺少必要的配置项: {', '.join(missing_fields)}")
        
        # 验证Obsidian路径存在
        if not Path(cls.OBSIDIAN_VAULT_PATH).exists():
            raise ValueError(f"Obsidian vault路径不存在: {cls.OBSIDIAN_VAULT_PATH}")
        
        return True
    
    @classmethod
    def create_directories(cls):
        """创建必要的目录"""
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)
        cls.DATA_DIR.mkdir(exist_ok=True)
        
        # 创建事件存储目录
        event_store_path = Path(cls.EVENT_STORE_PATH)
        event_store_path.mkdir(parents=True, exist_ok=True)
        
        # 创建日志目录
        log_dir = cls.PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)