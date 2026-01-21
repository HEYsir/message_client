import tkinter as tk
from tkinter import ttk, PanedWindow, Frame, BOTH, LEFT, RIGHT, VERTICAL, HORIZONTAL, END, WORD, X, Y, DISABLED,NORMAL
from tkinter import scrolledtext
from PIL import Image, ImageTk, ImageDraw, ImageFont
from core.message_bus import MessageBus
from typing import Type, Dict, List
from ui.base_tab import BaseConfigTab, CollapsibleNotebook

import xml.dom.minidom
import json
import html
import re
import os

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
        self.root.geometry("1600x800")
        self.message_bus = MessageBus()
        self.config_tab_instances: Dict[str, BaseConfigTab] = {}
        self.image_handler = ImageHandler('./downloads')

        # 初始化自定义样式
        self.init_styles()

        # 存储消息列表
        self.messages = {}  # source -> [messages]
        self.current_message = None
        
        # 图片相关属性
        self.current_image_path = None
        self.image_label = None
        
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
            self.clear_image()

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
        
        # 消息列表
        self.create_message_list(msg_paned)
        
        # 消息详情和图片显示区域
        self.create_message_detail_and_image(msg_paned)
        
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

        # 清空消息详情和图片显示
        self.detail_text.config(state=NORMAL)
        self.detail_text.delete(1.0, END)
        self.detail_text.config(state=DISABLED)
        self.clear_image()
        
    def create_message_detail_and_image(self, parent):
        """创建消息详情和图片显示区域"""
        # 创建水平分割，分为消息详情、图片预览和矩形框列表三部分
        detail_image_paned = PanedWindow(parent, orient=HORIZONTAL)
        parent.add(detail_image_paned)
        
        # 消息详情区域（左侧）
        detail_frame = ttk.LabelFrame(detail_image_paned, text="消息详情")
        detail_image_paned.add(detail_frame, minsize=400)
        
        self.detail_text = scrolledtext.ScrolledText(
            detail_frame,
            wrap=WORD,
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.detail_text.pack(fill=BOTH, expand=True)
        self.detail_text.config(state=DISABLED)
        
        # 图片显示区域（中间）
        image_frame = ttk.LabelFrame(detail_image_paned, text="图片预览")
        detail_image_paned.add(image_frame, minsize=400)
        
        # 图片显示标签
        self.image_label = tk.Label(
            image_frame,
            text="暂无图片",
            font=("Arial", 12),
            bg="white",
            relief="sunken",
            width=40,
            height=20
        )
        self.image_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 图片信息标签
        self.image_info_label = tk.Label(
            image_frame,
            text="",
            font=("Arial", 10),
            fg="gray"
        )
        self.image_info_label.pack(fill=X, padx=10, pady=5)
        
        # 矩形框和标签侧边栏（右侧）
        self.create_rect_sidebar(detail_image_paned)
        
    def create_rect_sidebar(self, parent):
        """创建矩形框和标签侧边栏"""
        sidebar_frame = ttk.LabelFrame(parent, text="检测目标列表")
        parent.add(sidebar_frame, minsize=250)
        
        # 控制按钮区域
        control_frame = ttk.Frame(sidebar_frame)
        control_frame.pack(fill=X, padx=5, pady=5)
        
        # 显示全部按钮
        self.show_all_btn = ttk.Button(
            control_frame, 
            text="显示全部", 
            command=self.show_all_rects
        )
        self.show_all_btn.pack(side=LEFT, padx=2)
        
        # 隐藏全部按钮
        self.hide_all_btn = ttk.Button(
            control_frame, 
            text="隐藏全部", 
            command=self.hide_all_rects
        )
        self.hide_all_btn.pack(side=LEFT, padx=2)
        
        # 矩形框列表
        list_frame = ttk.Frame(sidebar_frame)
        list_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 矩形框列表
        self.rect_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.SINGLE,
            yscrollcommand=scrollbar.set
        )
        self.rect_listbox.pack(fill=BOTH, expand=True)
        scrollbar.config(command=self.rect_listbox.yview)
        
        # 绑定选择事件
        self.rect_listbox.bind('<<ListboxSelect>>', self.on_rect_select)
        
        # 存储当前图片的矩形框信息
        self.current_rects = []
        self.selected_rect_index = None
        self.show_all_rects_flag = False
        
    def update_rect_sidebar(self, image_info):
        """更新矩形框侧边栏"""
        # 清空当前列表
        self.rect_listbox.delete(0, tk.END)
        self.current_rects = []
        
        # 检查是否有矩形框信息
        if 'rectList' in image_info and image_info['rectList']:
            for i, rect_info in enumerate(image_info['rectList']):
                if rect_info['type'] == 'rect':
                    # 提取标记信息
                    marks = rect_info.get('marks', [])
                    mark_text = ""
                    if marks:
                        mark_names = [mark['name'] for mark in marks if mark['value'] == 'true']
                        if mark_names:
                            mark_text = f" - {', '.join(mark_names)}"
                    
                    # 添加到列表
                    rect_text = f"目标 {i+1}{mark_text}"
                    self.rect_listbox.insert(tk.END, rect_text)
                    self.current_rects.append(rect_info)
        
        # 重置选择状态
        self.selected_rect_index = None
        self.show_all_rects_flag = False
        
    def on_rect_select(self, event):
        """矩形框选择事件处理"""
        selection = self.rect_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        self.selected_rect_index = index
        self.show_all_rects_flag = False
        
        # 重新显示图片，只显示选中的矩形框
        if self.current_image_path:
            self.refresh_image_display()
            
    def show_all_rects(self):
        """显示所有矩形框"""
        self.selected_rect_index = None
        self.show_all_rects_flag = True
        
        # 重新显示图片，显示所有矩形框
        if self.current_image_path:
            self.refresh_image_display()
            
    def hide_all_rects(self):
        """隐藏所有矩形框"""
        self.selected_rect_index = None
        self.show_all_rects_flag = False
        
        # 重新显示图片，不显示任何矩形框
        if self.current_image_path:
            self.refresh_image_display()
            
    def refresh_image_display(self):
        """刷新图片显示"""
        # 获取当前消息的图片信息
        if not self.current_message:
            return
            
        parser = ParserRegistry.get_parser(self.current_message["parsed_data"]["event_type"])
        image_info = parser.extract_image_info(self.current_message["parsed_data"])
        
        if image_info and self.current_image_path:
            image_info['filename'] = self.current_image_path
            self.display_image(image_info)
        
    def display_image(self, image_info: dict):
        """显示图片，并根据选择状态绘制矩形框和标记信息"""
        image_path = image_info['filename']
        if not image_path or not os.path.exists(image_path):
            self.clear_image()
            return
            
        try:
            # 加载图片
            image = Image.open(image_path)
            original_width, original_height = image.size
            
            # 调整图片大小以适应显示区域
            max_width = 400
            max_height = 300
            
            # 计算缩放比例
            scale = min(max_width/original_width, max_height/original_height, 1.0)
            
            if scale < 1.0:
                new_size = (int(original_width * scale), int(original_height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 只在第一次显示图片时更新侧边栏，避免重置选择状态
            if not self.current_rects:
                self.update_rect_sidebar(image_info)
            
            # 如果有rectList，根据选择状态绘制矩形框和标记
            if 'rectList' in image_info and image_info['rectList']:
                # 创建可绘制的图像副本
                drawable_image = image.copy()
                draw = ImageDraw.Draw(drawable_image)
                
                # 尝试加载字体，如果失败则使用默认字体
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except:
                    font = ImageFont.load_default()
                
                # 根据选择状态绘制矩形框
                if self.show_all_rects_flag:
                    # 显示所有矩形框
                    for i, rect_info in enumerate(image_info['rectList']):
                        self.draw_rect_with_marks(draw, rect_info, drawable_image, font, i)
                elif self.selected_rect_index is not None:
                    # 只显示选中的矩形框
                    if self.selected_rect_index < len(image_info['rectList']):
                        rect_info = image_info['rectList'][self.selected_rect_index]
                        self.draw_rect_with_marks(draw, rect_info, drawable_image, font, self.selected_rect_index)
                # 默认不显示任何矩形框
                
                # 使用绘制后的图像
                image = drawable_image
            
            # 转换为Tkinter可显示的格式
            photo = ImageTk.PhotoImage(image)
            
            # 更新图片标签
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # 保持引用
            
            # 更新图片信息
            file_size = os.path.getsize(image_path)
            file_size_kb = file_size / 1024
            
            rect_info = ""
            if 'rectList' in image_info and image_info['rectList']:
                rect_count = len(image_info['rectList'])
                display_mode = ""
                if self.show_all_rects_flag:
                    display_mode = " (显示全部)"
                elif self.selected_rect_index is not None:
                    display_mode = f" (显示目标 {self.selected_rect_index + 1})"
                rect_info = f" | 检测到 {rect_count} 个目标{display_mode}"
            
            image_info_text = f"尺寸: {original_width}x{original_height} | 大小: {file_size_kb:.1f}KB{rect_info}"
            self.image_info_label.config(text=image_info_text)
            
            self.current_image_path = image_path
            
        except Exception as e:
            print(f"显示图片失败: {e}")
            self.clear_image()
            
    def draw_rect_with_marks(self, draw, rect_info, image, font, index):
        """绘制单个矩形框及其标记信息"""
        if rect_info['type'] == 'rect':
            rect_data = rect_info['rect']
            marks = rect_info.get('marks', [])
            
            # 将相对坐标转换为绝对坐标
            x1 = int(rect_data['x'] * image.width)
            y1 = int(rect_data['y'] * image.height)
            x2 = int((rect_data['x'] + rect_data['width']) * image.width)
            y2 = int((rect_data['y'] + rect_data['height']) * image.height)
            
            # 绘制矩形框（红色边框）
            draw.rectangle([x1, y1, x2, y2], outline='red', width=2)
            
            # 绘制标记信息
            text_y = y1 - 20 if y1 > 30 else y2 + 5
            for j, mark in enumerate(marks):
                text = f"{mark['name']}: {mark['value']}"
                # 绘制文本背景
                bbox = draw.textbbox((x1, text_y + j*15), text, font=font)
                draw.rectangle(bbox, fill='red')
                # 绘制文本
                draw.text((x1, text_y + j*15), text, fill='white', font=font)
            
    def clear_image(self):
        """清除图片显示"""
        self.image_label.config(image="", text="暂无图片")
        self.image_info_label.config(text="")
        self.current_image_path = None
        
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
        
        # 清除当前图片显示
        self.clear_image()
  
        self.detail_text.insert(END, self.current_message.get("source"))
        self.detail_text.insert(END, f"\n来源IP: {self.current_message.get('ip', 'N/A')}\n")
        
        self.detail_text.insert(END, f"接收时间: {self.current_message['timestamp']}\n")
        self.detail_text.insert(END, "-" * 80 + "\n\n")
        
        # 提取图片信息并下载
        print(self.current_message["parsed_data"]["event_type"])
        parser = ParserRegistry.get_parser(self.current_message["parsed_data"]["event_type"])
        image_info = parser.extract_image_info(self.current_message["parsed_data"])
        if image_info:
            # 显示图片下载信息
            self.detail_text.insert(END, f"检测到图片URL: {image_info['url']}\n")
            self.detail_text.insert(END, f"图片文件名: {image_info['filename']}\n")
            self.detail_text.insert(END, "正在下载图片...\n")
            self.detail_text.insert(END, "-" * 80 + "\n\n")
            
            # 异步下载图片
            self.image_handler.async_download(
                image_info['url'],
                image_info['filename']
            )
            
            # 启动图片检查任务
            self.check_image_download(image_info)
                
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
        
    def check_image_download(self, image_info):
        """检查图片下载状态"""
        print(f"检查图片下载状态: {image_info}")
        try:
            # 构建完整的图片路径
            image_filename = image_info['filename']
            image_path = os.path.join('./downloads', image_filename)
            print(f"图片路径: {image_path}")
            
            if os.path.exists(image_path):
                # 图片已下载完成，显示图片
                print(f"图片已存在，开始显示: {image_path}")
                # 更新image_info中的filename为完整路径
                image_info['filename'] = image_path
                self.display_image(image_info)
                # 更新消息详情显示下载完成
                self.detail_text.config(state=NORMAL)
                self.detail_text.insert(END, f"\n图片下载完成: {image_path}\n")
                self.detail_text.config(state=DISABLED)
            else:
                # 图片还未下载完成，继续检查
                print(f"图片不存在，继续检查: {image_path}")
                self.root.after(500, lambda: self.check_image_download(image_info))
        except Exception as e:
            print(f"检查图片下载状态时出错: {e}")
            print(f"image_info类型: {type(image_info)}, 值: {image_info}")
        
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
            "name": "HTTP消息发送",
            "host": "0.0.0.0",
            "port": "8000",
            "url_path": "/httpalarm",
            "body": '{"msg":"hello"}',
            "result": ""
        })

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
