"""
程序入口模块
负责解析命令行参数、调用各模块执行完整处理流程
"""

import os
import sys
import argparse
import json
from typing import List, Dict, Any

import config
import utils
from utils import (
    initialize_logger,
    ensure_output_directories,
    log_processing_record,
    ProcessingError,
    validate_relative_path
)
from data_reader import DataReader
from data_cleaner import DataCleaner, extract_text_for_analysis
from feature_extractor import FeatureExtractor
from report_generator import ReportGenerator, generate_summary_report


g_cleaned_output_dir = config.OUTPUT_CLEANED_DIR


def save_cleaned_file(cleaned_data: Dict[str, Any]) -> str:
    """
    保存清洗后的文件
    
    Args:
        cleaned_data: 清洗后的数据字典
        
    Returns:
        保存的文件路径
    """
    file_name = cleaned_data.get('file_name', '')
    cleaned_content = cleaned_data.get('cleaned_content', '')
    cleaned_structured = cleaned_data.get('cleaned_data')
    
    if not file_name:
        raise ProcessingError("文件名为空")
    
    output_path = os.path.join(g_cleaned_output_dir, file_name)
    
    if not validate_relative_path(output_path):
        raise ProcessingError(f"输出路径必须使用相对路径: {output_path}")
    
    os.makedirs(g_cleaned_output_dir, exist_ok=True)
    
    is_json = file_name.lower().endswith('.json')
    
    if is_json and cleaned_structured is not None:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_structured, f, ensure_ascii=False, indent=2)
    else:
        if cleaned_content is None:
            cleaned_content = ''
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
    
    if utils.g_logger:
        utils.g_logger.info(f"清洗后文件已保存: {output_path}")
    
    return output_path


def process_single_file(
    file_name: str,
    reader: DataReader,
    cleaner: DataCleaner,
    extractor: FeatureExtractor,
    reporter: ReportGenerator
) -> Dict[str, Any]:
    """
    处理单个文件的完整流程
    
    Args:
        file_name: 文件名
        reader: 数据读取器
        cleaner: 数据清洗器
        extractor: 特征提取器
        reporter: 报告生成器
        
    Returns:
        处理结果字典
    """
    try:
        file_data = reader.read_file(file_name)
        
        if not file_data.get('is_valid', False):
            error_msg = file_data.get('error_message', '未知错误')
            log_processing_record(file_name, '失败', error_msg)
            return {
                'file_name': file_name,
                'success': False,
                'error': error_msg,
                'features': None
            }
        
        cleaned_data = cleaner.process_file(file_data)
        
        save_cleaned_file(cleaned_data)
        
        analysis_text = extract_text_for_analysis(cleaned_data)
        features = extractor.extract_features(analysis_text)
        
        log_processing_record(file_name, '成功', None, {
            '字符数': features.get('char_count', 0),
            '单词数': features.get('word_count', 0)
        })
        
        return {
            'file_name': file_name,
            'success': True,
            'error': None,
            'features': features
        }
        
    except Exception as e:
        error_msg = str(e)
        log_processing_record(file_name, '失败', error_msg)
        if utils.g_logger:
            utils.g_logger.error(f"处理文件失败 {file_name}: {error_msg}")
        return {
            'file_name': file_name,
            'success': False,
            'error': error_msg,
            'features': None
        }


def main():
    """
    主函数：执行完整的文本数据清洗与分析流程
    """
    parser = argparse.ArgumentParser(description='文本数据清洗与分析工具')
    parser.add_argument(
        '--input-dir',
        type=str,
        default=config.INPUT_DIR,
        help='输入文件目录（默认: ./data/input）'
    )
    parser.add_argument(
        '--generate-summary',
        action='store_true',
        default=True,
        help='是否生成汇总报告（默认: True）'
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("文本数据清洗与分析工具")
    print("=" * 60)
    
    initialize_logger()
    
    utils.g_logger.info("=" * 50)
    utils.g_logger.info("开始执行文本数据清洗与分析流程")
    utils.g_logger.info("=" * 50)
    
    ensure_output_directories()
    
    try:
        reader = DataReader(args.input_dir)
        cleaner = DataCleaner()
        extractor = FeatureExtractor()
        reporter = ReportGenerator()
        
        reader.read_readonly_reference()
        
        file_names = reader.list_input_files()
        
        if not file_names:
            print(f"警告: 输入目录 {args.input_dir} 中未找到有效文件")
            utils.g_logger.warning("未找到有效输入文件")
            return
        
        print(f"\n发现 {len(file_names)} 个待处理文件:")
        for name in file_names:
            print(f"  - {name}")
        
        print("\n开始处理...\n")
        
        results = []
        for file_name in file_names:
            result = process_single_file(file_name, reader, cleaner, extractor, reporter)
            results.append(result)
            
            status = "✅ 成功" if result['success'] else "❌ 失败"
            print(f"[{status}] {file_name}")
        
        print("\n" + "=" * 60)
        print("处理完成！")
        print("=" * 60)
        
        analysis_results = []
        for r in results:
            analysis_results.append({
                'file_name': r['file_name'],
                'features': r['features'],
                'error': r['error']
            })
        
        report_infos = reporter.generate_batch_reports(analysis_results)
        
        if args.generate_summary:
            summary_path = generate_summary_report(report_infos)
            print(f"\n汇总报告: {summary_path}")
        
        success_count = sum(1 for r in results if r['success'])
        failed_count = len(results) - success_count
        
        print(f"\n处理统计:")
        print(f"  总文件数: {len(results)}")
        print(f"  成功: {success_count}")
        print(f"  失败: {failed_count}")
        
        utils.g_logger.info(f"流程完成: 成功 {success_count}, 失败 {failed_count}")
        
    except Exception as e:
        utils.g_logger.error(f"主流程执行失败: {str(e)}", exc_info=True)
        print(f"\n错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
