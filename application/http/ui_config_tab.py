from tkinter import *
from tkinter import ttk
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow
import pyperclip
from tkinter import messagebox
from application.http.service import HTTPServer


class HTTPConfigTab(BaseConfigTab):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server = None  # 用于管理 HTTPServer 实例

    @classmethod
    def get_tab_name(cls) -> str:
        return "HTTP 服务"

    def _init_config_vars(self):
        """初始化配置变量"""
        super()._init_config_vars()
        self.config_vars.update({
            "host": StringVar(value="127.0.0.1"),
            "port": StringVar(value="8000"),
            "status": StringVar(value="已停止"),
            "name": StringVar(value="HTTP服务")
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
        self.host_entry = ttk.Entry(frame, textvariable=self.config_vars["host"])
        self.host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.host_entry.bind("<KeyRelease>", self.update_url)

        # 端口
        ttk.Label(frame, text="端口:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.port_entry = ttk.Entry(frame, textvariable=self.config_vars["port"], width=8)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.port_entry.bind("<KeyRelease>", self.update_url)

        # 启动按钮
        self.start_btn = ttk.Button(frame, text="启动服务", command=self._toggle_service)
        self.start_btn.grid(row=0, column=4, columnspan=2, padx=10, pady=5)

        # URL显示区域
        url_frame = Frame(frame)
        url_frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=5, pady=(0, 5))

        ttk.Label(url_frame, text="服务地址:").pack(side=LEFT, padx=(0, 5))

        self.url_label = ttk.Label(
            url_frame,
            text="",
            font=("Arial", 10, "bold"),
            foreground="blue",
            padding=(5, 0),
            cursor="hand2"
        )
        self.url_label.pack(side=LEFT, fill=X, expand=True)
        self.url_label.bind("<Button-1>", self.copy_url_to_clipboard)

        # 更新URL显示
        self.update_url()

    def update_url(self, event=None):
        """更新HTTP服务URL显示"""
        self.server_url = f"http://{self.config_vars['host'].get()}:{self.config_vars['port'].get()}/httpalarm"
        self.url_label.config(text=self.server_url)

    def copy_url_to_clipboard(self, event=None):
        """复制URL到剪贴板"""
        try:
            pyperclip.copy(self.server_url)
            self.url_label.config(foreground="green")
            self.frame.after(1000, lambda: self.url_label.config(foreground="blue"))
        except Exception as e:
            messagebox.showerror("复制失败", f"无法复制到剪贴板: {str(e)}")

    def _toggle_service(self):
        """切换服务状态"""
        if self.config_vars["status"].get() == "运行中":
            self.stop_service()
            # 启用 host 和 port 输入框
            self.host_entry.config(state="normal")
            self.port_entry.config(state="normal")
        else:
            self.start_service()
            # 禁用 host 和 port 输入框
            self.host_entry.config(state="disabled")
            self.port_entry.config(state="disabled")

    def start_service(self):
        """启动HTTP服务"""
        try:
            config = {
                "host": self.config_vars["host"].get(),
                "port": int(self.config_vars["port"].get()),
                "name": self.config_vars["name"].get()
            }
            self.server = HTTPServer(config)
            self.server.start()
            self.config_vars["status"].set("运行中")
            self.start_btn.config(text="停止服务")
        except Exception as e:
            messagebox.showerror("启动失败", f"无法启动服务: {str(e)}")

    def stop_service(self):
        """停止HTTP服务"""
        if self.server:
            self.server.stop()
            self.server.join()
            self.server = None
        self.config_vars["status"].set("已停止")
        self.start_btn.config(text="启动服务")

    def update_status(self, status: str):
        """更新服务状态"""
        self.config_vars["status"].set(status)


# 注册配置页面
MainWindow.register_config_tab(HTTPConfigTab)