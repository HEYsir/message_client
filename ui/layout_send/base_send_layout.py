"""公共发送布局基类"""

from tkinter import *
from tkinter import ttk
import tkinter as tk
import json
import threading
import time
from ui.base_tab import BaseConfigTab
from datetime import datetime, timedelta
from ui.key_value_table import KeyValueTable, KeyValueTableWithCustomHeaders


def child_hook(name=None):
    """注解装饰器，标记子类方法为钩子函数"""

    def decorator(func):
        func._is_child_hook = True
        func._hook_name = name or func.__name__
        return func

    return decorator


class BaseSendLayout(BaseConfigTab):
    """公共发送布局基类，包含定时发送、请求体、认证等通用功能"""

    def _discover_child_hooks(self):
        """自动发现子类注解的钩子方法"""
        self._child_hooks = {}

        for name in dir(self):
            attr = getattr(self, name)
            if callable(attr) and hasattr(attr, "_is_child_hook") and attr._is_child_hook:
                self._child_hooks[attr._hook_name] = attr

    def call_child_hook(self, notebook):
        """调用特定的子类钩子"""
        for hookname, hook in self._child_hooks.items():
            # 基础配置选项卡（子类实现）
            new_frame = ttk.Frame(notebook)
            notebook.add(new_frame, text=hookname)
            hook(new_frame)

    def _init_config_vars(self):
        """初始化配置变量"""
        self.config_vars.update(
            {
                "name": "消息发送",
                "method": "POST",
                "protocol": "http",
                "host": "localhost",
                "url_path": "/api",
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
        """创建标签页内容 - 公共发送布局"""
        self._discover_child_hooks()

        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10, pady=10, expand=True)

        # 顶部请求行
        request_frame = ttk.LabelFrame(frame, text="请求")
        request_frame.pack(fill="x", padx=5, pady=5)
        self._create_request_line(request_frame)

        # 主体左右分割区
        main_paned = PanedWindow(frame, orient=HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)

        # 左侧：参数配置区域
        left_frame = ttk.LabelFrame(main_paned)
        left_frame.pack_propagate(False)
        self._create_parameter_area(left_frame)
        main_paned.add(left_frame, minsize=600)

        # 右侧：响应结果和发送控制区域
        right_frame = ttk.LabelFrame(main_paned, text="发送控制")
        self._create_result_and_control_area(right_frame)
        main_paned.add(right_frame, minsize=400)

    def _create_request_line(self, parent):
        """创建请求行（协议、主机、URI路径等）"""
        # 请求方法选择
        self.method_var = tk.StringVar(value=self.config_vars["method"])
        method_combo = ttk.Combobox(
            parent,
            textvariable=self.method_var,
            values=["GET", "POST", "PUT", "DELETE"],
            state="readonly",
            width=8,
        )
        method_combo.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        # URL输入框
        url_frame = ttk.Frame(parent)
        url_frame.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        # 协议选择
        self.protocol_var = tk.StringVar(value=self.config_vars["protocol"])
        protocol_combo = ttk.Combobox(
            url_frame, textvariable=self.protocol_var, values=["http", "https"], state="readonly", width=4
        )
        protocol_combo.pack(side="left", padx=(0, 0))

        # 协议分隔符
        protocol_label = ttk.Label(url_frame, text="://")
        protocol_label.pack(side="left", padx=(0, 0))

        # 主机地址
        self.host_var = tk.StringVar(value=self.config_vars["host"])
        self.host_entry = ttk.Entry(url_frame, textvariable=self.host_var, width=15)
        self.host_entry.pack(side="left", padx=(0, 0))

        # URI路径
        self.path_var = tk.StringVar(value=self.config_vars["url_path"])
        self.path_entry = ttk.Entry(url_frame, textvariable=self.path_var, width=100)
        self.path_entry.pack(side="left", padx=(0, 0))

        # 发送按钮
        self.send_btn = ttk.Button(parent, text="发送", command=self.send_message, width=8)
        self.send_btn.grid(row=0, column=2, padx=(5, 10), pady=10, sticky="e")

        # 配置列权重
        parent.columnconfigure(1, weight=1)

    def _create_parameter_area(self, parent):
        """创建参数配置区域"""
        # 创建Notebook（选项卡）
        self.param_notebook = ttk.Notebook(parent)
        self.param_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.call_child_hook(self.param_notebook)

        # 请求体选项卡
        body_frame = ttk.Frame(self.param_notebook)
        self.param_notebook.add(body_frame, text="请求体")
        self._create_body_tab(body_frame)

        # 定时发送选项卡
        schedule_frame = ttk.Frame(self.param_notebook)
        self.param_notebook.add(schedule_frame, text="定时发送")
        self._create_schedule_tab(schedule_frame)

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

    def _create_result_and_control_area(self, parent):
        """创建响应结果和发送控制区域"""
        # 发送按钮
        send_frame = ttk.Frame(parent)
        send_frame.pack(fill="x", padx=10, pady=10)

        self.send_btn = ttk.Button(send_frame, text="发送", command=self.send_message, width=10)
        self.send_btn.pack(side="left", padx=5, pady=5)

        # 响应结果文本框
        result_frame = ttk.Frame(parent)
        result_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(result_frame, text="响应结果:").pack(anchor="w")

        self.result_text = tk.Text(result_frame, height=12, state=DISABLED)
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)

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
        """发送单个请求（用于并发发送）- 子类需要实现"""
        raise NotImplementedError("子类必须实现 _send_single_request 方法")

    def send_message(self):
        """发送消息的主方法"""
        send_mode = self.send_mode_var.get()

        if send_mode == "single":
            self._send_single_message()
        elif send_mode == "scheduled":
            self.start_scheduled_sending()

    def _send_single_message(self):
        """发送单次消息 - 子类需要实现"""
        raise NotImplementedError("子类必须实现 _send_single_message 方法")

    def update_status(self, status):
        """更新状态 - 子类可以重写"""
        pass
