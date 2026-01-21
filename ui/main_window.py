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
import uuid
from datetime import datetime

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
        
        # UUID消息索引管理
        self.message_uuid_map = {}  # uuid -> message
        self.uuid_counter = {}  # source -> counter (用于图片顺序编号)
        
        # 图片下载缓存，按消息UUID和图片序号存储
        self.image_cache = {}  # (message_uuid, image_index) -> image_path
        
        # 图片相关属性
        self.current_image_path = None
        
        # 初始化UI
        self.create_ui()
        
        # 订阅消息
        self.message_bus.subscribe("message.received", self.on_message_received)
        self.message_bus.subscribe("service.status", self.on_status_received)

        # 注册窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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
        """清除当前选项卡服务的消息，包括缓存和图片文件"""
        selected_tab = self.tab_container.get_selected_tab()
        if not selected_tab:
            print("未选择任何服务")
            return

        confirm = tk.messagebox.askyesno("确认清除", f"是否清除当前服务[{selected_tab}]的消息以及对应的图片文件？")
        if confirm:
            # 删除该服务的所有消息对应的图片文件
            if selected_tab in self.messages:
                deleted_count = 0
                for message in self.messages[selected_tab]:
                    message_uuid = message.get("uuid")
                    if message_uuid:
                        # 删除该消息对应的所有图片文件和缓存
                        deleted_count += self.delete_message_images(message_uuid)
                
                if deleted_count > 0:
                    print(f"已删除 {deleted_count} 个图片文件")
            
            # 清空消息列表和UI显示
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
        self.current_message = None
        
    def create_message_detail_and_image(self, parent):
        """创建消息详情和图片显示区域"""
        # 创建垂直分割，分为消息详情和图片缩略图区域
        detail_image_paned = PanedWindow(parent, orient=VERTICAL)
        parent.add(detail_image_paned)
        
        # 消息详情区域（顶部）
        detail_frame = ttk.LabelFrame(detail_image_paned, text="消息详情")
        detail_image_paned.add(detail_frame, minsize=200)
        
        self.detail_text = scrolledtext.ScrolledText(
            detail_frame,
            wrap=WORD,
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.detail_text.pack(fill=BOTH, expand=True)
        self.detail_text.config(state=DISABLED)
        
        # 图片缩略图区域（底部）
        self.create_thumbnail_area(detail_image_paned)
        
        # 创建图片弹窗
        self.create_image_popup()
        
    def create_thumbnail_area(self, parent):
        """创建图片缩略图区域"""
        thumbnail_frame = ttk.LabelFrame(parent, text="图片预览")
        parent.add(thumbnail_frame, minsize=120)
        
        # 创建一个可以水平滚动的缩略图容器
        thumbnail_canvas = tk.Canvas(thumbnail_frame, height=100)
        scrollbar = ttk.Scrollbar(thumbnail_frame, orient=HORIZONTAL, command=thumbnail_canvas.xview)
        thumbnail_canvas.configure(xscrollcommand=scrollbar.set)
        
        # 缩略图容器
        self.thumbnail_container = tk.Frame(thumbnail_canvas)
        thumbnail_canvas.create_window((0, 0), window=self.thumbnail_container, anchor="nw")
        
        # 布局
        thumbnail_canvas.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # 绑定容器大小变化事件
        self.thumbnail_container.bind("<Configure>", lambda e: thumbnail_canvas.configure(scrollregion=thumbnail_canvas.bbox("all")))
        
        # 存储缩略图标签
        self.thumbnail_labels = []
        
    def create_image_popup(self):
        """创建图片弹窗"""
        # 创建顶层窗口
        self.popup = tk.Toplevel(self.root)
        self.popup.title("图片详情")
        self.popup.geometry("1000x600")
        self.popup.withdraw()  # 初始隐藏
        
        # 创建水平分割布局
        popup_paned = PanedWindow(self.popup, orient=HORIZONTAL)
        popup_paned.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 图片显示区域（左侧）
        popup_image_frame = ttk.LabelFrame(popup_paned, text="图片预览")
        popup_paned.add(popup_image_frame, minsize=600)
        
        # 图片显示标签
        self.popup_image_label = tk.Label(
            popup_image_frame,
            text="暂无图片",
            font=("Arial", 12),
            bg="white",
            relief="sunken"
        )
        self.popup_image_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 图片信息标签
        self.popup_image_info_label = tk.Label(
            popup_image_frame,
            text="",
            font=("Arial", 10),
            fg="gray"
        )
        self.popup_image_info_label.pack(fill=X, padx=10, pady=5)
        
        # 矩形框和标签侧边栏（右侧）
        self.create_rect_sidebar(popup_paned)
        
        # 关闭按钮
        close_button = ttk.Button(self.popup, text="关闭", command=self.close_popup)
        close_button.pack(side=tk.BOTTOM, pady=10)
        
        # 弹窗关闭事件
        self.popup.protocol("WM_DELETE_WINDOW", self.close_popup)
        
    def close_popup(self):
        """关闭弹窗"""
        self.popup.withdraw()
        # 重置选择状态，以便下次打开时显示默认状态
        self.selected_rect_index = None
        self.show_all_rects_flag = False
        
    def show_popup(self, image_info):
        """显示图片弹窗"""
        self.popup.deiconify()
        self.popup.lift()
        self.popup.focus_force()
        
        # 显示图片和矩形框
        self.display_image_in_popup(image_info)
        
    def display_image_in_popup(self, image_info):
        """在弹窗中显示图片"""
        image_path = image_info['filename']
        if not image_path or not os.path.exists(image_path):
            self.popup_image_label.config(image="", text="暂无图片")
            self.popup_image_info_label.config(text="")
            return
            
        try:
            # 加载图片
            image = Image.open(image_path)
            original_width, original_height = image.size
            
            # 调整图片大小以适应弹窗
            max_width = 500
            max_height = 400
            
            # 计算缩放比例
            scale = min(max_width/original_width, max_height/original_height, 1.0)
            
            if scale < 1.0:
                new_size = (int(original_width * scale), int(original_height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 更新矩形框侧边栏
            self.update_rect_sidebar(image_info)
            
            # 如果有rectList，根据选择状态绘制矩形框
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
                        self.draw_rect_in_popup(draw, rect_info, drawable_image, font, i)
                elif self.selected_rect_index is not None:
                    # 只显示选中的矩形框
                    if self.selected_rect_index < len(image_info['rectList']):
                        rect_info = image_info['rectList'][self.selected_rect_index]
                        self.draw_rect_in_popup(draw, rect_info, drawable_image, font, self.selected_rect_index)
                else:
                    # 默认不显示矩形框
                    pass
                
                # 使用绘制后的图像
                image = drawable_image
            
            # 转换为Tkinter可显示的格式
            photo = ImageTk.PhotoImage(image)
            
            # 更新图片标签
            self.popup_image_label.config(image=photo, text="")
            self.popup_image_label.image = photo  # 保持引用
            
            # 更新图片信息
            file_size = os.path.getsize(image_path)
            file_size_kb = file_size / 1024
            
            rect_info = ""
            if 'rectList' in image_info and image_info['rectList']:
                rect_count = len(image_info['rectList'])
                rect_info = f" | 检测到 {rect_count} 个目标"
            
            image_info_text = f"尺寸: {original_width}x{original_height} | 大小: {file_size_kb:.1f}KB{rect_info}"
            self.popup_image_info_label.config(text=image_info_text)
            
        except Exception as e:
            print(f"显示弹窗图片失败: {e}")
            import traceback
            traceback.print_exc()
            self.popup_image_label.config(image="", text="显示失败")
            self.popup_image_info_label.config(text="")
            
    def add_thumbnail(self, image_info):
        """添加图片缩略图"""
        image_path = image_info['filename']
        if not image_path or not os.path.exists(image_path):
            return
            
        try:
            # 加载图片并创建缩略图
            image = Image.open(image_path)
            
            # 创建缩略图（80x60）
            thumbnail_size = (80, 60)
            thumbnail = image.copy()
            thumbnail.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # 转换为Tkinter可显示的格式
            photo = ImageTk.PhotoImage(thumbnail)
            
            # 创建缩略图标签
            thumbnail_label = tk.Label(
                self.thumbnail_container,
                image=photo,
                relief="raised",
                bd=1,
                cursor="hand2"  # 鼠标悬停时显示手型
            )
            thumbnail_label.image = photo  # 保持引用
            thumbnail_label.pack(side=tk.LEFT, padx=5, pady=5)
            
            # 绑定点击事件
            thumbnail_label.bind("<Button-1>", lambda e, info=image_info: self.show_popup(info))
            
            # 存储引用
            self.thumbnail_labels.append(thumbnail_label)
            
        except Exception as e:
            print(f"创建缩略图失败: {e}")
            
    def clear_thumbnails(self):
        """清除所有缩略图"""
        for label in self.thumbnail_labels:
            label.destroy()
        self.thumbnail_labels = []
        
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
                        # 显示所有标记，而不只是值为 'true' 的标记
                        mark_display = [f"{mark['name']}:{mark['value']}" for mark in marks]
                        if mark_display:
                            mark_text = f" - {', '.join(mark_display)}"
                    
                    # 添加到列表
                    rect_text = f"目标 {i+1}{mark_text}"
                    self.rect_listbox.insert(tk.END, rect_text)
                    self.current_rects.append(rect_info)
        
        # 重置选择状态 - 但保留当前选择状态
        # 只有在没有选择且没有显示全部时才重置
        if self.selected_rect_index is not None and self.rect_listbox.size() > 0:
            # 保持当前选择状态，但确保索引在有效范围内
            if self.selected_rect_index < self.rect_listbox.size():
                self.rect_listbox.selection_set(self.selected_rect_index)
            else:
                # 如果索引超出范围，重置选择状态
                self.selected_rect_index = None
                self.show_all_rects_flag = False
        elif self.show_all_rects_flag:
            # 显示全部模式，保持状态
            pass
        else:
            # 重置选择状态
            self.selected_rect_index = None
            self.show_all_rects_flag = False
        
    def on_rect_select(self, event):
        """矩形框选择事件处理"""
        selection = self.rect_listbox.curselection()
        if not selection:
            # 如果没有选择，则设置为不显示任何矩形框
            self.selected_rect_index = None
            self.show_all_rects_flag = False
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
        """刷新图片显示（用于弹窗中的矩形框选择）"""
        # 获取当前消息的图片信息
        if not self.current_message:
            print("当前消息为空")
            return
            
        message_uuid = self.current_message.get("uuid")
        if not message_uuid:
            print("当前消息没有UUID，无法刷新图片显示")
            return
            
        # 从缓存中获取图片信息
        parser = ParserRegistry.get_parser(self.current_message["parsed_data"]["event_type"])
        image_info_list = parser.extract_image_info_list(self.current_message["parsed_data"])
        
        if image_info_list and self.current_image_path:
            # 使用第一个图片的信息（支持多图片的情况）
            image_info = image_info_list[0]
            image_info['filename'] = self.current_image_path
            
            # 确保弹窗是可见的
            popup_state = self.popup.state()
            
            if popup_state == "withdrawn":
                # 如果弹窗已隐藏，重新显示
                self.show_popup(image_info)
            elif popup_state == "normal":
                # 如果弹窗正常显示，强制重新显示图片
                self.display_image_in_popup(image_info)
            else:
                # 其他状态（如iconic最小化），先显示再刷新
                self.popup.deiconify()
                self.display_image_in_popup(image_info)
        
    def draw_rect_in_popup(self, draw, rect_info, image, font, index):
        """在弹窗中绘制单个矩形框及其标记信息"""
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
        self.current_image_path = None
        self.clear_thumbnails()

    def delete_message_images(self, message_uuid):
        """删除指定消息UUID对应的所有图片文件和缓存"""
        deleted_count = 0
        
        # 遍历缓存，找到该消息UUID对应的所有图片
        cache_keys_to_delete = []
        for cache_key, image_path in self.image_cache.items():
            if cache_key[0] == message_uuid:  # cache_key[0] 是 message_uuid
                cache_keys_to_delete.append(cache_key)
                # 删除图片文件
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        deleted_count += 1
                        print(f"删除图片文件: {image_path}")
                except Exception as e:
                    print(f"删除图片文件失败 {image_path}: {e}")
        
        # 从缓存中删除对应的条目
        for cache_key in cache_keys_to_delete:
            del self.image_cache[cache_key]
        
        return deleted_count

    def cleanup_all_images(self):
        """清理整个图片文件夹下的所有内容"""
        total_deleted = 0
        downloads_dir = './downloads'
        
        # 删除整个downloads文件夹下的所有文件
        if os.path.exists(downloads_dir):
            for filename in os.listdir(downloads_dir):
                file_path = os.path.join(downloads_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        total_deleted += 1
                        print(f"删除图片文件: {file_path}")
                except Exception as e:
                    print(f"删除图片文件失败 {file_path}: {e}")
        
        # 清空缓存
        self.image_cache.clear()
        
        # 清空缩略图
        self.clear_thumbnails()
        
        print(f"总共删除 {total_deleted} 个图片文件（删除整个downloads文件夹下的所有文件）")
        return total_deleted
        
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
        """显示消息详情（UUID版本）"""
        self.current_message = message
        self.detail_text.config(state=NORMAL)
        self.detail_text.delete(1.0, END)
        
        # 清除当前图片显示
        self.clear_image()
  
        self.detail_text.insert(END, f"消息UUID: {self.current_message.get('uuid', 'N/A')}\n")
        self.detail_text.insert(END, f"来源: {self.current_message.get('source')}\n")
        self.detail_text.insert(END, f"来源IP: {self.current_message.get('ip', 'N/A')}\n")
        
        self.detail_text.insert(END, f"接收时间: {self.current_message['timestamp']}\n")
        self.detail_text.insert(END, "-" * 80 + "\n\n")
        
        # 显示所有图片信息
        message_uuid = self.current_message.get("uuid")
        if message_uuid:
            self.display_message_images(message_uuid)
                
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

    def display_message_images(self, message_uuid):
        """显示消息的所有图片"""
        # 获取消息的所有图片
        parser = ParserRegistry.get_parser(self.current_message["parsed_data"]["event_type"])
        image_info_list = parser.extract_image_info_list(self.current_message["parsed_data"])
        
        if not image_info_list:
            return
            
        self.detail_text.insert(END, "图片信息:\n")
        self.detail_text.insert(END, "-" * 40 + "\n")
        
        for image_index, image_info in enumerate(image_info_list):
            # 检查图片缓存
            cache_key = (message_uuid, image_index)
            if cache_key in self.image_cache:
                # 图片已存在缓存中
                image_path = self.image_cache[cache_key]
                image_info['filename'] = image_path
                self.add_thumbnail(image_info)
                # 设置当前图片路径（使用第一个可用的图片）
                if image_index == 0:
                    self.current_image_path = image_path
                self.detail_text.insert(END, f"图片 {image_index + 1}: 已下载完成\n")
            else:
                # 图片需要下载
                self.detail_text.insert(END, f"图片 {image_index + 1}: 正在下载...\n")
                
        self.detail_text.insert(END, "-" * 40 + "\n\n")
        
    def check_image_download_with_uuid(self, image_info, message_uuid, image_index):
        """检查图片下载状态（UUID版本）"""
        print(f"检查图片下载状态: {image_info}, UUID: {message_uuid}, 序号: {image_index}")
        try:
            # 构建完整的图片路径
            image_filename = image_info['filename']
            image_path = os.path.join('./downloads', image_filename)
            print(f"图片路径: {image_path}")
            
            if os.path.exists(image_path):
                # 图片已下载完成，添加到缓存
                cache_key = (message_uuid, image_index)
                self.image_cache[cache_key] = image_path
                
                # 更新image_info中的filename为完整路径
                image_info['filename'] = image_path
                
                # 如果当前显示的消息是这个UUID，则添加缩略图
                if self.current_message and self.current_message.get("uuid") == message_uuid:
                    self.add_thumbnail(image_info)
                    # 设置当前图片路径（如果是第一张图片）
                    if image_index == 0:
                        self.current_image_path = image_path
                    # 更新消息详情显示下载完成
                    self.detail_text.config(state=NORMAL)
                    self.detail_text.insert(END, f"\n图片下载完成: {image_path}\n")
                    self.detail_text.config(state=DISABLED)
            else:
                # 图片还未下载完成，继续检查
                print(f"图片不存在，继续检查: {image_path}")
                self.root.after(500, lambda: self.check_image_download_with_uuid(image_info, message_uuid, image_index))
        except Exception as e:
            print(f"检查图片下载状态时出错: {e}")
            print(f"image_info类型: {type(image_info)}, 值: {image_info}")
        
    def on_message_received(self, message):
        """处理接收到的消息"""
        source = message["source"]
        if source not in self.messages:
            self.messages[source] = []
            self.uuid_counter[source] = 0

        # 为消息生成UUID
        message_uuid = str(uuid.uuid4())
        message["uuid"] = message_uuid
        self.message_uuid_map[message_uuid] = message

        # 获取对应的解析器
        parser = ParserRegistry.get_parser('basealarm')
        post_data = message.get("raw_data", b"")
        parsed_data = parser.parse(message['content_type'], post_data)
        message["parsed_data"] = parsed_data

        # 处理消息中的图片
        self.process_message_images(message)

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

    def process_message_images(self, message):
        """处理消息中的图片，与消息UUID关联"""
        message_uuid = message["uuid"]
        source = message["source"]
        
        # 获取图片信息
        parser = ParserRegistry.get_parser(message["parsed_data"]["event_type"])
        image_info_list = parser.extract_image_info_list(message["parsed_data"])
        
        if not image_info_list:
            return
            
        # 为每个图片生成序号
        for image_index, image_info in enumerate(image_info_list):
            # 检查图片是否已经存在
            cache_key = (message_uuid, image_index)
            if cache_key in self.image_cache:
                # 图片已存在，直接使用缓存，但保留rectList信息
                image_info['filename'] = self.image_cache[cache_key]
                # 图片已存在，不需要下载，但需要确保rectList信息被保留
                continue
                
            # 生成新的图片文件名（包含消息UUID和图片序号）
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S+0800")
            image_filename = f"image_{message_uuid[:8]}_{image_index}_{timestamp}.jpg"
            image_info['filename'] = image_filename
            
            # 检查文件系统是否已存在该图片
            image_path = os.path.join('./downloads', image_filename)
            if os.path.exists(image_path):
                # 文件已存在，添加到缓存，保留rectList信息
                self.image_cache[cache_key] = image_path
                image_info['filename'] = image_path
            else:
                # 需要下载图片
                self.image_handler.async_download(
                    image_info['url'],
                    image_filename
                )
                # 启动图片检查任务
                self.check_image_download_with_uuid(image_info, message_uuid, image_index)
        
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
        
    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            confirm = tk.messagebox.askyesno(
                "确认关闭", 
                "是否清理所有下载的图片文件？\n\n选择'是'将删除所有图片文件\n选择'否'将保留图片文件"
            )
            
            if confirm:
                deleted_count = self.cleanup_all_images()
                print("清理完成", f"已清理 {deleted_count} 个图片文件\n")
            
            # 执行清理操作
            self.cleanup()
            
            # 退出应用
            self.root.quit()
        except Exception as e:
            print(f"关闭窗口时出错: {e}")
            # 确保程序退出
            self.root.quit()

    def cleanup(self):
        """清理资源"""
        # 停止所有服务线程
        for tab in self.config_tab_instances.values():
            if hasattr(tab, "stop_service"):
                tab.stop_service()
        
        # 关闭图片弹窗
        if hasattr(self, 'popup') and self.popup:
            self.popup.destroy()

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
