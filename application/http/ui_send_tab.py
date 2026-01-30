from tkinter import *
from tkinter import ttk
import tkinter as tk
import json
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow, UITableType
from application.http.send import FastHTTPPost


class SendMessageConfigTab(BaseConfigTab):
    def _init_config_vars(self):
        self.config_vars.update(
            {
                "name": "HTTP消息发送",
                "method": "POST",
                "protocol": "http",
                "host": "localhost",
                "port": "80",
                "url_path": "/httpalarm",
                "body": '{"msg":"hello"}',
                "result": "",
            }
        )

    def create_tab_content(self):
        # POSTMAN风格的布局
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10, expand=True)

        # 顶部请求行（类似POSTMAN）
        request_frame = ttk.LabelFrame(frame, text="请求")
        request_frame.pack(fill="x", padx=5, pady=5)

        # 请求方法选择
        self.method_var = tk.StringVar(value=self.config_vars["method"])
        method_combo = ttk.Combobox(
            request_frame,
            textvariable=self.method_var,
            values=["GET", "POST", "PUT", "DELETE"],
            state="readonly",
            width=8,
        )
        method_combo.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        # 完整的URL输入框（协议://主机地址:端口/URI）
        url_frame = ttk.Frame(request_frame)
        url_frame.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        # 协议选择
        self.protocol_var = tk.StringVar(value=self.config_vars["protocol"])
        protocol_combo = ttk.Combobox(
            url_frame, textvariable=self.protocol_var, values=["http", "https"], state="readonly", width=4
        )
        protocol_combo.pack(side="left", padx=(0, 0))

        # 协议分隔符（固定显示 ://）
        protocol_label = ttk.Label(url_frame, text="://")
        protocol_label.pack(side="left", padx=(0, 0))

        # 主机地址
        self.host_var = tk.StringVar(value=self.config_vars["host"])
        self.host_entry = ttk.Entry(url_frame, textvariable=self.host_var, width=15)
        self.host_entry.pack(side="left", padx=(0, 0))

        self.path_var = tk.StringVar(value=self.config_vars["url_path"])
        self.path_entry = ttk.Entry(url_frame, textvariable=self.path_var, width=100)
        # self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 0))
        self.path_entry.pack(side="left", padx=(0, 0))

        # 发送按钮
        self.send_btn = ttk.Button(request_frame, text="发送", command=self.send_message, width=8)
        self.send_btn.grid(row=0, column=2, padx=(5, 10), pady=10, sticky="e")

        # 配置列权重使URL输入框可以扩展
        request_frame.columnconfigure(1, weight=1)
        # 主体左右分割区
        main_paned = PanedWindow(frame, orient=HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)

        # 左侧：请求体
        left_frame = ttk.LabelFrame(main_paned, text="请求体")
        self.body_text = tk.Text(left_frame, width=40, height=12)
        self.body_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.body_text.insert(1.0, self.config_vars["body"])
        main_paned.add(left_frame)

        # 右侧：响应结果
        right_frame = ttk.LabelFrame(main_paned, text="响应")
        self.result_text = tk.Text(right_frame, width=40, height=12, state=DISABLED)
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)
        main_paned.add(right_frame)

    def update_status(self, status):
        pass

    def send_message(self):
        method = self.method_var.get()
        protocol = self.protocol_var.get()
        host = self.host_var.get().strip()
        path = self.path_var.get().strip()

        # 构建URL（智能处理端口）
        url = f"{protocol}://{host}{path}"
        body = self.body_text.get(1.0, END).strip()
        try:
            poster = FastHTTPPost(url)
            # 根据请求方法选择不同的发送方式
            if method == "GET":
                status, headers, content = poster.get()
            elif method == "POST":
                status, headers, content = poster.post(json_data=json.loads(body) if body else None)
            elif method == "PUT":
                status, headers, content = poster.put(json_data=json.loads(body) if body else None)
            elif method == "DELETE":
                status, headers, content = poster.delete()
            else:
                status, headers, content = poster.post(json_data=json.loads(body) if body else None)

            result = f"方法: {method}\nURL: {url}\n状态码: {status}\n响应头: {headers}\n响应体: {content.decode('utf-8', errors='replace')}"
        except Exception as e:
            result = f"方法: {method}\nURL: {url}\n错误: {e}"
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, result)
        self.result_text.config(state=DISABLED)


# 注册配置页面
MainWindow.register_config_tab(UITableType.SEND, SendMessageConfigTab)
