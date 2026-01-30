from tkinter import *
from tkinter import ttk
import tkinter as tk


class KeyValueTable:
    """Key-Value表格组件，用于显示和编辑键值对数据"""

    def __init__(self, parent, headers=None, row_height=200):
        """
        初始化Key-Value表格组件

        Args:
            parent: 父组件
            headers: 表头列表，默认为["Key", "Value", "描述", "操作"]
            row_height: 表格区域高度
        """
        self.parent = parent
        self.headers = headers or ["Key", "Value", "描述", "操作"]
        self.row_height = row_height
        self.rows = []  # 存储所有行的数据

        # 创建主框架
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill="both", expand=True)

        # 创建Canvas作为滚动容器
        self.canvas = tk.Canvas(self.main_frame, height=row_height)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)

        # 创建内部框架
        self.inner_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        def configure_scrollregion(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.inner_frame.bind("<Configure>", configure_scrollregion)

        # 创建表头
        self._create_headers()

        # 布局
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 添加空行
        self.add_empty_row()

    def _create_headers(self):
        """创建表头"""
        for i, header in enumerate(self.headers):
            ttk.Label(self.inner_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=i, padx=2, pady=2, sticky="ew"
            )

    def add_empty_row(self):
        """添加一个空行"""
        row_num = len(self.rows) + 1
        row_data = {}

        # 绑定滚轮事件到Entry组件
        def _on_entry_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Key输入框
        key_var = tk.StringVar()
        key_entry = ttk.Entry(self.inner_frame, textvariable=key_var, width=20)
        key_entry.grid(row=row_num, column=0, padx=2, pady=1, sticky="ew")
        key_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["key"] = key_var

        # Value输入框
        value_var = tk.StringVar()
        value_entry = ttk.Entry(self.inner_frame, textvariable=value_var, width=20)
        value_entry.grid(row=row_num, column=1, padx=2, pady=1, sticky="ew")
        value_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["value"] = value_var

        # 描述输入框
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(self.inner_frame, textvariable=desc_var, width=25)
        desc_entry.grid(row=row_num, column=2, padx=2, pady=1, sticky="ew")
        desc_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["desc"] = desc_var

        # 删除按钮
        def remove_row():
            # 直接销毁该行的所有组件
            for widget in self.inner_frame.grid_slaves(row=row_num):
                widget.destroy()

            # 从列表中移除行数据
            if row_data in self.rows:
                self.rows.remove(row_data)

            # 如果删除的是最后一行，添加一个空行
            if len(self.rows) == 0:
                self.add_empty_row()

        remove_btn = ttk.Button(self.inner_frame, text="删除", command=remove_row, width=6)
        remove_btn.grid(row=row_num, column=3, padx=2, pady=1)
        row_data["remove_btn"] = remove_btn
        row_data["row_num"] = row_num

        self.rows.append(row_data)

        # 配置列权重
        self.inner_frame.columnconfigure(0, weight=1)
        self.inner_frame.columnconfigure(1, weight=1)
        self.inner_frame.columnconfigure(2, weight=1)

        # 添加新行按钮（放在最后一行）
        self._update_add_button()

        return row_data

    def _update_add_button(self):
        """更新添加按钮的位置"""
        # 移除现有的添加按钮
        for widget in self.inner_frame.grid_slaves(row=100):
            widget.destroy()

        # 添加新的添加按钮
        add_btn = ttk.Button(
            self.inner_frame,
            text="添加",
            command=self.add_empty_row,
        )
        add_btn.grid(row=100, column=0, columnspan=4, pady=5)
        self.add_button = add_btn

    def get_data(self):
        """获取所有行的数据

        Returns:
            list: 包含所有行数据的列表
        """
        result = []
        for row in self.rows:
            key = row["key"].get().strip()
            value = row["value"].get().strip()
            desc = row["desc"].get().strip()
            if key or value or desc:  # 只要有一个字段有内容就返回
                result.append({"key": key, "value": value, "desc": desc})
        return result

    def set_data(self, data):
        """设置表格数据

        Args:
            data: 要设置的数据列表
        """
        # 清空现有数据
        self.clear()

        # 添加新数据
        for item in data:
            row_data = self.add_empty_row()
            row_data["key"].set(item.get("key", ""))
            row_data["value"].set(item.get("value", ""))
            row_data["desc"].set(item.get("desc", ""))

    def clear(self):
        """清空表格数据"""
        # 清空所有行
        for widget in self.inner_frame.grid_slaves():
            row = widget.grid_info().get("row", 0)
            if row > 0:  # 保留表头
                widget.destroy()

        self.rows = []

        # 重新创建表头
        self._create_headers()

        # 添加一个空行
        self.add_empty_row()


class KeyValueTableWithCustomHeaders(KeyValueTable):
    """支持自定义表头的Key-Value表格组件"""

    def __init__(self, parent, headers=None, row_height=200):
        """
        初始化支持自定义表头的Key-Value表格组件

        Args:
            parent: 父组件
            headers: 表头列表，例如["Header", "Value", "描述", "操作"]
            row_height: 表格区域高度
        """
        super().__init__(parent, headers, row_height)
