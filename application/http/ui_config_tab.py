from tkinter import *
from tkinter import ttk
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow

class HTTPConfigTab(BaseConfigTab):
    @classmethod
    def get_tab_name(cls) -> str:
        return "HTTP 服务"
    
    def _init_config_vars(self):
        """初始化配置变量"""
        super()._init_config_vars()
        self.config_vars.update({
            "host": StringVar(),
            "port": StringVar(value="8000")
        })
    
    def create_tab_content(self):
        """创建HTTP服务配置界面"""
        # 主框架
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        frame = ttk.Frame(main_frame)
        frame.pack(fill="x", pady=5)

        # 监听地址
        ttk.Label(frame, text="监听地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        host_entry = ttk.Entry(frame, textvariable=self.config_vars["host"])
        host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # 端口
        ttk.Label(frame, text="端口:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        port_entry = ttk.Entry(frame, textvariable=self.config_vars["port"], width=8)
        port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # 启动按钮
        self.start_btn = ttk.Button(frame, text="启动服务", command=self._toggle_service)
        self.start_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
    
    def _toggle_service(self):
        """切换服务状态"""
        if self.config_vars["status"].get() == "运行中":
            self.config_vars["status"].set("已停止")
            self.start_btn.config(text="启动服务")
        else:
            self.config_vars["status"].set("运行中")
            self.start_btn.config(text="停止服务")
    
    def update_status(self, status: str):
        """更新服务状态"""
        self.config_vars["status"].set(status)

# 注册配置页面
MainWindow.register_config_tab(HTTPConfigTab)