from tkinter import *
from tkinter import ttk
import tkinter as tk
import json
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow, UITableType
from application.rmq.producer import FastRMQProducer


class SendRMQMessageConfigTab(BaseConfigTab):
    def _init_config_vars(self):
        self.config_vars.update(
            {
                "name": "RabbitMQ消息发送",
                "host": "127.0.0.1",
                "port": 5672,
                "queue": "test",
                "username": "",
                "password": "",
                "body": '{"msg":"hello rmq"}',
                "result": "",
            }
        )

    def create_tab_content(self):
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10)
        ttk.Label(frame, text="主机地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.host_entry = ttk.Entry(frame, width=24)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.host_entry.insert(0, self.config_vars["host"])
        ttk.Label(frame, text="端口:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.port_entry = ttk.Entry(frame, width=8)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.port_entry.insert(0, str(self.config_vars["port"]))
        ttk.Label(frame, text="队列名称:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.queue_entry = ttk.Entry(frame, width=16)
        self.queue_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.queue_entry.insert(0, self.config_vars["queue"])
        ttk.Label(frame, text="用户名:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.user_entry = ttk.Entry(frame, width=16)
        self.user_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.user_entry.insert(0, self.config_vars["username"])
        ttk.Label(frame, text="密码:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.pass_entry = ttk.Entry(frame, width=16, show="*")
        self.pass_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        self.pass_entry.insert(0, self.config_vars["password"])
        # 消息体
        ttk.Label(frame, text="消息体(JSON):").grid(row=2, column=0, sticky="ne", padx=5, pady=5)
        self.body_text = tk.Text(frame, width=60, height=8)
        self.body_text.grid(row=2, column=1, columnspan=5, padx=5, pady=5, sticky="ew")
        self.body_text.insert(1.0, self.config_vars["body"])
        # 发送按钮
        self.send_btn = ttk.Button(frame, text="发送消息", command=self.send_message)
        self.send_btn.grid(row=3, column=5, sticky="e", pady=10)
        # 响应结果
        ttk.Label(frame, text="响应结果:").grid(row=4, column=0, sticky="ne", padx=5, pady=5)
        self.result_text = tk.Text(frame, width=60, height=8, state=DISABLED)
        self.result_text.grid(row=4, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

    def update_status(self, status):
        pass

    def send_message(self):
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        queue = self.queue_entry.get()
        username = self.user_entry.get() or None
        password = self.pass_entry.get() or None
        body = self.body_text.get(1.0, END).strip()
        try:
            producer = FastRMQProducer(host, port=port, username=username, password=password)
            producer.send(queue, message=json.loads(body))
            producer.close()
            result = "Message sent to RabbitMQ."
        except Exception as e:
            result = f"Error: {e}"
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, result)
        self.result_text.config(state=DISABLED)


# 注册配置页面
MainWindow.register_config_tab(UITableType.SEND, SendRMQMessageConfigTab)
