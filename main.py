import os
import fitz  # PyMuPDF
import pytesseract
import cv2  # 添加这行
from PIL import Image, ImageEnhance
import io
import argparse
import re
import numpy as np

# 配置Tesseract路径（如果未加入系统PATH中）
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def get_image_from_pdf(page):
    """从PDF页面中提取图像"""
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img

def preprocess_image(image):
    """预处理图像"""
    # 转换为灰度图像
    gray_image = image.convert('L')
    
    # 调整图像大小
    resized_image = gray_image.resize((gray_image.width * 2, gray_image.height * 2))
    
    # 增强对比度
    enhancer = ImageEnhance.Contrast(resized_image)
    enhanced_image = enhancer.enhance(2.0)  # 增强对比度的倍数
    
    return enhanced_image

def detect_orientation(image, page_num):
    """使用OCR检测图像方向"""
    try:
        # OCR配置
        custom_config = (
            'osd '
            '--oem 3 '
            '--psm 0 '
            '-l chi_sim '
            '--dpi 300 '
            '-c preserve_interword_spaces=1 '
            '-c tessedit_char_whitelist=一二三四五六七八九十1234567890 '
        )

        osd = pytesseract.image_to_osd(
            image,
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )

        rotation = int(osd.get('rotate', 0))
        confidence = float(osd.get('orientation_conf', 0))

        if confidence > 0.5:  # 降低置信度阈值
            return rotation, confidence
        else:
            print(f"第{page_num + 1}页：置信度不足，保持原方向 (置信度: {confidence:.2f})")
            return 0, 0.0

    except Exception as e:
        print(f"第{page_num + 1}页：检测方向时出错: {str(e)}")
        return 0, 0.0

def correct_pdf_orientation(input_pdf, output_pdf):
    """自动校正PDF页面方向"""
    success_count = 0
    fail_count = 0
    fail_reasons = []

    try:
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
            try:
                # 提取页面图像并预处理
                image = get_image_from_pdf(page)
                processed_image = preprocess_image(image)
                # 保存预处理后的图片
                processed_image_path = os.path.join(debug_dir, f'processed_page_{page_num + 1}.png')
                processed_image.save(processed_image_path)
                print(f"已保存预处理图片到: {processed_image_path}")
                
                # 获取旋转角度和置信度
                rotation, confidence = detect_orientation(processed_image, page_num)
                
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
            except Exception as e:
                fail_count += 1
                fail_reasons.append(f"第{page_num + 1}页调整失败，原因: {e}")
                print(f"第{page_num + 1}页调整失败，原因: {e}")

        # 保存校正后的PDF
        doc.save(output_pdf)
        doc.close()

        # 输出最终结果
        if success_count > 0:
            print(f"校正完成: {output_pdf}")
            print(f"成功调整 {success_count} 页，失败 {fail_count} 页")
        else:
            print(f"没有成功调整任何页面，失败 {fail_count} 页")
    except Exception as e:
        print(f"处理文件 {input_pdf} 时出错: {e}")

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
