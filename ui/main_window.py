import tkinter as tk
from tkinter import ttk, PanedWindow, Frame, BOTH, LEFT, RIGHT, VERTICAL, HORIZONTAL, END, WORD, X, Y, DISABLED,NORMAL
from tkinter import scrolledtext
from core.message_bus import MessageBus
from typing import Type, Dict, List
from ui.base_tab import BaseConfigTab, CollapsibleNotebook

import xml.dom.minidom
import json
import html
import re

from core.protocol_parser import ParserRegistry
from core.image_handler import ImageHandler
from application.http.send import FastHTTPPost
from application.kafka.producer import FastKafkaProducer
from application.rmq.producer import FastRMQProducer


class MainWindow:
    # 用于存储已注册的配置页面类
    _config_tabs: List[Type[BaseConfigTab]] = []
    
    @classmethod
    def register_config_tab(cls, tab_class: Type[BaseConfigTab]):
        """注册配置标签页"""
        cls._config_tabs.append(tab_class)
    
    def __init__(self, root):
        self.root = root
        self.root.title("报警服务监控工具")
        self.root.geometry("1200x800")
        self.message_bus = MessageBus()
        self.config_tab_instances: Dict[str, BaseConfigTab] = {}
        # self.image_handler = ImageHandler('./downloads')

        # 初始化自定义样式
        self.init_styles()

        # 存储消息列表
        self.messages = {}  # source -> [messages]
        self.current_message = None
        
        # 初始化UI
        self.create_ui()
        
        # 订阅消息
        self.message_bus.subscribe("message.received", self.on_message_received)
        self.message_bus.subscribe("service.status", self.on_status_received)

        # 启动消息处理

        self.process_messages()
    def init_styles(self):
        pass

    def create_sidebar(self, sidebar_frame):
        """创建侧边栏"""
        # 消费监听按钮
        consume_button = ttk.Button(sidebar_frame, text="消费监听", command=self.on_consume_listen)
        consume_button.pack(fill=X, padx=5, pady=5)

        # 报文发送按钮
        send_button = ttk.Button(sidebar_frame, text="报文发送", command=self.on_message_send)
        send_button.pack(fill=X, padx=5, pady=5)

    def on_clear_service_messages(self):
        """清除当前选项卡服务的消息"""
        selected_tab = self.tab_container.get_selected_tab()
        if not selected_tab:
            print("未选择任何服务")
            return

        confirm = tk.messagebox.askyesno("确认清除", f"是否清除当前服务[{selected_tab}]的消息？")
        if confirm:
            self.messages[selected_tab] = []
            self.ui_msg_tree.delete(*self.ui_msg_tree.get_children())
            self.detail_text.config(state=NORMAL)
            self.detail_text.delete(1.0, END)
            self.detail_text.config(state=DISABLED)

    def on_consume_listen(self):
        """切换到消费监听页面"""
        self.recived_paned.pack(fill=BOTH, expand=True, padx=5, pady=5)
        # 隐藏报文发送页面
        self.message_send_frame.pack_forget()

    def on_message_send(self):
        """切换到报文发送页面"""
        self.recived_paned.pack_forget()  # 隐藏消息显示区域
        # 显示报文发送页面
        self.message_send_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

    def create_ui(self):
        """创建主UI框架"""
        # 创建侧边栏
        sidebar_frame = Frame(self.root, width=150, bg="lightgray")
        sidebar_frame.pack(side=LEFT, fill=Y)
        self.create_sidebar(sidebar_frame)

        # 创建消费监听区域
        self.recived_paned = PanedWindow(self.root, orient=VERTICAL)
        self.recived_paned.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self.create_service_area(self.recived_paned)
        self.create_message_area(self.recived_paned)

        # 创建报文发送页面
        self.message_send_frame = Frame(self.root)
        self.message_send_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self.create_message_send_area(self.message_send_frame)
        self.message_send_frame.pack_forget()  # 默认隐藏

    def create_message_send_area(self, message_send_frame):
        """创建报文发送页面，增加配置tab"""
        from ui.base_tab import CollapsibleNotebook
        self.send_tab_container = CollapsibleNotebook(message_send_frame)
        self.send_tab_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.send_tab_container.add_tab(SendMessageConfigTab)
        self.send_tab_container.add_tab(SendKafkaMessageConfigTab)
        self.send_tab_container.add_tab(SendRMQMessageConfigTab)

    def create_service_area(self, main_paned):
        """创建服务配置区域"""
        # 创建标签页容器
        self.tab_container = CollapsibleNotebook(main_paned)
        self.tab_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_paned.add(self.tab_container)

        # 加载所有已注册的配置页面
        for tab_class in self._config_tabs:
            self.tab_container.add_tab(tab_class)
        # 消息列表监听标签页变化
        self.tab_container.register_tab_change_callback(self.on_service_tab_changed)
  
    def create_message_area(self, recived_paned):
        """创建消息显示区域"""
        message_frame = Frame(recived_paned)
        recived_paned.add(message_frame)

        # 创建水平分割
        msg_paned = PanedWindow(message_frame, orient=HORIZONTAL)
        msg_paned.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # # 消息列表
        self.create_message_list(msg_paned)
        
        # # 消息详情
        self.create_message_detail(msg_paned)
        
    def create_message_list(self, parent):
        """创建消息列表"""
        list_frame = ttk.LabelFrame(parent, text="消息列表")
        parent.add(list_frame)
        
        # 消息列表树形视图
        columns = ("time", "source", "config", "type", "topic")
        self.ui_msg_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        # 设置列
        self.setup_tree_columns()
        
        # 清除服务消息按钮放在消息列表下方
        clear_button = ttk.Button(list_frame, text="清除服务消息", command=self.on_clear_service_messages)
        clear_button.pack(fill=X, padx=5, pady=5, side='bottom')

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.ui_msg_tree.yview)
        self.ui_msg_tree.configure(yscroll=scrollbar.set)
        
        self.ui_msg_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 绑定选择事件
        self.ui_msg_tree.bind("<<TreeviewSelect>>", self.on_message_select)

    def on_service_tab_changed(self, selected_tab):
        """服务切换事件处理"""
        # 清空消息列表
        self.ui_msg_tree.delete(*self.ui_msg_tree.get_children())

        # 添加当前服务的消息
        if selected_tab in self.messages:
            for message in self.messages[selected_tab]:
                self.add_message_to_tree(message)

        # 清空消息详情
        self.detail_text.config(state=NORMAL)
        self.detail_text.delete(1.0, END)
        self.detail_text.config(state=DISABLED)
        
    def create_message_detail(self, parent):
        """创建消息详情区域"""
        detail_frame = ttk.LabelFrame(parent, text="消息详情")
        parent.add(detail_frame)
        
        self.detail_text = scrolledtext.ScrolledText(
            detail_frame,
            wrap=WORD,
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.detail_text.pack(fill=BOTH, expand=True)
        self.detail_text.config(state=DISABLED)
        
    def setup_tree_columns(self):
        """设置树形视图列"""
        columns = {
            "time": ("接收时间", 150),
            "source": ("来源", 80),
            "config": ("配置名称", 150),
            "type": ("事件类型", 120),
            "topic": ("主题/队列", 150)
        }
        
        for col, (text, width) in columns.items():
            self.ui_msg_tree.heading(col, text=text)
            self.ui_msg_tree.column(col, width=width)
            
    def on_message_select(self, event):
        """消息选择事件处理"""
        selection = self.ui_msg_tree.selection()
        if not selection:
            print("没有选中任何消息")
            return
            
        item = self.ui_msg_tree.item(selection[0])
        source = item["values"][1]
        timestamp = item["values"][0]
        
        # 查找对应消息
        if source in self.messages:
            for msg in self.messages[source]:
                if msg["timestamp"] == timestamp:
                    self.display_message(msg)
                    break
                    
    def display_message(self, message):
        """显示消息详情"""
        self.current_message = message
        self.detail_text.config(state=NORMAL)
        self.detail_text.delete(1.0, END)
        
  
        self.detail_text.insert(END, self.current_message.get("source"))
        self.detail_text.insert(END, f"\n来源IP: {self.current_message.get('ip', 'N/A')}\n")
        
        self.detail_text.insert(END, f"接收时间: {self.current_message['timestamp']}\n")
        self.detail_text.insert(END, "-" * 80 + "\n\n")
        
        # 提取图片信息
        # image_info = parser.extract_image_info(parsed_data)
        # if image_info:
        #     self.image_handler.async_download(
        #         image_info['url'],
        #         image_info['filename']
        #     )
                
        parsed_data = self.current_message["parsed_data"]
        
        if parsed_data.get("type") == "XML":
            try:
                parsed = xml.dom.minidom.parseString(self.current_message["raw_data"])
                xml_str = parsed.toprettyxml(indent="  ")
                xml_str = re.sub(r'\n\s*\n', '\n', xml_str)
                self.detail_text.insert(END, xml_str)
            except:
                raw_str = html.unescape(self.current_message["raw_data"].decode("utf-8", errors="replace"))
                self.detail_text.insert(END, raw_str)
        elif parsed_data.get("type") == "JSON":
            try:
                raw_str = html.unescape(self.current_message["raw_data"].decode("utf-8", errors="replace"))
                json_data = json.loads(raw_str)
                formatted = json.dumps(json_data, indent=2, ensure_ascii=False)
                self.detail_text.insert(END, formatted)
            except:
                raw_str = html.unescape(self.current_message["raw_data"].decode("utf-8", errors="replace"))
                self.detail_text.insert(END, raw_str)
        else:
            raw_str = html.unescape(self.current_message["raw_data"].decode("utf-8", errors="replace"))
            self.detail_text.insert(END, raw_str)
            
        self.detail_text.config(state=DISABLED)
        
    def on_message_received(self, message):
        """处理接收到的消息"""
        source = message["source"]
        if source not in self.messages:
            self.messages[source] = []

        # 获取对应的解析器
        parser = ParserRegistry.get_parser('basealarm')
        post_data = message.get("raw_data", b"")
        parsed_data = parser.parse(message['content_type'], post_data)
        message["parsed_data"] = parsed_data

        self.messages[source].append(message)
        self.add_message_to_tree(message)
        # 如果当前选中消息是新消息，自动显示详情
        if self.current_message and self.current_message["timestamp"] == message["timestamp"] and self.current_message["source"] == source:
            self.display_message(message)
        # 如果当前没有选中消息，自动显示最新消息
        elif not self.current_message:
            self.display_message(message)
        # 如果当前消息列表为空，自动显示最新消息
        elif not self.ui_msg_tree.get_children():
            self.display_message(message)

        # 更新服务状态
        if message.get("type") == "status":
            self.on_status_received(message)
        
    def add_message_to_tree(self, message):
        """添加消息到列表"""

        self.ui_msg_tree.insert("", "end", values=(
            message["timestamp"],
            message["source"],
            message.get("config_name", ""),
            message["parsed_data"].get("event_type", "N/A"),
            message.get("queue", message.get("topic", ""))
        ))

    def on_status_received(self, message):
        """更新服务状态"""
        source = message["source"]
        status = message.get("status", "未知状态")
        
        # 更新对应的标签页状态
        tab_instance = self.tab_container.tabs.get(source)
        if not tab_instance:
            return
        if hasattr(tab_instance, "update_status"):
            tab_instance.update_status(status)
        
    def process_messages(self):
        """处理消息队列"""
        self.message_bus.process_messages()
        self.root.after(100, self.process_messages)
        
    def cleanup(self):
        """清理资源"""
        # 停止所有服务线程
        for tab in self.config_tab_instances.values():
            if hasattr(tab, "stop_service"):
                tab.stop_service()

class SendMessageConfigTab(BaseConfigTab):
    def _init_config_vars(self):
        self.config_vars.update({
            "name": "发送消息",
            "url": "http://127.0.0.1:8000/",
            "body": "{\"msg\":\"hello\"}",
            "result": ""
        })

    def create_tab_content(self):
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10)
        ttk.Label(frame, text="目标URL:").grid(row=0, column=0, sticky="e")
        self.url_entry = ttk.Entry(frame, width=40)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.url_entry.insert(0, self.config_vars["url"])
        ttk.Label(frame, text="消息体(JSON):").grid(row=1, column=0, sticky="ne")
        self.body_text = tk.Text(frame, width=60, height=8)
        self.body_text.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.body_text.insert(1.0, self.config_vars["body"])
        self.send_btn = ttk.Button(frame, text="发送消息", command=self.send_message)
        self.send_btn.grid(row=2, column=1, sticky="e", pady=10)
        ttk.Label(frame, text="响应结果:").grid(row=3, column=0, sticky="ne")
        self.result_text = tk.Text(frame, width=60, height=8, state=DISABLED)
        self.result_text.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

    def update_status(self, status):
        pass

    def send_message(self):
        url = self.url_entry.get()
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

class SendKafkaMessageConfigTab(BaseConfigTab):
    def _init_config_vars(self):
        self.config_vars.update({
            "name": "Kafka消息发送",
            "bootstrap_servers": "127.0.0.1:9092",
            "topic": "STATIC_HUMAN_EXCEPTION_TOPIC",
            "key": "",
            "body": '{"msg":"hello kafka"}',
            "result": ""
        })

    def create_tab_content(self):
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10)
        ttk.Label(frame, text="Bootstrap Servers:").grid(row=0, column=0, sticky="e")
        self.servers_entry = ttk.Entry(frame, width=40)
        self.servers_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.servers_entry.insert(0, self.config_vars["bootstrap_servers"])
        ttk.Label(frame, text="Topic:").grid(row=1, column=0, sticky="e")
        self.topic_entry = ttk.Entry(frame, width=40)
        self.topic_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.topic_entry.insert(0, self.config_vars["topic"])
        ttk.Label(frame, text="Key(Optional):").grid(row=2, column=0, sticky="e")
        self.key_entry = ttk.Entry(frame, width=40)
        self.key_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.key_entry.insert(0, self.config_vars["key"])
        ttk.Label(frame, text="消息体(JSON):").grid(row=3, column=0, sticky="ne")
        self.body_text = tk.Text(frame, width=60, height=8)
        self.body_text.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.body_text.insert(1.0, self.config_vars["body"])
        self.send_btn = ttk.Button(frame, text="发送消息", command=self.send_message)
        self.send_btn.grid(row=4, column=1, sticky="e", pady=10)
        ttk.Label(frame, text="响应结果:").grid(row=5, column=0, sticky="ne")
        self.result_text = tk.Text(frame, width=60, height=8, state=DISABLED)
        self.result_text.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

    def update_status(self, status):
        pass

    def send_message(self):
        servers = self.servers_entry.get()
        topic = self.topic_entry.get()
        key = self.key_entry.get() or None
        body = self.body_text.get(1.0, END).strip()
        try:
            producer = FastKafkaProducer(servers)
            producer.send(topic, value=json.loads(body), key=key, on_delivery=FastKafkaProducer.default_delivery_report)
            producer.flush()
            result = "Message sent to Kafka."
        except Exception as e:
            result = f"Error: {e}"
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, result)
        self.result_text.config(state=DISABLED)

class SendRMQMessageConfigTab(BaseConfigTab):
    def _init_config_vars(self):
        self.config_vars.update({
            "name": "RabbitMQ消息发送",
            "host": "127.0.0.1",
            "port": 5672,
            "queue": "test",
            "username": "",
            "password": "",
            "body": '{"msg":"hello rmq"}',
            "result": ""
        })

    def create_tab_content(self):
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10)
        ttk.Label(frame, text="Host:").grid(row=0, column=0, sticky="e")
        self.host_entry = ttk.Entry(frame, width=30)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.host_entry.insert(0, self.config_vars["host"])
        ttk.Label(frame, text="Port:").grid(row=1, column=0, sticky="e")
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.port_entry.insert(0, str(self.config_vars["port"]))
        ttk.Label(frame, text="Queue:").grid(row=2, column=0, sticky="e")
        self.queue_entry = ttk.Entry(frame, width=30)
        self.queue_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.queue_entry.insert(0, self.config_vars["queue"])
        ttk.Label(frame, text="Username:").grid(row=3, column=0, sticky="e")
        self.user_entry = ttk.Entry(frame, width=20)
        self.user_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        self.user_entry.insert(0, self.config_vars["username"])
        ttk.Label(frame, text="Password:").grid(row=4, column=0, sticky="e")
        self.pass_entry = ttk.Entry(frame, width=20, show="*")
        self.pass_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        self.pass_entry.insert(0, self.config_vars["password"])
        ttk.Label(frame, text="消息体(JSON):").grid(row=5, column=0, sticky="ne")
        self.body_text = tk.Text(frame, width=60, height=8)
        self.body_text.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.body_text.insert(1.0, self.config_vars["body"])
        self.send_btn = ttk.Button(frame, text="发送消息", command=self.send_message)
        self.send_btn.grid(row=6, column=1, sticky="e", pady=10)
        ttk.Label(frame, text="响应结果:").grid(row=7, column=0, sticky="ne")
        self.result_text = tk.Text(frame, width=60, height=8, state=DISABLED)
        self.result_text.grid(row=7, column=1, padx=5, pady=5, sticky="ew")

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
