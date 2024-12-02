import argparse
import logging
import sys
from .config import load_config, setup_logging
from .pdf import process_folder

def parse_arguments():
    parser = argparse.ArgumentParser(description='PDF图片方向自动修正工具')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--api-key', help='百度OCR API Key')
    parser.add_argument('--secret-key', help='百度OCR Secret Key')
    parser.add_argument('--input-folder', help='输入文件夹路径')
    parser.add_argument('--output-folder', help='输出文件夹路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # 加载配置
    config = load_config(args.config)
    
    # 设置日志级别
    setup_logging(config.get('debug', False))
    
    # 命令行参数优先级高于配置文件
    if args.api_key:
        config['api_key'] = args.api_key
    if args.secret_key:
        config['secret_key'] = args.secret_key
    if args.input_folder:
        config['input_folder'] = args.input_folder
    if args.output_folder:
        config['output_folder'] = args.output_folder
    if args.debug:
        config['debug'] = True
        setup_logging(True)
    
    # 验证必要参数
    if not config['api_key'] or not config['secret_key']:
        logging.error("错误：必须提供百度OCR的API Key和Secret Key")
        sys.exit(1)
    
    if not config['input_folder']:
        logging.error("错误：必须指定输入文件夹路径")
        sys.exit(1)
    
    try:
        process_folder(config)
        logging.info("所有PDF文件已处理完成。")
    except Exception as e:
        logging.error(f"处理过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 