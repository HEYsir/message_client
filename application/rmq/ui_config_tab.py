from tkinter import *
from tkinter import ttk
import pika
from tkinter import messagebox
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow, UITableType
from application.rmq.service import RabbitMQConsumer


class RMQConfigTab(BaseConfigTab):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbitmq_consumer = None  # 用于管理 Server 实例

    def _init_config_vars(self):
        """初始化配置变量"""
        self.config_vars.update(
            {
                "name": "RabbitMQ服务",
                "host": "10.41.131.252",
                "port": 5672,
                "virtual_host": "/",
                "username": "admin",
                "password": "backend15",
                "queue": "test",
                "durable": True,
                "status": "已停止",
            }
        )

    def _update_config_vars(self):
        """更新配置变量"""
        self.config_vars["host"] = self.rmq_host_entry.get()
        self.config_vars["port"] = int(self.rmq_port_entry.get())
        self.config_vars["virtual_host"] = self.rmq_vhost_entry.get()
        self.config_vars["username"] = self.rmq_user_entry.get()
        self.config_vars["password"] = self.rmq_pass_entry.get()
        self.config_vars["queue"] = self.rmq_queue_entry.get()
        self.config_vars["durable"] = self.rmq_durable_var.get()

    def create_tab_content(self):
        """设置RabbitMQ服务标签页 - 优化高度匹配"""
        self.style = ttk.Style()
        self.style.configure("green.TFrame", background="green")
        # frame = ttk.Frame(self.frame, style='green.TFrame')
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10)

        # 主机地址
        ttk.Label(frame, text="主机地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.rmq_host_entry = ttk.Entry(frame)
        self.rmq_host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.rmq_host_entry.insert(0, self.config_vars["host"])

        ttk.Label(frame, text="端口:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.rmq_port_entry = ttk.Entry(frame)
        self.rmq_port_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.rmq_port_entry.insert(0, str(self.config_vars["port"]))

        ttk.Label(frame, text="虚拟主机:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.rmq_vhost_entry = ttk.Entry(frame)
        self.rmq_vhost_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.rmq_vhost_entry.insert(0, self.config_vars["virtual_host"])

        ttk.Label(frame, text="队列名称:").grid(row=1, column=4, padx=5, pady=0, sticky="e")
        self.rmq_queue_entry = ttk.Entry(frame)
        self.rmq_queue_entry.grid(row=1, column=5, padx=5, pady=0, sticky="w")
        self.rmq_queue_entry.insert(0, self.config_vars["queue"])

        # 用户名
        ttk.Label(frame, text="用户名:").grid(row=1, column=0, padx=5, pady=0, sticky="e")
        self.rmq_user_entry = ttk.Entry(frame)
        self.rmq_user_entry.grid(row=1, column=1, padx=5, pady=0, sticky="w")
        self.rmq_user_entry.insert(0, self.config_vars["username"])

        # 密码
        ttk.Label(frame, text="密码:").grid(row=1, column=2, padx=5, pady=0, sticky="e")
        self.rmq_pass_entry = ttk.Entry(frame, show="*")
        self.rmq_pass_entry.grid(row=1, column=3, padx=5, pady=0, sticky="ew")
        self.rmq_pass_entry.insert(0, self.config_vars["password"])

        # 持久化队列
        self.rmq_durable_var = BooleanVar(value=self.config_vars["durable"])
        ttk.Checkbutton(frame, text="持久化队列", variable=self.rmq_durable_var).grid(
            row=1, column=6, padx=5, pady=0, sticky="w"
        )

        # 操作按钮
        btn_frame = Frame(frame)
        btn_frame.grid(row=1, column=6, columnspan=4, sticky="e", padx=5, pady=0)

        self.start_btn = ttk.Button(
            btn_frame,
            text="启动消费" if self.config_vars["status"] != "运行中" else "停止消费",
            width=10,
            command=self._toggle_service,
        )
        self.start_btn.pack(side=LEFT, padx=5)

        check_btn = ttk.Button(btn_frame, text="检查队列", width=10, command=self.check_rmq_queue)
        check_btn.pack(side=LEFT, padx=5)

    def _toggle_service(self):
        """切换服务状态"""
        if self.rabbitmq_consumer:
            if self.rabbitmq_consumer.is_alive():
                self.rabbitmq_consumer.stop()
            # 停止消费者
            self.rabbitmq_consumer.stop()
            self.rabbitmq_consumer = None
            self.config_vars["status"] = "已停止"
            self.start_btn.config(text="启动消费")
        else:
            self._update_config_vars()  # 确保使用最新的配置
            if not self.config_vars["host"] or not self.config_vars["queue"]:
                messagebox.showerror("配置错误", "请确保主机地址和队列名称已填写")
                return

            # 启动消费者
            self.rabbitmq_consumer = RabbitMQConsumer(self.config_vars)
            self.rabbitmq_consumer.start()
            self.config_vars["status"] = "运行中"
            self.start_btn.config(text="停止消费")

    def check_rmq_queue(self):
        """检查RabbitMQ队列状态"""
        self._update_config_vars()  # 确保使用最新的配置
        if not self.config_vars["host"] or not self.config_vars["queue"]:
            messagebox.showerror("配置错误", "请确保主机地址和队列名称已填写")
            return
        try:
            # 创建临时连接检查队列
            credentials = pika.PlainCredentials(self.config_vars["username"], self.config_vars["password"])

            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.config_vars["host"],
                    port=int(self.config_vars["port"]),
                    virtual_host=self.config_vars.get("virtual_host", "/"),
                    credentials=credentials,
                )
            )

            channel = connection.channel()

            try:
                # 检查队列是否存在
                queue_info = channel.queue_declare(queue=self.config_vars["queue"], passive=True)

                # 显示队列信息
                queue_status = (
                    f"队列存在\n"
                    f"消息数: {queue_info.method.message_count}\n"
                    f"消费者数: {queue_info.method.consumer_count}\n"
                    # f"持久化: {'是' if queue_info.method.durable else '否'}"
                )

                messagebox.showinfo("队列状态", queue_status)
            except Exception as e:
                messagebox.showerror("队列检查错误", f"无法检查队列状态: {str(e)}")

            except pika.exceptions.ChannelClosedByBroker as e:
                if e.reply_code == 404:  # 队列不存在
                    messagebox.showinfo("队列状态", "队列不存在")
                else:
                    messagebox.showerror("队列检查错误", f"错误代码: {e.reply_code}\n错误信息: {e.reply_text}")

            finally:
                connection.close()

        except Exception as e:
            messagebox.showerror("连接错误", f"无法连接到RabbitMQ服务器: {str(e)}")

    def update_status(self, status: str):
        """更新服务状态"""
        self.config_vars["status"].set(status)


# 注册配置页面
MainWindow.register_config_tab(UITableType.RECV, RMQConfigTab)
