import sys
import os
import importlib
from tkinter import Tk
from ui.main_window import MainWindow

import application.http.ui_config_tab
import application.kafka.ui_config_tab
import application.rmq.ui_config_tab

def discover_config_tabs():
    """自动发现并导入所有配置标签页，兼容cx_Freeze打包路径"""
    # 1. 优先用 sys._MEIPASS（PyInstaller），2. 用 sys.executable 目录（cx_Freeze），3. 用 __file__ 目录（源码）
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(base_dir, 'application')
    print(f"[discover_config_tabs] search application dir: {app_path}")
    if not os.path.exists(app_path):
        print(f"Warning: Application directory not found at {app_path}")
        return
    for item in os.listdir(app_path):
        item_path = os.path.join(app_path, item)
        if os.path.isdir(item_path) and not item.startswith('__'):
            if os.path.exists(os.path.join(item_path, 'ui_config_tab.py')):
                module_path = f'application.{item}.ui_config_tab'
                print(f"[discover_config_tabs] Try import: {module_path}")
                try:
                    importlib.import_module(module_path)
                    print(f"[discover_config_tabs] Successfully imported: {module_path}")
                except (ImportError, SyntaxError) as e:
                    print(f"Error: Could not load config tab from {module_path}: {e}")

def main():
    # 发现并加载所有配置标签页
    # discover_config_tabs()

    # 创建主窗口
    root = Tk()
    app = MainWindow(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()