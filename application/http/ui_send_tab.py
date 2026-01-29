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
                "host": "0.0.0.0",
                "port": "8000",
                "url_path": "/httpalarm",
                "body": '{"msg":"hello"}',
                "result": "",
            }
        )

    def create_tab_content(self):
        # 与 HTTPConfigTab 配置区一致，消息体和应答区左右布局
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10)
        # 顶部配置区
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(top_frame, text="监听地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.host_var = tk.StringVar(value=self.config_vars["host"])
        ip_list = [self.config_vars["host"]]
        self.host_combo = ttk.Combobox(top_frame, textvariable=self.host_var, values=ip_list, state="readonly")
        self.host_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(top_frame, text="端口:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.port_entry = ttk.Entry(top_frame, width=8)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.port_entry.insert(0, self.config_vars["port"])
        ttk.Label(top_frame, text="路径:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.path_entry = ttk.Entry(top_frame, width=16)
        self.path_entry.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        self.path_entry.insert(0, self.config_vars["url_path"])
        # 主体左右分割区
        main_paned = PanedWindow(frame, orient=HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)
        # 左侧：消息体
        left_frame = ttk.LabelFrame(main_paned, text="消息体(JSON)")
        self.body_text = tk.Text(left_frame, width=40, height=12)
        self.body_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.body_text.insert(1.0, self.config_vars["body"])
        self.send_btn = ttk.Button(left_frame, text="发送消息", command=self.send_message)
        self.send_btn.pack(anchor="se", padx=5, pady=5)
        main_paned.add(left_frame)
        # 右侧：响应结果
        right_frame = ttk.LabelFrame(main_paned, text="响应结果")
        self.result_text = tk.Text(right_frame, width=40, height=12, state=DISABLED)
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)
        main_paned.add(right_frame)

    def update_status(self, status):
        pass

    def send_message(self):
        host = self.host_var.get()
        port = self.port_entry.get()
        path = self.path_entry.get()
        url = f"http://{host}:{port}{path}"
        body = self.body_text.get(1.0, END).strip()
        try:
            poster = FastHTTPPost(url)
            status, headers, content = poster.post(json_data=json.loads(body))
            result = f"Status: {status}\nHeaders: {headers}\nContent: {content.decode('utf-8', errors='replace')}"
        except Exception as e:
            result = f"Error: {e}"
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, result)
        self.result_text.config(state=DISABLED)


# 注册配置页面
MainWindow.register_config_tab(UITableType.SEND, SendMessageConfigTab)
