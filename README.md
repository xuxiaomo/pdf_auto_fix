# PDF图片方向自动修正工具

这是一个使用百度OCR API自动检测和修正PDF文件中图片方向的工具。当PDF文件中的图片方向不正确时（如倒置、歪斜等），本工具可以自动将其调整为正确方向。

## 功能特点

- 自动检测PDF中的图片方向
- 自动旋转图片到正确方向
- 批量处理多个PDF文件
- 保持原PDF文件质量

## 环境要求

- Python 3.6+
- 百度OCR API账号

## 快速开始

1. 克隆项目到本地
2. 配置项目：
   - 复制配置文件模板：
     ```bash
     cp config.yaml.template config.yaml
     ```
   - 编辑 `config.yaml`，填入你的百度OCR API密钥

3. 使用方法：
   - 将需要修正的PDF文件放入 `input` 文件夹
   - 运行程序：
     ```bash
     python main.py
     ```
   - 修正后的PDF文件将保存在 `output` 文件夹中

## 配置说明

配置文件 `config.yaml` 包含以下设置：

- `api_key`: 百度OCR API的API Key
- `secret_key`: 百度OCR API的Secret Key
- `input_folder`: 输入文件夹路径（默认: ./input）
- `output_folder`: 输出文件夹路径（默认: ./output）
- `debug`: 调试模式开关（true/false）

## 注意事项

- 首次使用需要基于 `config.yaml.template` 创建配置文件
- 请勿将包含密钥的 `config.yaml` 提交到代码仓库

## 获取百度OCR API密钥

1. 访问[百度AI开放平台](https://ai.baidu.com/)
2. 注册/登录账号
3. 创建OCR应用
4. 获取API Key和Secret Key

## 许可证

MIT License
