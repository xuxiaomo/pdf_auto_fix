import io
import os
import sys
import logging
import argparse
import base64
import time
from threading import Lock

import fitz  # PyMuPDF
import yaml
import requests
from PIL import Image


def setup_logging(debug=False):
    """配置日志记录器"""
    level = logging.DEBUG if debug else logging.INFO
    
    # 自定义日志格式
    class CustomFormatter(logging.Formatter):
        """自定义日志格式器"""
        grey = "\x1b[38;21m"
        blue = "\x1b[34;21m"
        yellow = "\x1b[33;21m"
        red = "\x1b[31;21m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"

        format_str = "%(asctime)s - %(levelname)s - %(message)s"

        FORMATS = {
            logging.DEBUG: grey + format_str + reset,
            logging.INFO: blue + format_str + reset,
            logging.WARNING: yellow + format_str + reset,
            logging.ERROR: red + format_str + reset,
            logging.CRITICAL: bold_red + format_str + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
            return formatter.format(record)

    # 配置日志处理器
    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有的处理器
    root_logger.handlers = []
    root_logger.addHandler(handler)

def singleton(cls):
    """单例模式装饰器"""
    _instance = {}
    
    def get_instance(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]
    
    return get_instance

class RateLimiter:
    def __init__(self, rate=2):  # rate: 每秒允许的请求数
        self.rate = rate
        self.tokens = rate  # 当前可用令牌数
        self.last_update = time.time()
        self.lock = Lock()
    
    def acquire(self):
        with self.lock:
            now = time.time()
            # 计算从上次更新到现在应该添加的令牌
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens < 1:
                # 需要等待的时间
                wait_time = (1 - self.tokens) / self.rate
                time.sleep(wait_time)
                self.tokens = 0
                self.last_update = time.time()
            else:
                self.tokens -= 1

@singleton
class PDFRotator:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.token = self.get_access_token()
        self.rate_limiter = RateLimiter(rate=2)
        # 在初始化时定义可用的API列表和失败计数器
        self.available_api_list = [
            "handwriting",
            "general_basic",
            "general",
            "accurate_basic", 
            "accurate",
            "webimage",
        ]
        # 初始化失败计数器字典
        self.api_fail_count = {api: 0 for api in self.available_api_list}
        # 设置最大失败次数
        self.max_fail_count = 3

    def get_access_token(self):
        """获取百度AI的access_token"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials", 
            "client_id": self.api_key, 
            "client_secret": self.secret_key
        }
        return str(requests.post(url, params=params).json().get("access_token"))

    def get_result_from_api(self, image, api_name):
        # 在发送请求前获取令牌
        self.rate_limiter.acquire()
        
        img_str = self._image_to_base64(image)
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{api_name}?access_token={self.token}"

        payload = {
            "image": img_str,
            "detect_direction": "true",
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        return result

    def auto_switch_api(self, image):
        for api in self.available_api_list:
            result = self.get_result_from_api(image, api)
            if result.get("direction") is not None:
                # 成功时重置失败计数
                self.api_fail_count[api] = 0
                return result
            else:
                logging.warning(f"接口不可用: {api}, Error Code: {result.get('error_code')}, Error Message: {result.get('error_msg')}")
                self.api_fail_count[api] += 1
            
            # 检查失败次数是否达到上限
            if self.api_fail_count[api] >= self.max_fail_count:
                logging.warning(f"接口 {api} 连续失败 {self.max_fail_count} 次，从可用列表中移除")
                self.available_api_list.remove(api)
                del self.api_fail_count[api]
        
        raise Exception("没有可用的OCR接口")

    def _image_to_base64(self, image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str

def get_image_from_pdf(page):
    """从PDF页面中提取图像"""
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img

def detect_orientation(image, config):
    """使用百度OCR检测图像方向"""
    ocr = PDFRotator(config['api_key'], config['secret_key'])
    result = ocr.auto_switch_api(image)
    
    if 'direction' in result:
        # 百度OCR返回的direction: 0:正向，1:逆时针90度，2:逆时针180度，3:逆时针270度
        direction_map = {
            0: 0,
            1: 90,
            2: 180,
            3: 270
        }
        angle = direction_map.get(result['direction'], 0)
        return angle, 1.0
    else:
        raise Exception("未检测到方向信息")

class ProcessStats:
    """处理统计类"""
    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.total_pages = 0
        self.rotated_pages = 0
        self.failed_pages = 0
        self.failed_files = 0

    def add_file_result(self, pages, rotated, failed):
        """添加单个文件的处理结果"""
        self.total_pages += pages
        self.rotated_pages += rotated
        self.failed_pages += failed
        self.processed_files += 1
        if failed > 0:
            self.failed_files += 1

    def get_summary(self):
        """获取处理汇总信息"""
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_pages": self.total_pages,
            "rotated_pages": self.rotated_pages,
            "failed_pages": self.failed_pages,
            "failed_files": self.failed_files
        }

def correct_pdf_orientation(input_pdf, output_pdf, config):
    """自动校正PDF页面方向"""
    success_count = 0
    fail_count = 0

    doc = fitz.open(input_pdf)
    total_pages = len(doc)
    
    if total_pages == 0:
        logging.warning("PDF文件为空")
        doc.close()
        return total_pages, success_count, fail_count
        
    logging.info(f"PDF文件共 {total_pages} 页")
    
    for page_num in range(total_pages):
        try:
            page = doc[page_num]
            
            # 提取页面图像
            image = get_image_from_pdf(page)
            
            # 获取旋转角度和置信度
            rotation, confidence = detect_orientation(image, config)
            
            # 根据检测结果旋转页面
            if rotation != 0:
                page.set_rotation(rotation)
                success_count += 1
                logging.info(f"第 {page_num + 1} 页: 旋转 {rotation}° (置信度: {confidence:.2f})")
            else:
                logging.debug(f"第 {page_num + 1} 页: 无需旋转 (置信度: {confidence:.2f})")
                
        except Exception as e:
            fail_count += 1
            logging.error(f"处理第 {page_num + 1} 页时出错: {str(e)}")

    # 保存校正后的PDF
    doc.save(output_pdf)
    doc.close()

    # 输出最终结果
    if success_count > 0:
        logging.info(f"校正完成: {output_pdf}")
        logging.info(f"成功调整 {success_count} 页，失败 {fail_count} 页")
    else:
        logging.warning(f"没有成功调整任何页面，失败 {fail_count} 页")
    
    return total_pages, success_count, fail_count

def process_folder(config, progress_callback=None):
    """递归扫描文件夹并修复所有PDF文件"""
    input_folder = config['input_folder']
    output_folder = config['output_folder']
    
    stats = ProcessStats()
    
    # 首先统计总文件数
    stats.total_files = sum(1 for root, _, files in os.walk(input_folder) 
                     for file in files if file.lower().endswith(".pdf"))
    
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                # 获取相对路径
                rel_path = os.path.relpath(root, input_folder)
                
                # 构建输入和输出路径
                input_pdf = os.path.abspath(os.path.join(root, file))
                output_dir = os.path.abspath(os.path.join(output_folder, rel_path))
                os.makedirs(output_dir, exist_ok=True)
                output_pdf = os.path.join(output_dir, file)
                
                logging.info(f"正在处理文件: {input_pdf}")
                total_pages, rotated, failed = correct_pdf_orientation(input_pdf, output_pdf, config)
                stats.add_file_result(total_pages, rotated, failed)
                
                if progress_callback:
                    progress_callback(stats.processed_files, stats.total_files)
    
    # 输出汇总信息
    summary = stats.get_summary()
    logging.info("----------------------------------------")
    logging.info("处理完成，汇总信息：")
    logging.info(f"总文件数: {summary['total_files']}")
    logging.info(f"处理文件数: {summary['processed_files']}")
    logging.info(f"总页数: {summary['total_pages']}")
    logging.info(f"旋转页数: {summary['rotated_pages']}")
    logging.info(f"失败页数: {summary['failed_pages']}")
    logging.info(f"失败文件数: {summary['failed_files']}")
    logging.info("----------------------------------------")
    
    return stats

def load_config(config_file=None):
    """加载配置文件"""
    default_config = {
        'api_key': None,
        'secret_key': None,
        'input_folder': None,
        'output_folder': None,
        'debug': False
    }
    
    if config_file:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                default_config.update(config)
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
    
    return default_config

def parse_arguments():
    parser = argparse.ArgumentParser(description="批量修复PDF页面方向")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--api-key", help="百度OCR API Key")
    parser.add_argument("--secret-key", help="百度OCR Secret Key")
    parser.add_argument("--input-folder", help="输入文件夹路径")
    parser.add_argument("--output-folder", help="输出文件夹路径")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    return parser.parse_args()

if __name__ == "__main__":
    if len(sys.argv) > 1:  # 如果有命令行参数，使用命令行模式
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
            setup_logging(True)  # 重新设置日志级别
        
        # 验证必要参数
        if not config['api_key'] or not config['secret_key']:
            logging.error("错误：必须提供百度OCR的API Key和Secret Key")
            sys.exit(1)
        
        if not config['input_folder']:
            logging.error("错误：必须指定输入文件夹路径")
            sys.exit(1)
        
        if not config['output_folder']:
            # 修改为与input_folder平级的output目录
            input_parent = os.path.dirname(config['input_folder'])  # 获取input的父目录
            config['output_folder'] = os.path.join(input_parent, 'output')
        
        if not os.path.exists(config['input_folder']):
            logging.error(f"输入文件夹不存在: {config['input_folder']}")
            sys.exit(1)
        
        os.makedirs(config['output_folder'], exist_ok=True)
        process_folder(config, None)
        logging.info("所有PDF文件已处理完成。")
    else:  # 如果没有命令行参数，启动GUI
        from gui import main
        main()
