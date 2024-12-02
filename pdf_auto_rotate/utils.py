import os
import logging
from PIL import Image
from io import BytesIO

def get_image_format(image_bytes):
    """获取图片格式"""
    try:
        img = Image.open(BytesIO(image_bytes))
        return img.format.lower()
    except Exception as e:
        logging.error(f"无法识别图片格式: {str(e)}")
        return None

def create_directories(*paths):
    """创建多个目录"""
    for path in paths:
        os.makedirs(path, exist_ok=True) 

def singleton(cls):
    """单例模式装饰器"""
    _instance = {}
    
    def get_instance(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]
    
    return get_instance
