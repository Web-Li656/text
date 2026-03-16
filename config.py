"""
全局配置常量模块
定义所有全局配置参数、路径和常量
"""

import os

# 输入输出路径配置（仅使用相对路径）
INPUT_DIR = "./data/input"
OUTPUT_CLEANED_DIR = "./build/dist/cleaned"
OUTPUT_REPORTS_DIR = "./build/dist/reports"

# 允许的文件格式
ALLOWED_INPUT_EXTENSIONS = {".txt", ".json"}
REPORT_EXTENSION = ".md"

# 只读参考文件路径（仅允许读取）
READONLY_REFERENCE_FILE = "./data/input/legacy.dat"

# 日志配置
LOG_DIR = "./build/dist"
LOG_FILE_NAME = "processing.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# 数据清洗配置
PRESERVED_CHARS_PATTERN = r"[^\u4e00-\u9fa5a-zA-Z0-9\s]"  # 保留中英文、数字、空格
LINE_BREAK_PATTERN = r"\r\n|\r"  # 需要统一为\n的换行符
TOP_N_WORDS = 10  # 高频词汇统计数量

# 高频词汇过滤配置（可选：过滤常见停用词）
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall",
    "can", "need", "dare", "ought", "used", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into",
    "through", "during", "before", "after", "above", "below",
    "between", "under", "and", "but", "or", "yet", "so",
    "if", "because", "although", "though", "while", "where",
    "when", "that", "which", "who", "whom", "whose", "what",
    "this", "these", "those", "i", "you", "he", "she", "it",
    "we", "they", "me", "him", "her", "us", "them", "my",
    "your", "his", "its", "our", "their", "mine", "yours",
    "hers", "ours", "theirs"
}
