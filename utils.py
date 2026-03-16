"""
通用工具函数模块
封装路径校验、日志初始化、异常处理等通用功能
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import config


def initialize_logger(log_file_name: Optional[str] = None) -> logging.Logger:
    """
    初始化日志记录器
    
    Args:
        log_file_name: 日志文件名，默认使用配置中的文件名
    
    Returns:
        配置好的日志记录器实例
    """
    global g_logger
    
    if log_file_name is None:
        log_file_name = config.LOG_FILE_NAME
    
    log_file_path = os.path.join(config.LOG_DIR, log_file_name)
    
    os.makedirs(config.LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger("text_processor")
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
    
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        
        formatter = logging.Formatter(config.LOG_FORMAT)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    g_logger = logger
    return logger


def validate_relative_path(path: str, must_exist: bool = False) -> bool:
    """
    验证路径是否为相对路径
    
    Args:
        path: 待验证的路径
        must_exist: 是否要求路径必须存在
    
    Returns:
        如果是相对路径返回True，否则返回False
    """
    if os.path.isabs(path):
        return False
    
    if must_exist and not os.path.exists(path):
        return False
    
    return True


def ensure_output_directories() -> Dict[str, bool]:
    """
    确保所有输出目录存在
    
    Returns:
        包含各目录创建状态的字典
    """
    global g_logger
    
    directories = [
        config.OUTPUT_CLEANED_DIR,
        config.OUTPUT_REPORTS_DIR,
        config.LOG_DIR
    ]
    
    results = {}
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            results[directory] = True
            if 'g_logger' in globals():
                g_logger.info(f"目录已确保存在: {directory}")
        except Exception as e:
            results[directory] = False
            if 'g_logger' in globals():
                g_logger.error(f"创建目录失败 {directory}: {str(e)}")
    
    return results


def log_processing_record(
    file_name: str,
    status: str,
    reason: Optional[str] = None,
    extra_info: Optional[Dict[str, Any]] = None
) -> None:
    """
    记录处理日志
    
    Args:
        file_name: 处理的文件名
        status: 处理状态（成功/失败）
        reason: 失败原因（如有）
        extra_info: 额外信息字典
    """
    global g_logger
    
    if 'g_logger' not in globals():
        initialize_logger()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = f"处理时间: {timestamp} | 文件: {file_name} | 状态: {status}"
    
    if reason:
        log_message += f" | 原因: {reason}"
    
    if extra_info:
        for key, value in extra_info.items():
            log_message += f" | {key}: {value}"
    
    if status.lower() in ["成功", "success"]:
        g_logger.info(log_message)
    else:
        g_logger.error(log_message)


class ProcessingError(Exception):
    """自定义处理异常类"""
    
    def __init__(self, message: str, file_name: Optional[str] = None):
        self.message = message
        self.file_name = file_name
        super().__init__(self.message)
    
    def __str__(self):
        if self.file_name:
            return f"[{self.file_name}] {self.message}"
        return self.message


class ValidationError(ProcessingError):
    """数据验证异常"""
    pass


class EncodingError(ProcessingError):
    """编码异常"""
    pass


def handle_exception(func):
    """
    异常处理装饰器
    
    Args:
        func: 被装饰的函数
    
    Returns:
        包装后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ProcessingError as e:
            if 'g_logger' in globals():
                g_logger.error(f"处理错误: {str(e)}")
            raise
        except Exception as e:
            if 'g_logger' in globals():
                g_logger.error(f"未预期的错误: {str(e)}")
            raise ProcessingError(f"未预期的错误: {str(e)}")
    
    return wrapper


def check_readonly_file(file_path: str) -> bool:
    """
    检查文件是否为只读参考文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        如果是只读文件返回True
    """
    normalized_path = os.path.normpath(file_path)
    normalized_readonly = os.path.normpath(config.READONLY_REFERENCE_FILE)
    return normalized_path == normalized_readonly


def get_file_extension(file_name: str) -> str:
    """
    获取文件扩展名
    
    Args:
        file_name: 文件名
    
    Returns:
        小写的扩展名（包含点）
    """
    _, ext = os.path.splitext(file_name)
    return ext.lower()


def is_allowed_file_type(file_name: str) -> bool:
    """
    检查文件类型是否允许
    
    Args:
        file_name: 文件名
    
    Returns:
        如果允许返回True
    """
    ext = get_file_extension(file_name)
    return ext in config.ALLOWED_INPUT_EXTENSIONS


# 初始化全局日志记录器
g_logger = None
