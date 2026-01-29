from tkinter import *
from tkinter import ttk
import tkinter as tk
import json
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow, UITableType
from application.kafka.producer import FastKafkaProducer


class SendKafkaMessageConfigTab(BaseConfigTab):
    def _init_config_vars(self):
        self.config_vars.update(
            {
                "name": "Kafka消息发送",
                "bootstrap_servers": "127.0.0.1:9092",
                "topic": "STATIC_HUMAN_EXCEPTION_TOPIC",
                "key": "",
                "body": '{"msg":"hello kafka"}',
                "result": "",
            }
        )

    def create_tab_content(self):
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10)
        ttk.Label(frame, text="服务地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.servers_entry = ttk.Entry(frame, width=40)
        self.servers_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.servers_entry.insert(0, self.config_vars["bootstrap_servers"])
        ttk.Label(frame, text="主题:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.topic_entry = ttk.Entry(frame, width=24)
        self.topic_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.topic_entry.insert(0, self.config_vars["topic"])
        ttk.Label(frame, text="Key(Optional):").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.key_entry = ttk.Entry(frame, width=16)
        self.key_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.key_entry.insert(0, self.config_vars["key"])
        # 消息体
        ttk.Label(frame, text="消息体(JSON):").grid(row=1, column=0, sticky="ne", padx=5, pady=5)
        self.body_text = tk.Text(frame, width=60, height=8)
        self.body_text.grid(row=1, column=1, columnspan=5, padx=5, pady=5, sticky="ew")
        self.body_text.insert(1.0, self.config_vars["body"])
        # 发送按钮
        self.send_btn = ttk.Button(frame, text="发送消息", command=self.send_message)
        self.send_btn.grid(row=2, column=5, sticky="e", pady=10)
        # 响应结果
        ttk.Label(frame, text="响应结果:").grid(row=3, column=0, sticky="ne", padx=5, pady=5)
        self.result_text = tk.Text(frame, width=60, height=8, state=DISABLED)
        self.result_text.grid(row=3, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

    def update_status(self, status):
        pass

    def send_message(self):
        servers = self.servers_entry.get()
        topic = self.topic_entry.get()
        key = self.key_entry.get() or None
        body = self.body_text.get(1.0, END).strip()
        try:
            producer = FastKafkaProducer(servers)
            producer.send(
                topic,
                value=json.loads(body),
                key=key,
                on_delivery=FastKafkaProducer.default_delivery_report,
            )
            producer.flush()
            result = "Message sent to Kafka."
        except Exception as e:
            result = f"Error: {e}"
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, result)
        self.result_text.config(state=DISABLED)


# 注册配置页面
MainWindow.register_config_tab(UITableType.SEND, SendKafkaMessageConfigTab)
