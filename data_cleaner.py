"""
数据清洗模块
实现数据清洗核心逻辑，包含特殊字符过滤、格式统一、大小写转换等功能
"""

import re
import json
from typing import Dict, Any, Optional

import config
import utils
from utils import ProcessingError, handle_exception


class DataCleaner:
    """数据清洗器类"""
    
    def __init__(self):
        """初始化数据清洗器"""
        self.special_char_pattern = re.compile(config.PRESERVED_CHARS_PATTERN)
        self.line_break_pattern = re.compile(config.LINE_BREAK_PATTERN)
    
    def remove_special_characters(self, text: str) -> str:
        """
        移除特殊字符，仅保留中英文、数字、空格
        
        Args:
            text: 原始文本
        
        Returns:
            清洗后的文本
        """
        cleaned = self.special_char_pattern.sub('', text)
        return cleaned
    
    def normalize_line_breaks(self, text: str) -> str:
        """
        统一换行符格式为\n
        
        Args:
            text: 原始文本
        
        Returns:
            换行符统一后的文本
        """
        normalized = self.line_break_pattern.sub('\n', text)
        return normalized
    
    def convert_to_lowercase(self, text: str) -> str:
        """
        将所有英文字符转为小写
        
        Args:
            text: 原始文本
        
        Returns:
            小写转换后的文本
        """
        return text.lower()
    
    def remove_extra_whitespace(self, text: str) -> str:
        """
        移除多余的空白字符
        
        Args:
            text: 原始文本
        
        Returns:
            处理后的文本
        """
        # 将多个连续空格替换为单个空格
        text = re.sub(r' +', ' ', text)
        # 移除行首行尾空格
        lines = [line.strip() for line in text.split('\n')]
        # 过滤掉完全为空的行
        lines = [line for line in lines if line]
        return '\n'.join(lines)
    
    @handle_exception
    def clean_text(self, text: str) -> str:
        """
        执行完整的文本清洗流程
        
        Args:
            text: 原始文本
        
        Returns:
            清洗后的文本
        """
        
        
        if not text:
            return ""
        
        # 步骤1: 统一换行符
        text = self.normalize_line_breaks(text)
        
        # 步骤2: 移除特殊字符
        text = self.remove_special_characters(text)
        
        # 步骤3: 转为小写
        text = self.convert_to_lowercase(text)
        
        # 步骤4: 清理多余空白
        text = self.remove_extra_whitespace(text)
        
        if utils.g_logger:
            utils.g_logger.debug("文本清洗完成")
        
        return text
    
    @handle_exception
    def clean_json_content(self, data: Any) -> Any:
        """
        递归清洗JSON数据结构中的文本内容
        
        Args:
            data: JSON数据（可以是dict, list, str等）
        
        Returns:
            清洗后的数据
        """
        if isinstance(data, str):
            return self.clean_text(data)
        elif isinstance(data, dict):
            return {key: self.clean_json_content(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.clean_json_content(item) for item in data]
        else:
            return data
    
    @handle_exception
    def process_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个文件的数据清洗
        
        Args:
            file_data: 包含文件信息的字典
        
        Returns:
            包含清洗后数据的字典
        """
        
        
        file_name = file_data.get('file_name', '')
        content = file_data.get('content', '')
        parsed_data = file_data.get('parsed_data')
        
        if not content:
            raise ProcessingError("文件内容为空", file_name)
        
        cleaned_data = {
            'file_name': file_name,
            'original_content': content,
            'cleaned_content': None,
            'is_json': file_name.lower().endswith('.json'),
            'cleaned_data': None
        }
        
        # 如果是JSON文件且解析成功，清洗结构化数据
        if cleaned_data['is_json'] and parsed_data is not None:
            cleaned_structure = self.clean_json_content(parsed_data)
            cleaned_data['cleaned_data'] = cleaned_structure
            # 同时保留文本形式的清洗结果
            if isinstance(parsed_data, dict):
                # 提取text或content字段进行清洗
                text_content = parsed_data.get('text') or parsed_data.get('content', '')
                if isinstance(text_content, str):
                    cleaned_data['cleaned_content'] = self.clean_text(text_content)
            else:
                cleaned_data['cleaned_content'] = self.clean_text(json.dumps(parsed_data, ensure_ascii=False))
        else:
            # 普通文本文件直接清洗
            cleaned_data['cleaned_content'] = self.clean_text(content)
        
        if utils.g_logger:
            utils.g_logger.info(f"文件清洗完成: {file_name}")
        
        return cleaned_data
    
    @handle_exception
    def process_files(self, file_data_list: list) -> list:
        """
        批量处理多个文件
        
        Args:
            file_data_list: 文件数据字典列表
        
        Returns:
            清洗后的数据列表
        """
        
        
        results = []
        
        for file_data in file_data_list:
            try:
                if not file_data.get('is_valid', True):
                    if utils.g_logger:
                        utils.g_logger.warning(f"跳过无效文件: {file_data.get('file_name')}")
                    continue
                
                cleaned = self.process_file(file_data)
                results.append(cleaned)
            except Exception as e:
                if utils.g_logger:
                    utils.g_logger.error(f"清洗文件失败 {file_data.get('file_name')}: {str(e)}")
                results.append({
                    'file_name': file_data.get('file_name'),
                    'error': str(e),
                    'cleaned_content': None
                })
        
        if utils.g_logger:
            utils.g_logger.info(f"共清洗 {len(results)} 个文件")
        
        return results


def extract_text_for_analysis(cleaned_data: Dict[str, Any]) -> str:
    """
    从清洗后的数据中提取用于分析的文本
    
    Args:
        cleaned_data: 清洗后的数据字典
    
    Returns:
        用于分析的文本内容
    """
    # 优先使用cleaned_content
    if cleaned_data.get('cleaned_content'):
        return cleaned_data['cleaned_content']
    
    # 如果是JSON且有清洗后的数据结构
    if cleaned_data.get('cleaned_data'):
        data = cleaned_data['cleaned_data']
        if isinstance(data, dict):
            text = data.get('text') or data.get('content', '')
            if isinstance(text, str):
                return text
        return json.dumps(data, ensure_ascii=False)
    
    return ""
