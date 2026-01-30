from tkinter import *
from tkinter import ttk
import tkinter as tk
import json
import threading
import time
from datetime import datetime, timedelta
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow, UITableType
from ui.key_value_table import KeyValueTable, KeyValueTableWithCustomHeaders
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
                # 定时发送控制参数
                "send_mode": "single",  # single: 单次发送, scheduled: 定时发送
                "concurrent_count": 1,  # 每秒并发次数
                "send_interval": 1,  # 发送间隔（秒）
                "duration": 60,  # 持续时间（秒）
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 开始时间
                "end_time": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),  # 结束时间
                "is_sending": False,  # 是否正在发送
            }
        )
        # 定时发送线程控制
        self.sending_thread = None
        self.stop_sending = False

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

        # 定时发送选项卡
        schedule_frame = ttk.Frame(self.param_notebook)
        self.param_notebook.add(schedule_frame, text="定时发送")
        self._create_schedule_tab(schedule_frame)

        # 设置左侧区域的最小宽度
        main_paned.add(left_frame, minsize=600)

        # 右侧：响应结果区域
        right_frame = ttk.LabelFrame(main_paned, text="响应结果")
        self.result_text = tk.Text(right_frame, height=12, state=DISABLED)
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)
        main_paned.add(right_frame, minsize=400)

    def _create_query_params_tab(self, parent):
        """创建Query参数选项卡"""
        # 使用公共Key-Value组件
        self.query_params_table = KeyValueTable(parent, headers=["Key", "Value", "描述", "操作"], row_height=200)
        return self.query_params_table.main_frame

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
        # 使用公共Key-Value组件，自定义表头为Header
        self.headers_table = KeyValueTableWithCustomHeaders(
            parent, headers=["Header", "Value", "描述", "操作"], row_height=200
        )
        return self.headers_table.main_frame

    def _create_body_tab(self, parent):
        """创建请求体选项卡"""
        body_frame = ttk.Frame(parent)
        body_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(body_frame, text="请求体内容:").pack(anchor="w")

        # 请求体文本区域
        self.body_text = tk.Text(body_frame, width=60, height=15)
        self.body_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.body_text.insert(1.0, self.config_vars["body"])

    def _create_schedule_tab(self, parent):
        """创建定时发送选项卡"""
        schedule_frame = ttk.Frame(parent)
        schedule_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 发送模式选择
        mode_frame = ttk.LabelFrame(schedule_frame, text="发送模式")
        mode_frame.pack(fill="x", padx=5, pady=5)

        self.send_mode_var = tk.StringVar(value=self.config_vars["send_mode"])
        single_radio = ttk.Radiobutton(mode_frame, text="单次发送", variable=self.send_mode_var, value="single")
        single_radio.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        scheduled_radio = ttk.Radiobutton(mode_frame, text="定时发送", variable=self.send_mode_var, value="scheduled")
        scheduled_radio.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # 并发控制配置
        concurrent_frame = ttk.LabelFrame(schedule_frame, text="并发控制")
        concurrent_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(concurrent_frame, text="每秒并发次数:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.concurrent_count_var = tk.IntVar(value=self.config_vars["concurrent_count"])
        concurrent_spinbox = ttk.Spinbox(
            concurrent_frame, from_=1, to=100, textvariable=self.concurrent_count_var, width=10
        )
        concurrent_spinbox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 发送间隔配置
        interval_frame = ttk.LabelFrame(schedule_frame, text="发送间隔")
        interval_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(interval_frame, text="发送间隔(秒):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.send_interval_var = tk.IntVar(value=self.config_vars["send_interval"])
        interval_spinbox = ttk.Spinbox(interval_frame, from_=1, to=3600, textvariable=self.send_interval_var, width=10)
        interval_spinbox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(interval_frame, text="持续时间(秒):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.duration_var = tk.IntVar(value=self.config_vars["duration"])
        duration_spinbox = ttk.Spinbox(interval_frame, from_=1, to=86400, textvariable=self.duration_var, width=10)
        duration_spinbox.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # 发送计划配置
        plan_frame = ttk.LabelFrame(schedule_frame, text="发送计划")
        plan_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(plan_frame, text="开始时间:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.start_time_var = tk.StringVar(value=self.config_vars["start_time"])
        start_entry = ttk.Entry(plan_frame, textvariable=self.start_time_var, width=20)
        start_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(plan_frame, text="结束时间:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.end_time_var = tk.StringVar(value=self.config_vars["end_time"])
        end_entry = ttk.Entry(plan_frame, textvariable=self.end_time_var, width=20)
        end_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # 定时发送控制按钮
        control_frame = ttk.Frame(schedule_frame)
        control_frame.pack(fill="x", padx=5, pady=10)

        self.start_schedule_btn = ttk.Button(control_frame, text="开始定时发送", command=self.start_scheduled_sending)
        self.start_schedule_btn.pack(side="left", padx=5)

        self.stop_schedule_btn = ttk.Button(
            control_frame, text="停止定时发送", command=self.stop_scheduled_sending, state="disabled"
        )
        self.stop_schedule_btn.pack(side="left", padx=5)

        # 状态显示
        self.status_label = ttk.Label(schedule_frame, text="状态: 准备就绪")
        self.status_label.pack(pady=5)

        return schedule_frame

    def start_scheduled_sending(self):
        """开始定时发送"""
        if self.config_vars["is_sending"]:
            return

        # 验证时间格式
        try:
            start_time = datetime.strptime(self.start_time_var.get(), "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(self.end_time_var.get(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.status_label.config(text="状态: 时间格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式")
            return

        if start_time >= end_time:
            self.status_label.config(text="状态: 开始时间必须早于结束时间")
            return

        # 更新状态
        self.config_vars["is_sending"] = True
        self.stop_sending = False
        self.start_schedule_btn.config(state="disabled")
        self.stop_schedule_btn.config(state="normal")
        self.status_label.config(text="状态: 定时发送已启动")

        # 启动发送线程
        self.sending_thread = threading.Thread(target=self._scheduled_sending_worker)
        self.sending_thread.daemon = True
        self.sending_thread.start()

    def stop_scheduled_sending(self):
        """停止定时发送"""
        self.stop_sending = True
        self.config_vars["is_sending"] = False
        self.start_schedule_btn.config(state="normal")
        self.stop_schedule_btn.config(state="disabled")
        self.status_label.config(text="状态: 定时发送已停止")

    def _scheduled_sending_worker(self):
        """定时发送工作线程"""
        concurrent_count = self.concurrent_count_var.get()
        send_interval = self.send_interval_var.get()
        duration = self.duration_var.get()

        start_time = datetime.strptime(self.start_time_var.get(), "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(self.end_time_var.get(), "%Y-%m-%d %H:%M:%S")

        # 等待到开始时间
        current_time = datetime.now()
        if current_time < start_time:
            wait_seconds = (start_time - current_time).total_seconds()
            self.status_label.config(text=f"状态: 等待开始时间，剩余 {int(wait_seconds)} 秒")
            time.sleep(wait_seconds)

        # 开始定时发送
        start_timestamp = time.time()

        while not self.stop_sending:
            current_time = datetime.now()
            if current_time >= end_time:
                self.status_label.config(text="状态: 定时发送已完成（到达结束时间）")
                break

            # 检查是否超过持续时间
            elapsed_time = time.time() - start_timestamp
            if elapsed_time >= duration:
                self.status_label.config(text="状态: 定时发送已完成（到达持续时间）")
                break

            # 并发发送请求
            threads = []
            for i in range(concurrent_count):
                thread = threading.Thread(target=self._send_single_request)
                thread.daemon = True
                thread.start()
                threads.append(thread)

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            # 更新状态
            remaining_time = min(duration - elapsed_time, (end_time - current_time).total_seconds())
            self.status_label.config(
                text=f"状态: 发送中... 已发送 {int(elapsed_time/send_interval) * concurrent_count} 个请求，剩余时间 {int(remaining_time)} 秒"
            )

            # 等待间隔时间
            if not self.stop_sending and elapsed_time + send_interval <= duration:
                time.sleep(send_interval)

        # 发送完成，重置状态
        self.config_vars["is_sending"] = False
        self.start_schedule_btn.config(state="normal")
        self.stop_schedule_btn.config(state="disabled")

    def _send_single_request(self):
        """发送单个请求（用于并发发送）"""
        try:
            method = self.method_var.get()
            protocol = self.protocol_var.get()
            host = self.host_var.get().strip()
            path = self.path_var.get().strip()

            # 构建URL（包含Query参数）
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
                    import base64

                    auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers["Authorization"] = f"Basic {auth_str}"
            elif (
                auth_type == "digest" and hasattr(self, "digest_username_var") and hasattr(self, "digest_password_var")
            ):
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

        except Exception as e:
            # 在定时发送模式下，不显示单个请求的错误，避免界面卡顿
            pass

    def update_status(self, status):
        pass

    def send_message(self):
        """发送消息的主方法，根据发送模式决定单次发送还是定时发送"""
        send_mode = self.send_mode_var.get()

        if send_mode == "single":
            self._send_single_message()
        elif send_mode == "scheduled":
            self.start_scheduled_sending()

    def _send_single_message(self):
        """发送单次消息"""
        method = self.method_var.get()
        protocol = self.protocol_var.get()
        host = self.host_var.get().strip()
        path = self.path_var.get().strip()

        # 构建URL（包含Query参数）
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
            header = item["key"].strip()  # 使用key字段存储header名称
            value = item["value"].strip()
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
