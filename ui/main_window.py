import tkinter as tk
from tkinter import ttk, PanedWindow, Frame, BOTH, LEFT, RIGHT, VERTICAL, HORIZONTAL, END, WORD, X, Y
from tkinter import scrolledtext
from core.message_bus import MessageBus
from typing import Type, Dict, List
from ui.base_tab import BaseConfigTab, CollapsibleNotebook

import tkinter as tk
from tkinter import ttk, StringVar
from abc import ABC, abstractmethod


class MainWindow:
    # 用于存储已注册的配置页面类
    _config_tabs: Dict[str, Type[BaseConfigTab]] = {}
    
    @classmethod
    def register_config_tab(cls, tab_class: Type[BaseConfigTab]):
        """注册配置标签页"""
        cls._config_tabs[tab_class.get_tab_name()] = tab_class
    
    def __init__(self, root):
        self.root = root
        self.root.title("报警服务监控工具")
        self.root.geometry("1200x800")
        self.message_bus = MessageBus()
        self.config_tab_instances: Dict[str, BaseConfigTab] = {}

        # 初始化自定义样式
        self.init_styles()

        # 存储消息列表
        self.messages = {}  # source -> [messages]
        self.current_message = None
        
        # 初始化UI
        self.create_ui()
        
        # 订阅消息
        self.message_bus.subscribe("message.received", self.on_message_received)
        self.message_bus.subscribe("message.status", self.on_status_received)

        # 启动消息处理
        self.process_messages()

    def init_styles(self):
        pass

    def create_ui(self):
        """创建主UI框架"""
        # 创建主分割面板
        self.main_paned = PanedWindow(self.root, orient=VERTICAL)
        self.main_paned.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 创建服务配置区
        self.create_service_area()
        
        # 创建消息区域
        self.create_message_area()
        
    def create_service_area(self):
        """创建服务配置区域"""
        # 创建标签页容器
        self.tab_container = CollapsibleNotebook(self.main_paned)
        self.tab_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_paned.add(self.tab_container)

        # 加载所有已注册的配置页面
        for tab_name, tab_class in self._config_tabs.items():
            ui_tab_instance = self.tab_container.add_tab(tab_class)
            self.config_tab_instances[tab_name] = ui_tab_instance
  
    def create_message_area(self):
        """创建消息显示区域"""
        message_frame = Frame(self.main_paned)
        self.main_paned.add(message_frame)
        
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
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.ui_msg_tree.yview)
        self.ui_msg_tree.configure(yscroll=scrollbar.set)
        
        self.ui_msg_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 绑定选择事件
        self.ui_msg_tree.bind("<<TreeviewSelect>>", self.on_message_select)
        
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
        self.detail_text.config(state="disabled")
        
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
        self.detail_text.config(state="normal")
        self.detail_text.delete(1.0, END)
        
        # 显示消息内容
        # todo:这里实现
        self.detail_text.config(state="disabled")
        
    def on_message_received(self, message):
        """处理接收到的消息"""
        source = message["source"]
        if source not in self.messages:
            self.messages[source] = []
            
        self.messages[source].append(message)
        self.add_message_to_tree(message)
        
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
        tab_instance = self.config_tab_instances.get(source)
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
