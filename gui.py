import os
import sys
import queue
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

import yaml # PyYAML

class IORedirector(object):
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.updating = True
        self.buffer = []
        self.last_update = 0
        self._redirect_setup()
        threading.Thread(target=self._update_text_widget, daemon=True).start()

    def _redirect_setup(self):
        # 保存原始的stdout和stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # 只重定向一次
        if not isinstance(sys.stdout, IORedirector):
            sys.stdout = self
        if not isinstance(sys.stderr, IORedirector):
            sys.stderr = self

    def write(self, string):
        if string.strip():
            import re
            clean_string = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', string)
            clean_string = ''.join(char for char in clean_string if ord(char) >= 32 or char in '\n\r\t')
            if clean_string.strip():
                self.queue.put(clean_string)

    def flush(self):
        pass

    def _update_text_widget(self):
        import time
        while self.updating:
            try:
                while True:
                    string = self.queue.get_nowait()
                    self.buffer.append(string)
                    
                    current_time = time.time()
                    if len(self.buffer) >= 10 or (current_time - self.last_update) > 0.1:
                        combined_text = ''.join(self.buffer)
                        self.text_widget.after(0, lambda t=combined_text: self._safe_update(t))
                        self.buffer = []
                        self.last_update = current_time
                        
            except queue.Empty:
                if self.buffer:
                    combined_text = ''.join(self.buffer)
                    self.text_widget.after(0, lambda t=combined_text: self._safe_update(t))
                    self.buffer = []
                    self.last_update = time.time()
                time.sleep(0.1)

    def _safe_update(self, text):
        try:
            current_length = float(self.text_widget.index('end-1c'))
            if current_length > 1000:
                self.text_widget.delete('1.0', f'{current_length-1000}.0')
            
            self.text_widget.insert(tk.END, text)
            self.text_widget.see(tk.END)
        except Exception as e:
            print(f"Error updating text widget: {e}", file=self.original_stderr)

    def __del__(self):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

class PDFOrientationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF方向修正工具")
        self.root.geometry("800x600")
        
        # 配置文件路径
        self.config_file = "config.yaml"
        
        if hasattr(sys, 'getwindowsversion'):
            self.root.option_add('*font', ('Microsoft YaHei UI', 9))
        
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.create_input_fields()
        self.create_log_area()
        self.create_buttons()
        
        # 加载保存的配置
        self.load_config()
        
        # 在窗口关闭时保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            self.main_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.progress.grid_remove()

    def load_config(self):
        """加载保存的配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:  # 确保配置不为空
                        self.api_key_var.set(config.get('api_key', ''))
                        self.secret_key_var.set(config.get('secret_key', ''))
                        self.input_folder_var.set(config.get('input_folder', ''))
                        self.output_folder_var.set(config.get('output_folder', ''))
                        self.debug_var.set(config.get('debug', False))
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")

    def save_config(self):
        """保存当前配置"""
        try:
            config = {
                'api_key': self.api_key_var.get(),
                'secret_key': self.secret_key_var.get(),
                'input_folder': self.input_folder_var.get(),
                'output_folder': self.output_folder_var.get(),
                'debug': self.debug_var.get()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            logging.info("配置已保存")
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")

    def on_closing(self):
        """窗口关闭时的处理"""
        self.save_config()
        self.root.destroy()

    def create_input_fields(self):
        # API Key
        ttk.Label(self.main_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(self.main_frame, textvariable=self.api_key_var)
        self.api_key_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Secret Key
        ttk.Label(self.main_frame, text="Secret Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.secret_key_var = tk.StringVar()
        self.secret_key_entry = ttk.Entry(self.main_frame, textvariable=self.secret_key_var)
        self.secret_key_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # 输入文件夹
        ttk.Label(self.main_frame, text="输入文件夹:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.input_folder_var = tk.StringVar()
        self.input_folder_entry = ttk.Entry(self.main_frame, textvariable=self.input_folder_var)
        self.input_folder_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(self.main_frame, text="浏览", command=self.browse_input_folder).grid(row=2, column=2, pady=5)

        # 输出文件夹
        ttk.Label(self.main_frame, text="输出文件夹:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.output_folder_var = tk.StringVar()
        self.output_folder_entry = ttk.Entry(self.main_frame, textvariable=self.output_folder_var)
        self.output_folder_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(self.main_frame, text="浏览", command=self.browse_output_folder).grid(row=3, column=2, pady=5)

        # Debug模式
        self.debug_var = tk.BooleanVar()
        ttk.Checkbutton(self.main_frame, text="Debug模式", variable=self.debug_var).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=5)

    def create_log_area(self):
        # 日志显示区域
        log_frame = ttk.LabelFrame(self.main_frame, text="运行日志", padding="5")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # 创建带滚动条的文本框
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=15,
            wrap=tk.WORD,
            font=('Microsoft YaHei UI', 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 创建单个IORedirector实例
        self.io_redirector = IORedirector(self.log_text)

    def create_buttons(self):
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="开始处理", command=self.start_processing).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清除日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side=tk.LEFT, padx=5)

    def browse_input_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            # 确保使用反斜杠
            folder = folder.replace('/', '\\')
            self.input_folder_var.set(folder)
            # 如果输出文件夹为空，设置为与input平级的output目录
            if not self.output_folder_var.get():
                input_parent = os.path.dirname(folder)  # 获取input的父目录
                output_folder = os.path.join(input_parent, 'output').replace('/', '\\')
                self.output_folder_var.set(output_folder)
            self.save_config()  # 自动保存配置

    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder_var.set(folder)
            self.save_config()  # 自动保存配置

    def clear_log(self):
        self.log_text.delete('1.0', tk.END)
        self.log_text.update_idletasks()

    def start_processing(self):
        # 获取输入值
        config = {
            'api_key': self.api_key_var.get(),
            'secret_key': self.secret_key_var.get(),
            'input_folder': self.input_folder_var.get(),
            'output_folder': self.output_folder_var.get(),
            'debug': self.debug_var.get()
        }

        # 验证输入
        if not all([config['api_key'], config['secret_key'], config['input_folder']]):
            logging.error("请填写所有必要的字段！")
            return

        # 在新线程中运行处理过程
        threading.Thread(target=self.run_process, args=(config,), daemon=True).start()

    def run_process(self, config):
        try:
            # 显示进度条
            self.root.after(0, self.progress.grid)
            self.root.after(0, lambda: self.disable_inputs(True))
            
            def progress_callback(current, total):
                progress = (current / total) * 100
                self.root.after(0, lambda: self.progress_var.set(progress))
            
            # 导入主程序
            from main import setup_logging, process_folder
            
            # 设置日志
            setup_logging(config['debug'])
            
            # 处理文件夹
            process_folder(config, progress_callback)
            
            logging.info("处理完成！")
        except Exception as e:
            logging.error(f"处理过程中出错: {str(e)}")
        finally:
            # 隐藏进度条并启用输入
            self.root.after(0, self.progress.grid_remove)
            self.root.after(0, lambda: self.disable_inputs(False))
            self.root.after(0, lambda: self.progress_var.set(0))

    def disable_inputs(self, disabled=True):
        state = 'disabled' if disabled else 'normal'
        self.api_key_entry.configure(state=state)
        self.secret_key_entry.configure(state=state)
        self.input_folder_entry.configure(state=state)
        self.output_folder_entry.configure(state=state)

def main():
    root = tk.Tk()
    app = PDFOrientationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 