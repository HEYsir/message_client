from tkinter import *
from tkinter import ttk
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow

class KafkaConfigTab(BaseConfigTab):
    @classmethod
    def get_tab_name(cls) -> str:
        return "Kafka 消费"
    
    def _init_config_vars(self):
        """初始化配置变量"""
        super()._init_config_vars()
        self.config_vars.update({
            "bootstrap_servers": StringVar(),
            "topics": StringVar(),
            "group_id": StringVar()
        })
    
    def create_tab_content(self):
        """创建Kafka服务配置界面"""
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        # 服务地址
        ttk.Label(frame, text="服务地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        servers_entry = ttk.Entry(frame, textvariable=self.config_vars["bootstrap_servers"])
        servers_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # 主题
        ttk.Label(frame, text="主题:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        topics_entry = ttk.Entry(frame, textvariable=self.config_vars["topics"])
        topics_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # 消费组ID
        ttk.Label(frame, text="消费组ID:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        group_entry = ttk.Entry(frame, textvariable=self.config_vars["group_id"])
        group_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # 启动按钮
        self.start_btn = ttk.Button(frame, text="启动服务", command=self._toggle_service)
        self.start_btn.grid(row=1, column=4, padx=10, pady=5)
    
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
MainWindow.register_config_tab(KafkaConfigTab)
