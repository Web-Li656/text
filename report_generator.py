"""
报告生成模块
实现分析报告生成逻辑，负责将特征数据转为.md格式并保存
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import config
import utils
from utils import validate_relative_path, ProcessingError, handle_exception
from feature_extractor import format_top_words


class ReportGenerator:
    """报告生成器类"""
    
    def __init__(self, output_dir: str = config.OUTPUT_REPORTS_DIR):
        """
        初始化报告生成器
        
        Args:
            output_dir: 报告输出目录（相对路径）
        """
        self.output_dir = output_dir
        self._validate_output_dir()
    
    def _validate_output_dir(self) -> None:
        """验证输出目录"""
        if not validate_relative_path(self.output_dir):
            raise ProcessingError(f"输出目录必须使用相对路径: {self.output_dir}")
        
        # 确保目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_report_filename(self, original_filename: str) -> str:
        """
        生成报告文件名
        
        Args:
            original_filename: 原始文件名
        
        Returns:
            报告文件名（格式: {原文件名}_analysis.md）
        """
        # 移除原始扩展名
        base_name = os.path.splitext(original_filename)[0]
        # 添加后缀和扩展名
        report_name = f"{base_name}_analysis{config.REPORT_EXTENSION}"
        return report_name
    
    def format_processing_time(self) -> str:
        """
        格式化处理时间
        
        Returns:
            格式化的时间字符串
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_markdown_content(
        self,
        file_name: str,
        features: Dict[str, Any],
        processing_time: Optional[str] = None
    ) -> str:
        """
        生成Markdown格式的报告内容
        
        Args:
            file_name: 处理的文件名
            features: 特征分析结果
            processing_time: 处理时间
        
        Returns:
            Markdown格式的报告内容
        """
        if processing_time is None:
            processing_time = self.format_processing_time()
        
        # 提取特征数据
        char_count = features.get('char_count', 0)
        word_count = features.get('word_count', 0)
        top_words = features.get('top_words', [])
        
        # 格式化高频词汇
        top_words_str = format_top_words(top_words)
        
        # 构建Markdown内容
        lines = [
            "# 文本数据分析报告",
            "",
            "## 文件信息",
            "",
            f"| 项目 | 内容 |",
            f"|------|------|",
            f"| 文件名称 | {file_name} |",
            f"| 处理时间 | {processing_time} |",
            "",
            "## 统计信息",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 字符数 | {char_count} |",
            f"| 单词数 | {word_count} |",
            "",
            "## 高频词汇（前10）",
            "",
            f"{top_words_str}",
            "",
            "---",
            "",
            "*报告由文本数据清洗与分析工具自动生成*"
        ]
        
        return "\n".join(lines)
    
    def generate_error_report(
        self,
        file_name: str,
        error_message: str,
        processing_time: Optional[str] = None
    ) -> str:
        """
        生成错误报告的Markdown内容
        
        Args:
            file_name: 处理的文件名
            error_message: 错误信息
            processing_time: 处理时间
        
        Returns:
            Markdown格式的错误报告内容
        """
        if processing_time is None:
            processing_time = self.format_processing_time()
        
        lines = [
            "# 文本数据分析报告",
            "",
            "## 文件信息",
            "",
            f"| 项目 | 内容 |",
            f"|------|------|",
            f"| 文件名称 | {file_name} |",
            f"| 处理时间 | {processing_time} |",
            f"| 处理状态 | ❌ 失败 |",
            "",
            "## 错误信息",
            "",
            f"```",
            f"{error_message}",
            f"```",
            "",
            "---",
            "",
            "*报告由文本数据清洗与分析工具自动生成*"
        ]
        
        return "\n".join(lines)
    
    @handle_exception
    def save_report(self, file_name: str, content: str) -> str:
        """
        保存报告文件
        
        Args:
            file_name: 报告文件名
            content: 报告内容
        
        Returns:
            保存的文件路径
        """
        
        
        report_path = os.path.join(self.output_dir, file_name)
        
        # 验证输出路径为相对路径
        if not validate_relative_path(report_path):
            raise ProcessingError(f"报告路径必须使用相对路径: {report_path}")
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 写入文件
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if utils.g_logger:
            utils.g_logger.info(f"报告已保存: {report_path}")
        
        return report_path
    
    @handle_exception
    def generate_and_save_report(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成并保存单个报告
        
        Args:
            analysis_result: 分析结果字典，包含file_name, features, error
        
        Returns:
            包含报告信息的字典
        """
        
        
        file_name = analysis_result.get('file_name', '')
        features = analysis_result.get('features')
        error = analysis_result.get('error')
        processing_time = self.format_processing_time()
        
        # 生成报告文件名
        report_name = self.generate_report_filename(file_name)
        
        # 根据是否有错误生成不同内容
        if error:
            content = self.generate_error_report(file_name, error, processing_time)
            status = "失败"
        else:
            content = self.generate_markdown_content(file_name, features, processing_time)
            status = "成功"
        
        # 保存报告
        report_path = self.save_report(report_name, content)
        
        result = {
            'original_file': file_name,
            'report_file': report_name,
            'report_path': report_path,
            'status': status,
            'processing_time': processing_time
        }
        
        if utils.g_logger:
            utils.g_logger.info(f"报告生成完成 [{status}]: {report_name}")
        
        return result
    
    @handle_exception
    def generate_batch_reports(self, analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量生成报告
        
        Args:
            analysis_results: 分析结果列表
        
        Returns:
            报告信息列表
        """
        
        
        reports = []
        
        for result in analysis_results:
            try:
                report_info = self.generate_and_save_report(result)
                reports.append(report_info)
            except Exception as e:
                if utils.g_logger:
                    utils.g_logger.error(f"生成报告失败 {result.get('file_name')}: {str(e)}")
                reports.append({
                    'original_file': result.get('file_name', ''),
                    'report_file': None,
                    'report_path': None,
                    'status': '失败',
                    'error': str(e)
                })
        
        if utils.g_logger:
            utils.g_logger.info(f"共生成 {len(reports)} 份报告")
        
        return reports


def generate_summary_report(
    all_reports: List[Dict[str, Any]],
    output_path: str = "./build/dist/summary_report.md"
) -> str:
    """
    生成汇总报告
    
    Args:
        all_reports: 所有报告信息列表
        output_path: 汇总报告输出路径
    
    Returns:
        汇总报告路径
    """
    
    
    processing_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_count = len(all_reports)
    success_count = sum(1 for r in all_reports if r.get('status') == '成功')
    failed_count = total_count - success_count
    
    lines = [
        "# 文本数据处理汇总报告",
        "",
        f"**生成时间**: {processing_time}",
        "",
        "## 处理统计",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总文件数 | {total_count} |",
        f"| 成功处理 | {success_count} |",
        f"| 处理失败 | {failed_count} |",
        "",
        "## 详细报告列表",
        "",
        "| 序号 | 原始文件 | 报告文件 | 状态 | 处理时间 |",
        "|------|----------|----------|------|----------|"
    ]
    
    for idx, report in enumerate(all_reports, 1):
        original = report.get('original_file', '')
        report_file = report.get('report_file', 'N/A')
        status = report.get('status', '未知')
        time = report.get('processing_time', '')
        
        status_icon = "✅" if status == "成功" else "❌"
        lines.append(f"| {idx} | {original} | {report_file} | {status_icon} {status} | {time} |")
    
    lines.extend([
        "",
        "---",
        "",
        "*本报告由文本数据清洗与分析工具自动生成*"
    ])
    
    content = "\n".join(lines)
    
    # 保存汇总报告
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    if utils.g_logger:
        utils.g_logger.info(f"汇总报告已保存: {output_path}")
    
    return output_path
