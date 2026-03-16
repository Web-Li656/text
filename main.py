"""
主程序入口模块
负责解析命令行参数、调用各模块执行完整处理流程
"""

import os
import sys
import argparse
import json
from typing import Optional, List

import config
import utils as utils_module
from utils import (
    initialize_logger,
    ensure_output_directories,
    log_processing_record,
    validate_relative_path,
    ProcessingError,
    g_logger
)
from data_reader import DataReader
from data_cleaner import DataCleaner, extract_text_for_analysis
from feature_extractor import FeatureExtractor
from report_generator import ReportGenerator, generate_summary_report


class TextProcessor:
    """文本处理器主类"""
    
    def __init__(self):
        """初始化文本处理器"""
        self.reader = None
        self.cleaner = None
        self.extractor = None
        self.report_generator = None
        self.processing_results = []
    
    def initialize(self) -> bool:
        """
        初始化处理环境
        
        Returns:
            初始化是否成功
        """
        global g_logger
        
        try:
            # 初始化日志
            logger = initialize_logger()
            g_logger = utils_module.g_logger
            g_logger.info("=" * 50)
            g_logger.info("文本数据清洗与分析工具启动")
            g_logger.info("=" * 50)
            
            # 确保输出目录存在
            dir_results = ensure_output_directories()
            for dir_path, success in dir_results.items():
                if not success:
                    g_logger.error(f"无法创建目录: {dir_path}")
                    return False
            
            # 验证输入目录
            if not validate_relative_path(config.INPUT_DIR, must_exist=True):
                g_logger.error(f"输入目录无效或不存在: {config.INPUT_DIR}")
                return False
            
            # 初始化各模块
            self.reader = DataReader(config.INPUT_DIR)
            self.cleaner = DataCleaner()
            self.extractor = FeatureExtractor(config.TOP_N_WORDS)
            self.report_generator = ReportGenerator(config.OUTPUT_REPORTS_DIR)
            
            g_logger.info("初始化完成")
            return True
            
        except Exception as e:
            if g_logger:
                g_logger.error(f"初始化失败: {str(e)}")
            else:
                print(f"初始化失败: {str(e)}")
            return False
    
    def save_cleaned_data(self, cleaned_data: dict) -> bool:
        """
        保存清洗后的数据
        
        Args:
            cleaned_data: 清洗后的数据字典
        
        Returns:
            保存是否成功
        """
        global g_logger
        
        try:
            file_name = cleaned_data.get('file_name', '')
            
            # 确定输出文件路径
            output_path = os.path.join(config.OUTPUT_CLEANED_DIR, file_name)
            
            # 验证输出路径为相对路径
            if not validate_relative_path(output_path):
                raise ProcessingError(f"输出路径必须使用相对路径: {output_path}", file_name)
            
            # 确保输出目录存在
            os.makedirs(config.OUTPUT_CLEANED_DIR, exist_ok=True)
            
            # 获取要保存的内容
            content = cleaned_data.get('cleaned_content', '')
            
            # 如果是JSON文件且有结构化数据，保存JSON格式
            if cleaned_data.get('is_json') and cleaned_data.get('cleaned_data'):
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data['cleaned_data'], f, ensure_ascii=False, indent=2)
            else:
                # 保存文本内容
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            if g_logger:
                g_logger.info(f"清洗数据已保存: {output_path}")
            
            return True
            
        except Exception as e:
            if g_logger:
                g_logger.error(f"保存清洗数据失败: {str(e)}")
            return False
    
    def process_single_file(self, file_data: dict) -> dict:
        """
        处理单个文件
        
        Args:
            file_data: 文件数据字典
        
        Returns:
            处理结果字典
        """
        global g_logger
        
        file_name = file_data.get('file_name', '')
        result = {
            'file_name': file_name,
            'status': '失败',
            'reason': None,
            'char_count': 0,
            'word_count': 0,
            'top_words': []
        }
        
        try:
            # 检查文件是否有效
            if not file_data.get('is_valid', True):
                result['reason'] = file_data.get('error_message', '文件验证失败')
                log_processing_record(file_name, '失败', result['reason'])
                return result
            
            # 步骤1: 数据清洗
            if g_logger:
                g_logger.info(f"开始清洗: {file_name}")
            
            cleaned_data = self.cleaner.process_file(file_data)
            
            # 保存清洗后的数据
            if not self.save_cleaned_data(cleaned_data):
                result['reason'] = '保存清洗数据失败'
                log_processing_record(file_name, '失败', result['reason'])
                return result
            
            # 步骤2: 特征提取
            if g_logger:
                g_logger.info(f"开始特征提取: {file_name}")
            
            text = extract_text_for_analysis(cleaned_data)
            features = self.extractor.extract_features(text)
            
            # 更新结果
            result['status'] = '成功'
            result['char_count'] = features.get('char_count', 0)
            result['word_count'] = features.get('word_count', 0)
            result['top_words'] = features.get('top_words', [])
            
            # 生成报告
            analysis_result = {
                'file_name': file_name,
                'features': features,
                'error': None
            }
            self.report_generator.generate_and_save_report(analysis_result)
            
            log_processing_record(
                file_name,
                '成功',
                extra_info={
                    '字符数': result['char_count'],
                    '单词数': result['word_count']
                }
            )
            
            if g_logger:
                g_logger.info(f"文件处理完成: {file_name}")
            
        except Exception as e:
            error_msg = str(e)
            result['reason'] = error_msg
            log_processing_record(file_name, '失败', error_msg)
            
            # 生成错误报告
            try:
                error_analysis = {
                    'file_name': file_name,
                    'features': None,
                    'error': error_msg
                }
                self.report_generator.generate_and_save_report(error_analysis)
            except:
                pass
        
        return result
    
    def run(self) -> bool:
        """
        执行完整的处理流程
        
        Returns:
            处理是否成功完成
        """
        global g_logger
        
        try:
            # 读取所有输入文件
            if g_logger:
                g_logger.info("开始读取输入文件...")
            
            file_data_list = self.reader.read_all_files()
            
            if not file_data_list:
                g_logger.warning("未发现有效的输入文件")
                return False
            
            g_logger.info(f"共读取 {len(file_data_list)} 个文件")
            
            # 处理每个文件
            self.processing_results = []
            for file_data in file_data_list:
                result = self.process_single_file(file_data)
                self.processing_results.append(result)
            
            # 生成汇总报告
            try:
                report_infos = []
                for result in self.processing_results:
                    report_infos.append({
                        'original_file': result['file_name'],
                        'report_file': f"{os.path.splitext(result['file_name'])[0]}_analysis.md",
                        'status': result['status'],
                        'processing_time': ''
                    })
                
                generate_summary_report(report_infos)
            except Exception as e:
                g_logger.warning(f"生成汇总报告失败: {str(e)}")
            
            # 输出处理统计
            success_count = sum(1 for r in self.processing_results if r['status'] == '成功')
            failed_count = len(self.processing_results) - success_count
            
            g_logger.info("=" * 50)
            g_logger.info("处理完成统计:")
            g_logger.info(f"  总文件数: {len(self.processing_results)}")
            g_logger.info(f"  成功: {success_count}")
            g_logger.info(f"  失败: {failed_count}")
            g_logger.info("=" * 50)
            
            return failed_count == 0
            
        except Exception as e:
            if g_logger:
                g_logger.error(f"处理过程发生错误: {str(e)}")
            return False


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description='文本数据清洗与分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python main.py                    # 使用默认配置运行
  python main.py --verbose          # 显示详细日志
        '''
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志信息'
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        default=config.INPUT_DIR,
        help=f'输入目录路径 (默认: {config.INPUT_DIR})'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./build/dist',
        help='输出目录根路径 (默认: ./build/dist)'
    )
    
    return parser.parse_args()


def main() -> int:
    """
    主函数
    
    Returns:
        程序退出码 (0表示成功，1表示失败)
    """
    args = parse_arguments()
    
    # 更新配置（如果需要）
    if args.input_dir != config.INPUT_DIR:
        config.INPUT_DIR = args.input_dir
    
    if args.output_dir != './build/dist':
        config.OUTPUT_CLEANED_DIR = os.path.join(args.output_dir, 'cleaned')
        config.OUTPUT_REPORTS_DIR = os.path.join(args.output_dir, 'reports')
        config.LOG_DIR = args.output_dir
    
    # 创建处理器并运行
    processor = TextProcessor()
    
    if not processor.initialize():
        print("初始化失败，程序退出")
        return 1
    
    success = processor.run()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
