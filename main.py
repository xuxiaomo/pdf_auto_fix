import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

# 配置Tesseract路径（如果未加入系统PATH中）
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def get_image_from_pdf(page):
    """从PDF页面中提取图像"""
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img

def detect_orientation(image):
    """使用OCR检测图像方向"""
    try:
        osd = pytesseract.image_to_osd(image)
        rotation = int(re.search(r'(?<=Rotate: )\d+', osd).group(0))
        return rotation
    except Exception as e:
        print(f"检测方向时出错: {e}")
        return 0  # 默认无旋转

def correct_pdf_orientation(input_pdf, output_pdf):
    """自动校正PDF页面方向"""
    try:
        doc = fitz.open(input_pdf)
        for page_num in range(len(doc)):
            page = doc[page_num]
            # 提取页面图像
            image = get_image_from_pdf(page)
            # 检测方向
            rotation = detect_orientation(image)
            # 根据检测结果旋转页面
            if rotation == 90:
                page.set_rotation(90)
            elif rotation == 180:
                page.set_rotation(180)
            elif rotation == 270:
                page.set_rotation(270)
        # 保存校正后的PDF
        doc.save(output_pdf)
        doc.close()
        print(f"校正完成: {output_pdf}")
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
    # 输入和输出文件夹
    input_folder = "path/to/your/input/folder"  # 修改为实际输入文件夹路径
    output_folder = "path/to/your/output/folder"  # 修改为实际输出文件夹路径

    if not os.path.exists(input_folder):
        print(f"输入文件夹不存在: {input_folder}")
    else:
        os.makedirs(output_folder, exist_ok=True)
        process_folder(input_folder, output_folder)
        print("所有PDF文件已处理完成。")
