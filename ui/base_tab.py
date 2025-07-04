import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod
from tkinter import ttk, filedialog
from tkinter import END
from typing import Type, Dict

class BaseConfigTab(ABC):
    """标签页基类"""

    def get_tab_name(self) -> str:
        return self.config_vars["name"]
    
    def __init__(self, parent):
        self.parent = parent
        self.config_vars = {}
        self._init_config_vars()
        
        # 创建框架作为标签页内容
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True)
        
        # 创建标签页内容
        self.create_tab_content()

    @abstractmethod
    def _init_config_vars(self):
        """参数初始化(子类实现)"""
        raise NotImplementedError("Subclass must implement _init_config_vars()")

    @abstractmethod
    def create_tab_content(self):
        """创建标签页具体内容（由子类实现）"""
        pass
    
    @abstractmethod
    def update_status(self):
        """创建标签页具体内容（由子类实现）"""
        pass

    def browse_file(self, entry_widget):
        """浏览文件并设置到输入框"""
        filepath = filedialog.askopenfilename()
        if filepath:
            entry_widget.configure(state='normal')
            entry_widget.delete(0, END)
            entry_widget.insert(0, filepath)
            entry_widget.configure(state='readonly')

class CollapsibleNotebook(ttk.Frame):
    """可折叠的标签页容器 - 保留标签选择条"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.expanded = True  # 初始为展开状p态p
        self.current_tab = None  # 当前选中的标签页pijoiasdasd

        # 创建顶部框架（包含折叠按钮和标签选择条）
        self.top_frame = ttk.Frame(self)
        self.top_frame.pack(fill="x", side="top")
        
        # 折叠/展开按钮
        self.toggle_btn = ttk.Button(
            self.top_frame,
            text="▲ 折叠",  # 向上箭头表示展开状态
            command=self.toggle,
            width=8
        )
        self.toggle_btn.pack(side="right", padx=(0, 10), pady=5)
        
        # 标签页容器（只包含标签选择条）
        self.notebook = ttk.Notebook(self.top_frame)
        self.notebook.pack(side="left", fill="x", expand=True)
        
        # 内容容器（可折叠）
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True)
        
        # 标签页字典（存储标签页内容框架）
        self.tabs:Dict[str, BaseConfigTab] = {}
        # 绑定标签切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 存储外部注册的回调函数
        self.external_tab_change_callbacks = []  # 存储外部注册的回调函数

    def add_tab(self, tab_class: Type[BaseConfigTab]):
        """添加新的标签页"""
        # 创建标签页内容框架（可折叠部分）
        tab = tab_class(self.content_frame)
        tab_name = tab.get_tab_name()

        # 添加到笔记本（标签选择条） - 使用占位框架
        placeholder_frame = ttk.Frame(self.notebook)
        self.notebook.add(placeholder_frame, text=tab_name)

        # 存储标签页实例
        self.tabs[tab_name] = tab
        
        # 默认隐藏所有标签页内容
        # tab.frame.pack_forget()
        # 如果是第一个标签页，设置为当前标签页
        if len(self.tabs) == 1:
            self.current_tab = tab_name
            self.tabs[tab_name].frame.pack(fill="both", expand=True)
        return tab
    
    def register_tab_change_callback(self, callback):
        """注册外部标签页切换回调函数"""
        if not callable(callback):
            raise TypeError("Callback must be a callable function")
        self.external_tab_change_callbacks.append(callback)

    def on_tab_changed(self, event):
        """当标签页切换时更新显示内容并调用外部回调"""
        selected_index = self.notebook.index(self.notebook.select())
        selected_tab = self.notebook.tab(selected_index, "text")
        self.current_tab = selected_tab

        # 更新显示内容
        if self.expanded:
            self._update_tab_display()

        # 调用外部注册的回调函数
        for callback in self.external_tab_change_callbacks:
            try:
                callback(self.current_tab)
            except Exception as e:
                print(f"Error in external callback: {e}")

    def _update_tab_display(self):
        """更新标签页显示"""
        # 隐藏所有标签页内容
        for tab in self.tabs.values():
            tab.frame.pack_forget()
        
        # 显示当前标签页内容
        if self.current_tab in self.tabs:
            self.tabs[self.current_tab].frame.pack(fill="both", expand=True)

    def toggle(self):
        """切换整个标签页容器的可见状态"""
        if self.expanded:
            # 折叠内容区域
            self.content_frame.pack_forget()
            self.toggle_btn.config(text="▼ 展开")  # 向下箭头表示折叠状态
            self.expanded = False
        else:
            # 展开内容区域
            self.content_frame.pack(fill="both", expand=True)
            self.toggle_btn.config(text="▲ 折叠")  # 向上箭头表示展开状态
            self.expanded = True
            # 确保显示当前标签页内容
            self._update_tab_display()
    
        # 重新布局父容器
        self.parent.update_idletasks()
    
    def get_selected_tab(self) -> str:
        """获取当前选中的标签页名称"""
        return self.current_tab if self.current_tab else ""


