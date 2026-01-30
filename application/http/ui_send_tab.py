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
                "url_path": "/httpalarm",
                "body": '{"msg":"hello"}',
                "query_params": [],
                "auth_type": "none",
                "auth_params": {},
                "headers": [],
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
        self.path_entry.pack(side="left", padx=(0, 0))

        # 发送按钮
        self.send_btn = ttk.Button(request_frame, text="发送", command=self.send_message, width=8)
        self.send_btn.grid(row=0, column=2, padx=(5, 10), pady=10, sticky="e")

        # 配置列权重使URL输入框可以扩展
        request_frame.columnconfigure(1, weight=1)

        # 主体左右分割区
        main_paned = PanedWindow(frame, orient=HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)

        # 左侧：参数配置区域
        left_frame = ttk.LabelFrame(main_paned)
        left_frame.pack_propagate(False)  # 防止子控件改变框架大小

        # 创建Notebook（选项卡）
        self.param_notebook = ttk.Notebook(left_frame)
        self.param_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Query参数选项卡
        query_frame = ttk.Frame(self.param_notebook)
        self.param_notebook.add(query_frame, text="Query参数")
        self._create_query_params_tab(query_frame)

        # 认证选项卡
        auth_frame = ttk.Frame(self.param_notebook)
        self.param_notebook.add(auth_frame, text="认证")
        self._create_auth_tab(auth_frame)

        # 请求头选项卡
        headers_frame = ttk.Frame(self.param_notebook)
        self.param_notebook.add(headers_frame, text="请求头")
        self._create_headers_tab(headers_frame)

        # 请求体选项卡
        body_frame = ttk.Frame(self.param_notebook)
        self.param_notebook.add(body_frame, text="请求体")
        self._create_body_tab(body_frame)

        # 设置左侧区域的最小宽度
        main_paned.add(left_frame, minsize=600)

        # 右侧：响应结果区域
        right_frame = ttk.LabelFrame(main_paned, text="响应结果")
        self.result_text = tk.Text(right_frame, height=12, state=DISABLED)
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)
        main_paned.add(right_frame, minsize=400)

    def _create_query_params_tab(self, parent):
        """创建Query参数选项卡"""
        # 使用简单的框架和滚动条
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True)

        # 创建滚动框架
        from tkinter import Scrollbar

        # 创建Canvas作为滚动容器
        canvas = tk.Canvas(main_frame, height=200)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)

        # 创建内部框架
        inner_frame = ttk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def configure_scrollregion(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner_frame.bind("<Configure>", configure_scrollregion)

        # 表头
        headers = ["Key", "Value", "描述", "操作"]
        for i, header in enumerate(headers):
            ttk.Label(inner_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=i, padx=2, pady=2, sticky="ew"
            )

        # 存储参数行的列表
        self.query_param_rows = []

        # 添加第一行空参数
        self._add_query_param_row(inner_frame, 1)

        # 添加参数按钮
        add_btn = ttk.Button(
            inner_frame,
            text="添加参数",
            command=lambda: self._add_query_param_row(inner_frame, len(self.query_param_rows) + 1),
        )
        add_btn.grid(row=100, column=0, columnspan=4, pady=5)

        # 布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return inner_frame

    def _add_query_param_row(self, parent, row_num, existing_data=None):
        """添加Query参数行"""
        row_data = existing_data if existing_data else {}

        # 绑定滚轮事件到Entry组件
        def _on_entry_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Key输入框
        key_var = tk.StringVar(
            value=existing_data.get("key", "").get() if existing_data and existing_data.get("key") else ""
        )
        key_entry = ttk.Entry(parent, textvariable=key_var, width=20)
        key_entry.grid(row=row_num, column=0, padx=2, pady=1, sticky="ew")
        key_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["key"] = key_var

        # Value输入框
        value_var = tk.StringVar(
            value=existing_data.get("value", "").get() if existing_data and existing_data.get("value") else ""
        )
        value_entry = ttk.Entry(parent, textvariable=value_var, width=20)
        value_entry.grid(row=row_num, column=1, padx=2, pady=1, sticky="ew")
        value_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["value"] = value_var

        # 描述输入框
        desc_var = tk.StringVar(
            value=existing_data.get("desc", "").get() if existing_data and existing_data.get("desc") else ""
        )
        desc_entry = ttk.Entry(parent, textvariable=desc_var, width=25)
        desc_entry.grid(row=row_num, column=2, padx=2, pady=1, sticky="ew")
        desc_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["desc"] = desc_var

        # 删除按钮
        def remove_row():
            # 直接销毁该行的所有组件
            for widget in parent.grid_slaves(row=row_num):
                widget.destroy()

            # 从列表中移除行数据
            if row_data in self.query_param_rows:
                self.query_param_rows.remove(row_data)

            # 重新构建所有行
            self._rebuild_query_params(parent)

        remove_btn = ttk.Button(parent, text="删除", command=remove_row, width=6)
        remove_btn.grid(row=row_num, column=3, padx=2, pady=1)
        row_data["remove_btn"] = remove_btn

        if not existing_data:
            self.query_param_rows.append(row_data)

        # 配置列权重
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)

    def _rebuild_query_params(self, parent):
        """重新构建Query参数行"""
        # 清空所有参数行（保留表头和添加按钮）
        for widget in parent.grid_slaves():
            row = widget.grid_info().get("row", 0)
            if row > 0 and row < 100:  # 只删除参数行，保留表头和添加按钮
                widget.destroy()

        # 重新创建所有参数行
        for i, row_data in enumerate(self.query_param_rows, 1):
            self._add_query_param_row(parent, i, row_data)

        # 如果所有行都被删除，添加一个空行
        if not self.query_param_rows:
            self._add_query_param_row(parent, 1)

    def _reorder_query_params(self, parent):
        """重新排序Query参数行"""
        # 获取所有行号并排序（只处理参数行，不处理添加按钮）
        row_numbers = []
        for widget in parent.grid_slaves():
            row = widget.grid_info().get("row", 0)
            if row > 0 and row < 100 and row not in row_numbers:  # 排除添加按钮行（row=100）
                row_numbers.append(row)

        row_numbers.sort()

        # 重新排列参数行
        for i, row_num in enumerate(row_numbers, 1):
            widgets = parent.grid_slaves(row=row_num)
            for widget in widgets:
                widget.grid(row=i)

    def _create_auth_tab(self, parent):
        """创建认证选项卡"""
        # 认证类型选择
        auth_frame = ttk.Frame(parent)
        auth_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(auth_frame, text="认证类型:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.auth_type_var = tk.StringVar(value=self.config_vars["auth_type"])
        auth_combo = ttk.Combobox(
            auth_frame,
            textvariable=self.auth_type_var,
            values=["none", "basic", "digest", "bearer"],
            state="readonly",
            width=10,
        )
        auth_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 认证参数区域
        self.auth_params_frame = ttk.Frame(parent)
        self.auth_params_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 根据认证类型显示不同的参数
        auth_combo.bind("<<ComboboxSelected>>", self._update_auth_params)
        self._update_auth_params()

    def _update_auth_params(self, event=None):
        """根据认证类型更新参数界面"""
        # 清空现有参数界面
        for widget in self.auth_params_frame.winfo_children():
            widget.destroy()

        auth_type = self.auth_type_var.get()

        if auth_type == "basic":
            ttk.Label(self.auth_params_frame, text="用户名:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            self.basic_username_var = tk.StringVar()
            ttk.Entry(self.auth_params_frame, textvariable=self.basic_username_var, width=20).grid(
                row=0, column=1, padx=5, pady=5, sticky="w"
            )

            ttk.Label(self.auth_params_frame, text="密码:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            self.basic_password_var = tk.StringVar()
            ttk.Entry(self.auth_params_frame, textvariable=self.basic_password_var, show="*", width=20).grid(
                row=1, column=1, padx=5, pady=5, sticky="w"
            )

        elif auth_type == "digest":
            ttk.Label(self.auth_params_frame, text="用户名:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            self.digest_username_var = tk.StringVar()
            ttk.Entry(self.auth_params_frame, textvariable=self.digest_username_var, width=20).grid(
                row=0, column=1, padx=5, pady=5, sticky="w"
            )

            ttk.Label(self.auth_params_frame, text="密码:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            self.digest_password_var = tk.StringVar()
            ttk.Entry(self.auth_params_frame, textvariable=self.digest_password_var, show="*", width=20).grid(
                row=1, column=1, padx=5, pady=5, sticky="w"
            )

            ttk.Label(self.auth_params_frame, text="域:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            self.digest_realm_var = tk.StringVar()
            ttk.Entry(self.auth_params_frame, textvariable=self.digest_realm_var, width=20).grid(
                row=2, column=1, padx=5, pady=5, sticky="w"
            )

            ttk.Label(self.auth_params_frame, text="随机数:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
            self.digest_nonce_var = tk.StringVar()
            ttk.Entry(self.auth_params_frame, textvariable=self.digest_nonce_var, width=30).grid(
                row=3, column=1, padx=5, pady=5, sticky="w"
            )

        elif auth_type == "bearer":
            ttk.Label(self.auth_params_frame, text="Token:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            self.bearer_token_var = tk.StringVar()
            ttk.Entry(self.auth_params_frame, textvariable=self.bearer_token_var, width=30).grid(
                row=0, column=1, padx=5, pady=5, sticky="w"
            )

    def _create_headers_tab(self, parent):
        """创建请求头选项卡（类似Query参数）"""
        # 使用简单的框架和滚动条
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True)

        # 创建Canvas作为滚动容器
        canvas = tk.Canvas(main_frame, height=200)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)

        # 创建内部框架
        inner_frame = ttk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def configure_scrollregion(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner_frame.bind("<Configure>", configure_scrollregion)

        # 表头
        headers = ["Header", "Value", "描述", "操作"]
        for i, header in enumerate(headers):
            ttk.Label(inner_frame, text=header, font=("Arial", 9, "bold")).grid(
                row=0, column=i, padx=2, pady=2, sticky="ew"
            )

        # 存储请求头行的列表
        self.header_rows = []

        # 添加第一行空请求头
        self._add_header_row(inner_frame, 1)

        # 添加请求头按钮
        add_btn = ttk.Button(
            inner_frame,
            text="添加请求头",
            command=lambda: self._add_header_row(inner_frame, len(self.header_rows) + 1),
        )
        add_btn.grid(row=100, column=0, columnspan=4, pady=5)

        # 布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return inner_frame

    def _add_header_row(self, parent, row_num, existing_data=None):
        """添加请求头行"""
        row_data = existing_data if existing_data else {}

        # 绑定滚轮事件到Entry组件
        def _on_entry_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Header输入框
        header_var = tk.StringVar(
            value=existing_data.get("header", "").get() if existing_data and existing_data.get("header") else ""
        )
        header_entry = ttk.Entry(parent, textvariable=header_var, width=20)
        header_entry.grid(row=row_num, column=0, padx=2, pady=1, sticky="ew")
        header_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["header"] = header_var

        # Value输入框
        value_var = tk.StringVar(
            value=existing_data.get("value", "").get() if existing_data and existing_data.get("value") else ""
        )
        value_entry = ttk.Entry(parent, textvariable=value_var, width=20)
        value_entry.grid(row=row_num, column=1, padx=2, pady=1, sticky="ew")
        value_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["value"] = value_var

        # 描述输入框
        desc_var = tk.StringVar(
            value=existing_data.get("desc", "").get() if existing_data and existing_data.get("desc") else ""
        )
        desc_entry = ttk.Entry(parent, textvariable=desc_var, width=25)
        desc_entry.grid(row=row_num, column=2, padx=2, pady=1, sticky="ew")
        desc_entry.bind("<MouseWheel>", _on_entry_mousewheel)
        row_data["desc"] = desc_var

        # 删除按钮
        def remove_row():
            # 直接销毁该行的所有组件
            for widget in parent.grid_slaves(row=row_num):
                widget.destroy()

            # 从列表中移除行数据
            if row_data in self.header_rows:
                self.header_rows.remove(row_data)

            # 重新构建所有行
            self._rebuild_headers(parent)

        remove_btn = ttk.Button(parent, text="删除", command=remove_row, width=6)
        remove_btn.grid(row=row_num, column=3, padx=2, pady=1)
        row_data["remove_btn"] = remove_btn

        if not existing_data:
            self.header_rows.append(row_data)

        # 配置列权重
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)

    def _rebuild_headers(self, parent):
        """重新构建请求头行"""
        # 清空所有请求头行（保留表头和添加按钮）
        for widget in parent.grid_slaves():
            row = widget.grid_info().get("row", 0)
            if row > 0 and row < 100:  # 只删除请求头行，保留表头和添加按钮
                widget.destroy()

        # 重新创建所有请求头行
        for i, row_data in enumerate(self.header_rows, 1):
            self._add_header_row(parent, i, row_data)

        # 如果所有行都被删除，添加一个空行
        if not self.header_rows:
            self._add_header_row(parent, 1)

    def _reorder_headers(self, parent):
        """重新排序请求头行"""
        # 获取所有行号并排序（只处理请求头行，不处理添加按钮）
        row_numbers = []
        for widget in parent.grid_slaves():
            row = widget.grid_info().get("row", 0)
            if row > 0 and row < 100 and row not in row_numbers:  # 排除添加按钮行（row=100）
                row_numbers.append(row)

        row_numbers.sort()

        # 重新排列请求头行
        for i, row_num in enumerate(row_numbers, 1):
            widgets = parent.grid_slaves(row=row_num)
            for widget in widgets:
                widget.grid(row=i)

    def _create_body_tab(self, parent):
        """创建请求体选项卡"""
        body_frame = ttk.Frame(parent)
        body_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(body_frame, text="请求体内容:").pack(anchor="w")

        # 请求体文本区域
        self.body_text = tk.Text(body_frame, width=60, height=15)
        self.body_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.body_text.insert(1.0, self.config_vars["body"])

    def update_status(self, status):
        pass

    def send_message(self):
        method = self.method_var.get()
        protocol = self.protocol_var.get()
        host = self.host_var.get().strip()
        path = self.path_var.get().strip()

        # 构建URL（包含Query参数）
        url = f"{protocol}://{host}{path}"

        # 处理Query参数
        query_params = []
        for row in self.query_param_rows:
            key = row["key"].get().strip()
            value = row["value"].get().strip()
            if key and value:
                query_params.append(f"{key}={value}")

        if query_params:
            url += "?" + "&".join(query_params)

        # 处理请求头
        headers = {}
        for row in self.header_rows:
            header = row["header"].get().strip()
            value = row["value"].get().strip()
            if header and value:
                headers[header] = value

        # 处理认证
        auth_type = self.auth_type_var.get()
        if auth_type == "basic" and hasattr(self, "basic_username_var") and hasattr(self, "basic_password_var"):
            username = self.basic_username_var.get().strip()
            password = self.basic_password_var.get().strip()
            if username and password:
                import base64

                auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth_str}"
        elif auth_type == "digest" and hasattr(self, "digest_username_var") and hasattr(self, "digest_password_var"):
            username = self.digest_username_var.get().strip()
            password = self.digest_password_var.get().strip()
            realm = self.digest_realm_var.get().strip() if hasattr(self, "digest_realm_var") else ""
            nonce = self.digest_nonce_var.get().strip() if hasattr(self, "digest_nonce_var") else ""

            if username and password:
                # 对于Digest认证，在Authorization头中包含密码信息，让send.py能够提取
                if realm and nonce:
                    # 如果有realm和nonce，构建包含密码的认证头
                    headers["Authorization"] = (
                        f'Digest username="{username}", password="{password}", realm="{realm}", nonce="{nonce}"'
                    )
                else:
                    # 如果没有realm和nonce，构建包含用户名和密码的认证头
                    headers["Authorization"] = f'Digest username="{username}", password="{password}"'
        elif auth_type == "bearer" and hasattr(self, "bearer_token_var"):
            token = self.bearer_token_var.get().strip()
            if token:
                headers["Authorization"] = f"Bearer {token}"

        # 获取请求体
        body = self.body_text.get(1.0, END).strip()

        try:
            poster = FastHTTPPost(url)
            # 根据请求方法选择不同的发送方式
            if method == "GET":
                status, response_headers, content = poster.get(headers=headers)
            elif method == "POST":
                status, response_headers, content = poster.post(
                    json_data=json.loads(body) if body else None, headers=headers
                )
            elif method == "PUT":
                status, response_headers, content = poster.put(
                    json_data=json.loads(body) if body else None, headers=headers
                )
            elif method == "DELETE":
                status, response_headers, content = poster.delete(headers=headers)
            else:
                status, response_headers, content = poster.post(
                    json_data=json.loads(body) if body else None, headers=headers
                )

            result = f"方法: {method}\nURL: {url}\n状态码: {status}\n响应头: {response_headers}\n响应体: {content.decode('utf-8', errors='replace')}"
        except Exception as e:
            result = f"方法: {method}\nURL: {url}\n错误: {e}"
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, result)
        self.result_text.config(state=DISABLED)


# 注册配置页面
MainWindow.register_config_tab(UITableType.SEND, SendMessageConfigTab)
