import sys
from loguru import logger

def setup_logger(level: str = "INFO"):
    """配置控制台与文件日志输出"""
    logger.remove()
    
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=log_format,
        colorize=True,
    )
    
    logger.add(
        "logs/rst_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format=log_format,
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )
    return logger

# 默认初始化
setup_logger("INFO")

__all__ = ["logger", "setup_logger"]
