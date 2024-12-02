import os
import logging
import fitz
from PIL import Image
from io import BytesIO
from .ocr import BaiduOCR

def process_folder(config):
    """处理文件夹中的所有PDF文件"""
    ocr = BaiduOCR(config['api_key'], config['secret_key'])
    
    input_folder = config['input_folder']
    output_folder = config['output_folder']
    
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.pdf'):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            try:
                process_pdf(input_path, output_path, ocr)
                logging.info(f"成功处理文件: {filename}")
            except Exception as e:
                logging.error(f"处理文件 {filename} 时出错: {str(e)}")

def process_pdf(input_path, output_path, ocr):
    """处理单个PDF文件"""
    doc = fitz.open(input_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        for _, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # 检测方向
            orientation, _ = ocr.detect_orientation(image_bytes)
            if orientation != 0:
                # 旋转图片
                img = Image.open(BytesIO(image_bytes))
                rotated_img = img.rotate(orientation, expand=True)
                
                # 将旋转后的图片替换回PDF
                img_bytes = BytesIO()
                rotated_img.save(img_bytes, format=img.format)
                page.replace_image(xref, img_bytes.getvalue())
    
    doc.save(output_path)
    doc.close() 