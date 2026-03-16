"""
特征提取模块
实现文本特征提取逻辑，包含字符数统计、高频词汇分析等功能
"""

import re
from typing import Dict, List, Tuple, Any
from collections import Counter

import config
from utils import handle_exception, g_logger


class FeatureExtractor:
    """特征提取器类"""
    
    def __init__(self, top_n: int = config.TOP_N_WORDS):
        """
        初始化特征提取器
        
        Args:
            top_n: 高频词汇统计数量
        """
        self.top_n = top_n
        self.stop_words = config.STOP_WORDS
    
    def count_characters(self, text: str) -> int:
        """
        统计文本字符数（包含所有字符）
        
        Args:
            text: 文本内容
        
        Returns:
            字符总数
        """
        return len(text)
    
    def count_words(self, text: str) -> int:
        """
        统计单词数（按空格分割）
        
        Args:
            text: 文本内容
        
        Returns:
            单词总数
        """
        if not text or not text.strip():
            return 0
        
        # 按空格分割，过滤空字符串
        words = [word for word in text.split(' ') if word.strip()]
        return len(words)
    
    def extract_words(self, text: str) -> List[str]:
        """
        提取所有单词
        
        Args:
            text: 文本内容
        
        Returns:
            单词列表
        """
        if not text:
            return []
        
        # 按空格分割并过滤
        words = []
        for word in text.split(' '):
            word = word.strip()
            if word:
                words.append(word)
        
        return words
    
    def get_word_frequency(self, text: str, filter_stopwords: bool = False) -> List[Tuple[str, int]]:
        """
        统计词频，返回前N个高频词汇
        
        Args:
            text: 文本内容
            filter_stopwords: 是否过滤停用词
        
        Returns:
            (单词, 频次) 列表，按频次降序排列
        """
        global g_logger
        
        words = self.extract_words(text)
        
        if not words:
            return []
        
        # 过滤停用词（可选）
        if filter_stopwords:
            words = [w for w in words if w not in self.stop_words]
        
        # 统计词频
        word_counts = Counter(words)
        
        # 获取前N个高频词
        most_common = word_counts.most_common(self.top_n)
        
        if g_logger:
            g_logger.debug(f"提取了 {len(most_common)} 个高频词汇")
        
        return most_common
    
    def analyze_chinese_characters(self, text: str) -> Dict[str, Any]:
        """
        分析中文字符统计
        
        Args:
            text: 文本内容
        
        Returns:
            中文字符统计信息
        """
        # 匹配中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
        
        return {
            'chinese_char_count': len(chinese_chars),
            'unique_chinese_chars': len(set(chinese_chars))
        }
    
    def analyze_english_words(self, text: str) -> Dict[str, Any]:
        """
        分析英文单词统计
        
        Args:
            text: 文本内容
        
        Returns:
            英文单词统计信息
        """
        # 匹配英文单词
        english_words = re.findall(r'[a-z]+', text)
        
        return {
            'english_word_count': len(english_words),
            'unique_english_words': len(set(english_words))
        }
    
    @handle_exception
    def extract_features(self, text: str) -> Dict[str, Any]:
        """
        提取文本的核心特征
        
        Args:
            text: 清洗后的文本内容
        
        Returns:
            特征分析结果字典
        """
        global g_logger
        
        if not text:
            return {
                'char_count': 0,
                'word_count': 0,
                'top_words': [],
                'chinese_stats': {'chinese_char_count': 0, 'unique_chinese_chars': 0},
                'english_stats': {'english_word_count': 0, 'unique_english_words': 0}
            }
        
        # 基础统计
        char_count = self.count_characters(text)
        word_count = self.count_words(text)
        
        # 高频词汇
        top_words = self.get_word_frequency(text, filter_stopwords=False)
        
        # 中英文统计
        chinese_stats = self.analyze_chinese_characters(text)
        english_stats = self.analyze_english_words(text)
        
        features = {
            'char_count': char_count,
            'word_count': word_count,
            'top_words': top_words,
            'chinese_stats': chinese_stats,
            'english_stats': english_stats
        }
        
        if g_logger:
            g_logger.debug(f"特征提取完成: {char_count} 字符, {word_count} 单词")
        
        return features
    
    @handle_exception
    def process_cleaned_data(self, cleaned_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量处理清洗后的数据，提取特征
        
        Args:
            cleaned_data_list: 清洗后的数据列表
        
        Returns:
            包含特征分析结果的数据列表
        """
        global g_logger
        
        results = []
        
        for cleaned_data in cleaned_data_list:
            try:
                file_name = cleaned_data.get('file_name', '')
                
                # 获取用于分析的文本
                text = self._get_analysis_text(cleaned_data)
                
                if not text:
                    if g_logger:
                        g_logger.warning(f"文件无有效文本内容: {file_name}")
                    results.append({
                        'file_name': file_name,
                        'features': None,
                        'error': '无有效文本内容'
                    })
                    continue
                
                # 提取特征
                features = self.extract_features(text)
                
                results.append({
                    'file_name': file_name,
                    'features': features,
                    'error': None
                })
                
                if g_logger:
                    g_logger.info(f"特征提取完成: {file_name}")
                    
            except Exception as e:
                if g_logger:
                    g_logger.error(f"特征提取失败 {cleaned_data.get('file_name')}: {str(e)}")
                results.append({
                    'file_name': cleaned_data.get('file_name', ''),
                    'features': None,
                    'error': str(e)
                })
        
        if g_logger:
            g_logger.info(f"共完成 {len(results)} 个文件的特征提取")
        
        return results
    
    def _get_analysis_text(self, cleaned_data: Dict[str, Any]) -> str:
        """
        从清洗后的数据中获取分析用的文本
        
        Args:
            cleaned_data: 清洗后的数据字典
        
        Returns:
            文本内容
        """
        # 优先使用cleaned_content
        if cleaned_data.get('cleaned_content'):
            return cleaned_data['cleaned_content']
        
        # 从cleaned_data中提取
        if cleaned_data.get('cleaned_data'):
            data = cleaned_data['cleaned_data']
            if isinstance(data, dict):
                text = data.get('text') or data.get('content', '')
                if isinstance(text, str):
                    return text
        
        return ""


def format_top_words(top_words: List[Tuple[str, int]]) -> str:
    """
    格式化高频词汇为字符串
    
    Args:
        top_words: (单词, 频次) 列表
    
    Returns:
        格式化后的字符串
    """
    if not top_words:
        return "无"
    
    formatted = []
    for idx, (word, count) in enumerate(top_words, 1):
        formatted.append(f"{idx}. {word} ({count}次)")
    
    return " | ".join(formatted)
