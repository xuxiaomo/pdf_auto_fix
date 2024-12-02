import os
import logging
import yaml

def setup_logging(debug=False):
    """设置日志级别和格式"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def load_config(config_path):
    """加载配置文件"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 设置默认值
    config.setdefault('debug', False)
    if config.get('output_folder') is None and config.get('input_folder'):
        config['output_folder'] = os.path.join(
            os.path.dirname(config['input_folder']), 
            'output'
        )
    
    return config

def validate_config(config):
    """验证配置是否完整"""
    required_fields = ['api_key', 'secret_key', 'input_folder']
    for field in required_fields:
        if not config.get(field):
            raise ValueError(f"配置缺少必要字段: {field}")
    
    if not os.path.exists(config['input_folder']):
        raise FileNotFoundError(f"输入文件夹不存在: {config['input_folder']}")
    
    # 确保输出文件夹存在
    os.makedirs(config['output_folder'], exist_ok=True) 