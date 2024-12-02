from setuptools import setup, find_packages
from pdf_auto_rotate.__version__ import __version__

setup(
    name="pdf-auto-rotate",
    version=__version__,
    author="xuxiaomo",
    author_email="helloxiaomo@gmail.com",
    description="自动检测和修正PDF文件中图片方向的工具",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/xuxiaomo/pdf-auto-rotate",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "baidu-aip",
        "PyMuPDF",
        "Pillow",
        "PyYAML",
        "requests"
    ],
) 