from tkinter import *
from tkinter import ttk
import tkinter as tk
import json
import base64
from ui.main_window import MainWindow, UITableType
from ui.layout_send import BaseSendLayout, child_hook
from ui.key_value_table import KeyValueTable, KeyValueTableWithCustomHeaders
from application.http.send import FastHTTPPost


class HttpSendMessageConfigTab(BaseSendLayout):
    """HTTP消息发送配置选项卡，使用公共发送布局"""

    def _init_config_vars(self):
        """重写初始化配置变量，设置HTTP特定的默认值"""
        super()._init_config_vars()
        # 更新HTTP特定的默认配置
        self.config_vars.update(
            {
                "name": "HTTP消息发送",
                "protocol": "http",
                "host": "localhost",
                "url_path": "/httpalarm",
                "body": '{"msg":"hello"}',
            }
        )

    @child_hook("基础配置")
    def _create_basic_config_tab(self, parent):
        """创建HTTP基础配置选项卡"""
        basic_frame = ttk.Frame(parent)
        basic_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 基础配置说明
        info_label = ttk.Label(
            basic_frame, text="HTTP协议支持GET、POST、PUT、DELETE方法，支持Basic、Digest、Bearer认证"
        )
        info_label.pack(anchor="w", pady=5)

        # 这里可以添加其他HTTP特定的配置项
        # 例如：超时设置、重试次数、SSL验证等

        config_frame = ttk.LabelFrame(basic_frame, text="高级配置")
        config_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(config_frame, text="连接超时(秒):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.timeout_var = tk.IntVar(value=30)
        timeout_entry = ttk.Entry(config_frame, textvariable=self.timeout_var, width=10)
        timeout_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(config_frame, text="重试次数:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.retry_var = tk.IntVar(value=3)
        retry_entry = ttk.Entry(config_frame, textvariable=self.retry_var, width=10)
        retry_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ssl_frame = ttk.Frame(config_frame)
        ssl_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="w")

        self.ssl_verify_var = tk.BooleanVar(value=True)
        ssl_check = ttk.Checkbutton(ssl_frame, text="SSL证书验证", variable=self.ssl_verify_var)
        ssl_check.pack(side="left", padx=(0, 10))

    @child_hook("请求参数")
    def _create_query_params_tab(self, parent):
        """创建HTTP Query参数选项卡"""
        self.query_params_table = KeyValueTable(parent, headers=["Key", "Value", "描述", "操作"], row_height=200)
        self.query_params_table.main_frame.pack(fill="both", expand=True, padx=5, pady=5)

    @child_hook("认证信息")
    def _create_auth_tab(self, parent):
        """创建HTTP认证选项卡"""
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

        # 绑定认证类型变化事件
        auth_combo.bind("<<ComboboxSelected>>", self._update_http_auth_params)
        self._update_http_auth_params()

    @child_hook("请求头")
    def _create_headers_tab(self, parent):
        """创建HTTP请求头选项卡"""
        self.headers_table = KeyValueTableWithCustomHeaders(
            parent, headers=["Header", "Value", "描述", "操作"], row_height=200
        )
        self.headers_table.main_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def _update_http_auth_params(self, event=None):
        """根据认证类型更新HTTP认证参数界面"""
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

    def _send_single_request(self):
        """发送单个HTTP请求（用于并发发送）"""
        try:
            self._send_http_request()
        except Exception:
            # 在定时发送模式下，不显示单个请求的错误
            pass

    def _send_single_message(self):
        """发送单次HTTP消息"""
        try:
            self._send_http_request()
        except Exception as e:
            # 在单次发送模式下显示错误信息
            method = self.method_var.get()
            protocol = self.protocol_var.get()
            host = self.host_var.get().strip()
            path = self.path_var.get().strip()
            url = f"{protocol}://{host}{path}"

            result = f"方法: {method}\nURL: {url}\n错误: {e}"
            self.result_text.config(state=NORMAL)
            self.result_text.delete(1.0, END)
            self.result_text.insert(END, result)
            self.result_text.config(state=DISABLED)

    def _send_http_request(self):
        """执行HTTP请求的核心逻辑"""
        method = self.method_var.get()
        protocol = self.protocol_var.get()
        host = self.host_var.get().strip()
        path = self.path_var.get().strip()

        # 构建基础URL
        url = f"{protocol}://{host}{path}"

        # 处理Query参数
        query_params = []
        query_data = self.query_params_table.get_data()
        for item in query_data:
            key = item["key"].strip()
            value = item["value"].strip()
            if key and value:
                query_params.append(f"{key}={value}")

        if query_params:
            url += "?" + "&".join(query_params)

        # 处理请求头
        headers = {}
        headers_data = self.headers_table.get_data()
        for item in headers_data:
            header = item["key"].strip()
            value = item["value"].strip()
            if header and value:
                headers[header] = value

        # 处理认证
        auth_type = self.auth_type_var.get()
        if auth_type == "basic" and hasattr(self, "basic_username_var") and hasattr(self, "basic_password_var"):
            username = self.basic_username_var.get().strip()
            password = self.basic_password_var.get().strip()
            if username and password:
                auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {auth_str}"
        elif auth_type == "digest" and hasattr(self, "digest_username_var") and hasattr(self, "digest_password_var"):
            username = self.digest_username_var.get().strip()
            password = self.digest_password_var.get().strip()
            realm = self.digest_realm_var.get().strip() if hasattr(self, "digest_realm_var") else ""
            nonce = self.digest_nonce_var.get().strip() if hasattr(self, "digest_nonce_var") else ""

            if username and password:
                if realm and nonce:
                    headers["Authorization"] = (
                        f'Digest username="{username}", password="{password}", realm="{realm}", nonce="{nonce}"'
                    )
                else:
                    headers["Authorization"] = f'Digest username="{username}", password="{password}"'
        elif auth_type == "bearer" and hasattr(self, "bearer_token_var"):
            token = self.bearer_token_var.get().strip()
            if token:
                headers["Authorization"] = f"Bearer {token}"

        # 获取请求体
        body = self.body_text.get(1.0, END).strip()

        # 执行HTTP请求
        poster = FastHTTPPost(url)
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

        # 处理响应结果
        result = f"方法: {method}\nURL: {url}\n状态码: {status}\n响应头: {response_headers}\n响应体: {content.decode('utf-8', errors='replace')}"
        self.result_text.config(state=NORMAL)
        self.result_text.delete(1.0, END)
        self.result_text.insert(END, result)
        self.result_text.config(state=DISABLED)


# 注册配置页面
MainWindow.register_config_tab(UITableType.SEND, HttpSendMessageConfigTab)
