import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance
import io
import argparse
import re

# 配置Tesseract路径（如果未加入系统PATH中）
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def get_image_from_pdf(page):
    """从PDF页面中提取图像"""
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img

def preprocess_image(image):
    """对图像进行预处理：针对潦草汉字的优化"""
    # 确保图像有正确的DPI信息
    dpi = 300
    image.info['dpi'] = (dpi, dpi)
    
    # 计算新的尺寸，确保图像足够大以供识别
    width = int(image.width * 1.5)  # 放大1.5倍
    height = int(image.height * 1.5)
    
    # 使用高质量的重采样方法
    image = image.convert('RGB')
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    
    # 增强对比度
    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(2.0)  # 增加对比度
    
    # 增加锐度
    sharpness = ImageEnhance.Sharpness(image)
    image = sharpness.enhance(1.5)
    
    # 转换为灰度图像
    image = image.convert('L')
    
    # 使用自适应阈值
    threshold = 150  # 降低阈值以保留更多文字
    image = image.point(lambda x: 0 if x < threshold else 255, '1')
    
    return image

def detect_orientation(image):
    """使用OCR检测图像方向"""
    try:
        # 优化OCR配置
        custom_config = r'--oem 3 --psm 0 -l chi_sim ' \
                       r'--dpi 300 ' \
                       r'-c tessedit_do_invert=0 ' \
                       r'-c tessedit_pageseg_mode=0 ' \
                       r'-c textord_heavy_nr=0 ' \
                       r'-c textord_min_linesize=1.5'
        
        # 转换为RGB模式（某些版本的Tesseract在处理二值图像时可能有问题）
        if image.mode == '1':
            image = image.convert('RGB')
        
        # 尝试多次检测
        max_attempts = 3
        rotations = []
        
        for _ in range(max_attempts):
            try:
                osd = pytesseract.image_to_osd(
                    image, 
                    config=custom_config,
                    output_type=pytesseract.Output.DICT
                )
                rotation = int(osd.get('rotate', 0))
                confidence = float(osd.get('orientation_conf', 0))
                
                if confidence > 1.0:  # 只记录置信度较高的结果
                    rotations.append(rotation)
            except Exception:
                continue
        
        # 如果有有效的旋转结果，返回出现最多的角度
        if rotations:
            from collections import Counter
            most_common = Counter(rotations).most_common(1)[0]
            rotation_angle = most_common[0]
            rotation_count = most_common[1]
            
            if rotation_count >= 2:  # 至少有2次相同的检测结果
                print(f"检测到可信的旋转角度: {rotation_angle}度")
                return rotation_angle
        
        print("未能确定可信的旋转角度，保持原方向")
        return 0
        
    except Exception as e:
        print(f"检测方向时出错: {e}")
        # 保存调试图像
        try:
            debug_path = f"debug_image_{hash(str(image))}.png"
            image.save(debug_path)
            print(f"已保存调试图像到: {debug_path}")
        except Exception as save_error:
            print(f"保存调试图像失败: {save_error}")
        return 0

def correct_pdf_orientation(input_pdf, output_pdf):
    """自动校正PDF页面方向"""
    success_count = 0
    fail_count = 0
    fail_reasons = []

    try:
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
                processed_image.save(f"debug_page_{page_num+1}.png")  # 保存处理后的图片用于调试
                # 检测方向
                rotation = detect_orientation(processed_image)
                
                # 根据检测结果旋转页面
                if rotation == 90:
                    page.set_rotation(90)
                    success_count += 1
                    print(f"第{page_num + 1}页：旋转角度为90°")
                elif rotation == 180:
                    page.set_rotation(180)
                    success_count += 1
                    print(f"第{page_num + 1}页：旋转角度为180°")
                elif rotation == 270:
                    page.set_rotation(270)
                    success_count += 1
                    print(f"第{page_num + 1}页：旋转角度为270°")
                else:
                    print(f"第{page_num + 1}页：无需旋转")
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
