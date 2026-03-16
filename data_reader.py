"""
数据读取模块
实现文件读取逻辑，包含读取指定目录文件、格式校验、编码检测功能
"""

import os
import json
import chardet
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

import config
from utils import (
    validate_relative_path,
    is_allowed_file_type,
    check_readonly_file,
    ValidationError,
    EncodingError,
    handle_exception,
    g_logger
)


class DataReader:
    """数据读取器类"""
    
    def __init__(self, input_dir: str = config.INPUT_DIR):
        """
        初始化数据读取器
        
        Args:
            input_dir: 输入目录路径（相对路径）
        """
        self.input_dir = input_dir
        self._validate_input_dir()
    
    def _validate_input_dir(self) -> None:
        """验证输入目录"""
        if not validate_relative_path(self.input_dir):
            raise ValidationError(f"输入目录必须使用相对路径: {self.input_dir}")
        
        if not os.path.exists(self.input_dir):
            raise ValidationError(f"输入目录不存在: {self.input_dir}")
        
        if not os.path.isdir(self.input_dir):
            raise ValidationError(f"输入路径不是目录: {self.input_dir}")
    
    def list_input_files(self) -> List[str]:
        """
        列出输入目录下所有允许格式的文件
        
        Returns:
            符合条件的文件名列表（不含路径）
        """
        global g_logger
        
        files = []
        try:
            for file_name in os.listdir(self.input_dir):
                file_path = os.path.join(self.input_dir, file_name)
                
                # 跳过子目录
                if os.path.isdir(file_path):
                    continue
                
                # 检查文件类型
                if is_allowed_file_type(file_name):
                    files.append(file_name)
                    if g_logger:
                        g_logger.debug(f"发现有效文件: {file_name}")
        except Exception as e:
            if g_logger:
                g_logger.error(f"读取目录失败: {str(e)}")
            raise ValidationError(f"无法读取输入目录: {str(e)}")
        
        if g_logger:
            g_logger.info(f"共发现 {len(files)} 个有效文件")
        
        return files
    
    def detect_encoding(self, file_path: str) -> str:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
        
        Returns:
            检测到的编码格式
        """
        global g_logger
        
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)
                
                if g_logger:
                    g_logger.debug(f"文件 {os.path.basename(file_path)} 编码检测: {encoding} (置信度: {confidence:.2f})")
                
                return encoding
        except Exception as e:
            if g_logger:
                g_logger.error(f"编码检测失败 {file_path}: {str(e)}")
            raise EncodingError(f"无法检测文件编码: {str(e)}", os.path.basename(file_path))
    
    def validate_utf8_encoding(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        验证文件是否为UTF-8编码
        
        Args:
            file_path: 文件路径
        
        Returns:
            (是否UTF-8, 错误信息)
        """
        global g_logger
        
        detected_encoding = self.detect_encoding(file_path)
        
        # 如果检测到的编码不是UTF-8，尝试以UTF-8读取验证
        if detected_encoding.lower() not in ['utf-8', 'utf8']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read()
            except UnicodeDecodeError:
                error_msg = f"文件编码不是UTF-8 (检测到: {detected_encoding})"
                if g_logger:
                    g_logger.warning(f"{os.path.basename(file_path)}: {error_msg}")
                return False, error_msg
        
        return True, None
    
    def check_empty_lines(self, content: str) -> Tuple[bool, List[int]]:
        """
        检查内容中是否存在空行
        
        Args:
            content: 文件内容
        
        Returns:
            (是否存在空行, 空行行号列表)
        """
        lines = content.split('\n')
        empty_line_numbers = []
        
        for idx, line in enumerate(lines, start=1):
            if line.strip() == '':
                empty_line_numbers.append(idx)
        
        return len(empty_line_numbers) > 0, empty_line_numbers
    
    def validate_json_structure(self, content: str, file_name: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        验证JSON文件结构
        
        Args:
            content: 文件内容
            file_name: 文件名
        
        Returns:
            (是否有效, 错误信息, 解析后的数据)
        """
        global g_logger
        
        try:
            data = json.loads(content)
            
            # 检查关键字段（假设JSON应包含text字段）
            if isinstance(data, dict):
                if 'text' not in data and 'content' not in data:
                    warning_msg = "JSON缺少关键字段(text或content)"
                    if g_logger:
                        g_logger.warning(f"{file_name}: {warning_msg}")
                    # 不返回False，仅作为警告
            
            return True, None, data
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误: {str(e)}"
            if g_logger:
                g_logger.error(f"{file_name}: {error_msg}")
            return False, error_msg, None
    
    @handle_exception
    def read_file(self, file_name: str) -> Dict[str, Any]:
        """
        读取并验证单个文件
        
        Args:
            file_name: 文件名（不含路径）
        
        Returns:
            包含文件内容的字典
        """
        global g_logger
        
        file_path = os.path.join(self.input_dir, file_name)
        
        # 检查是否为只读文件
        if check_readonly_file(file_path):
            if g_logger:
                g_logger.info(f"检测到只读参考文件: {file_name}")
        
        # 验证UTF-8编码
        is_utf8, encoding_error = self.validate_utf8_encoding(file_path)
        if not is_utf8:
            raise EncodingError(encoding_error, file_name)
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise ValidationError(f"无法读取文件: {str(e)}", file_name)
        
        # 检查空行
        has_empty_lines, empty_line_nums = self.check_empty_lines(content)
        
        result = {
            'file_name': file_name,
            'file_path': file_path,
            'content': content,
            'has_empty_lines': has_empty_lines,
            'empty_line_numbers': empty_line_nums,
            'is_valid': True,
            'error_message': None
        }
        
        # 如果是JSON文件，额外验证结构
        if file_name.lower().endswith('.json'):
            is_valid_json, json_error, parsed_data = self.validate_json_structure(content, file_name)
            result['is_json_valid'] = is_valid_json
            result['json_error'] = json_error
            result['parsed_data'] = parsed_data
            
            if not is_valid_json:
                result['is_valid'] = False
                result['error_message'] = json_error
        
        if g_logger:
            g_logger.info(f"文件读取成功: {file_name}")
        
        return result
    
    @handle_exception
    def read_all_files(self) -> List[Dict[str, Any]]:
        """
        读取所有输入文件
        
        Returns:
            文件内容字典列表
        """
        global g_logger
        
        file_names = self.list_input_files()
        results = []
        
        for file_name in file_names:
            try:
                file_data = self.read_file(file_name)
                results.append(file_data)
            except Exception as e:
                if g_logger:
                    g_logger.error(f"读取文件失败 {file_name}: {str(e)}")
                results.append({
                    'file_name': file_name,
                    'file_path': os.path.join(self.input_dir, file_name),
                    'content': None,
                    'is_valid': False,
                    'error_message': str(e)
                })
        
        return results
    
    def read_readonly_reference(self) -> Optional[str]:
        """
        读取只读参考文件内容
        
        Returns:
            参考文件内容，如果不存在则返回None
        """
        global g_logger
        
        if not os.path.exists(config.READONLY_REFERENCE_FILE):
            if g_logger:
                g_logger.warning(f"只读参考文件不存在: {config.READONLY_REFERENCE_FILE}")
            return None
        
        try:
            with open(config.READONLY_REFERENCE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            if g_logger:
                g_logger.info(f"成功读取只读参考文件: {config.READONLY_REFERENCE_FILE}")
            return content
        except Exception as e:
            if g_logger:
                g_logger.error(f"读取只读参考文件失败: {str(e)}")
            return None
