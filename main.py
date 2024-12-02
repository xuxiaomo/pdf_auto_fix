import os
import fitz  # PyMuPDF
import requests
import base64
from PIL import Image
import io
import argparse
import re
import numpy as np

# 百度OCR API密钥
API_KEY = "eHXu6KgWw18TNWxStKWWcwm2"
SECRET_KEY = "H77fFvbXTmIJyvRydDNKKB9SThhCtCME"

class BaiduOCR:
    def __init__(self, api_key, secret_key):
        self.API_KEY = api_key
        self.SECRET_KEY = secret_key
        self.token = self.get_access_token()
    
    def get_access_token(self):
        """获取百度AI的access_token"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials", 
            "client_id": self.API_KEY, 
            "client_secret": self.SECRET_KEY
        }
        return str(requests.post(url, params=params).json().get("access_token"))

def get_image_from_pdf(page):
    """从PDF页面中提取图像"""
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img

def detect_orientation(image, page_num):
    """使用百度OCR检测图像方向"""
    global ocr
    if 'ocr' not in globals():
        ocr = BaiduOCR(API_KEY, SECRET_KEY)
        
    # 将PIL图像转换为字节流
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=95)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # API URL
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/webimage_loc?access_token={ocr.token}"
    
    try:
        # 请求参数
        data = {
            'image': img_str,
            'detect_direction': 'true',  # 检测方向
            'poly_location': 'false',    # 不需要多边形顶点
            'probability': 'false'       # 不需要置信度
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # 发送请求
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        
        if 'direction' in result:
            # 百度OCR返回的direction: 0:正向，1:逆时针90度，2:逆时针180度，3:逆时针270度
            direction_map = {
                0: 0,
                1: 90,
                2: 180,
                3: 270
            }
            angle = direction_map.get(result['direction'], 0)
            print(f"第 {page_num + 1} 页：检测到方向 {angle}°")
            return angle, 1.0
            
        else:
            print(f"第 {page_num + 1} 页：未检测到方向信息")
            return 0, 0.0
            
    except Exception as e:
        print(f"第 {page_num + 1} 页：方向检测失败 - {str(e)}")
        return 0, 0.0

def correct_pdf_orientation(input_pdf, output_pdf):
    """自动校正PDF页面方向"""
    success_count = 0
    fail_count = 0

    # 创建以输入文件名命名的调试目录
    input_filename = os.path.splitext(os.path.basename(input_pdf))[0]
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    debug_dir = os.path.join(temp_dir, input_filename)
    os.makedirs(debug_dir, exist_ok=True)

    doc = fitz.open(input_pdf)
    total_pages = len(doc)
    print(f"开始处理PDF文件，共 {total_pages} 页")
    
    for page_num in range(total_pages):
        print(f"正在处理第 {page_num + 1}/{total_pages} 页...")
        page = doc[page_num]
        
        # 提取页面图像并预处理
        image = get_image_from_pdf(page)
        image.save(os.path.join(debug_dir, f"page_{page_num + 1}.png"))
        
        # 获取旋转角度和置信度
        rotation, confidence = detect_orientation(image, page_num)
        
        # 根据检测结果旋转页面
        if rotation == 90:
            page.set_rotation(90)
            success_count += 1
            print(f"第{page_num + 1}页：旋转角度为90° (置信度: {confidence:.2f})")
        elif rotation == 180:
            page.set_rotation(180)
            success_count += 1
            print(f"第{page_num + 1}页：旋转角度为180° (置信度: {confidence:.2f})")
        elif rotation == 270:
            page.set_rotation(270)
            success_count += 1
            print(f"第{page_num + 1}页：旋转角度为270° (置信度: {confidence:.2f})")
        else:
            print(f"第{page_num + 1}页：无需旋转 (置信度: {confidence:.2f})")

    # 保存校正后的PDF
    doc.save(output_pdf)
    doc.close()

    # 输出最终结果
    if success_count > 0:
        print(f"校正完成: {output_pdf}")
        print(f"成功调整 {success_count} 页，失败 {fail_count} 页")
    else:
        print(f"没有成功调整任何页面，失败 {fail_count} 页")

def process_folder(folder_path, output_folder):
    """递归扫描文件夹并修复所有PDF文件"""
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".pdf"):
                input_pdf = os.path.join(root, file)
                relative_path = os.path.relpath(root, folder_path)
                output_dir = os.path.join(output_folder, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                output_pdf = os.path.join(output_dir, file)
                print(f"正在处理文件: {input_pdf}")
                correct_pdf_orientation(input_pdf, output_pdf)

if __name__ == "__main__":
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="批量修复PDF页面方向")
    parser.add_argument("input_folder", help="输入文件夹路径")
    parser.add_argument("output_folder", help="输出文件夹路径")

    # 解析命令行参数
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder

    if not os.path.exists(input_folder):
        print(f"输入文件夹不存在: {input_folder}")
    else:
        os.makedirs(output_folder, exist_ok=True)
        process_folder(input_folder, output_folder)
        print("所有PDF文件已处理完成。")
