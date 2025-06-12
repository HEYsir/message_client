from tkinter import *
from tkinter import ttk
import pika
from tkinter import messagebox
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow
from application.rmq.service import RabbitMQConsumer

class RMQConfigTab(BaseConfigTab):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rabbitmq_consumer = None  # 用于管理 Server 实例

    @classmethod
    def get_tab_name(cls) -> str:
        return "RMQ 服务"
    
    def _init_config_vars(self):
        """初始化配置变量"""
        super()._init_config_vars()
        self.rabbitmq_config = {
            "name": "RabbitMQ服务",
            "host": "10.41.131.252",
            "port": 5672,
            "virtual_host": "/",
            "username": "admin",
            "password": "backend15",
            "queue": "test",
            "durable": False,
            "status": "已停止"
        }
    
    def create_tab_content(self):
        """设置RabbitMQ服务标签页 - 优化高度匹配"""
        self.style = ttk.Style()
        self.style.configure('green.TFrame', background='green')
        # frame = ttk.Frame(self.frame, style='green.TFrame')
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10)

        # 主机地址
        ttk.Label(frame, text="主机地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.rmq_host_entry = ttk.Entry(frame)
        self.rmq_host_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.rmq_host_entry.insert(0, self.rabbitmq_config["host"])
        
        ttk.Label(frame, text="端口:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.rmq_port_entry = ttk.Entry(frame)
        self.rmq_port_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.rmq_port_entry.insert(0, str(self.rabbitmq_config["port"]))
        
        ttk.Label(frame, text="虚拟主机:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.rmq_vhost_entry = ttk.Entry(frame)
        self.rmq_vhost_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.rmq_vhost_entry.insert(0, self.rabbitmq_config["virtual_host"])

        ttk.Label(frame, text="队列名称:").grid(row=1, column=4, padx=5, pady=0, sticky="e")
        self.rmq_queue_entry = ttk.Entry(frame)
        self.rmq_queue_entry.grid(row=1, column=5, padx=5, pady=0, sticky="w")
        self.rmq_queue_entry.insert(0, self.rabbitmq_config["queue"])
        
        # 用户名
        ttk.Label(frame, text="用户名:").grid(row=1, column=0, padx=5, pady=0, sticky="e")
        self.rmq_user_entry = ttk.Entry(frame)
        self.rmq_user_entry.grid(row=1, column=1, padx=5, pady=0, sticky="w")
        self.rmq_user_entry.insert(0, self.rabbitmq_config["username"])
        
        # 密码
        ttk.Label(frame, text="密码:").grid(row=1, column=2, padx=5, pady=0, sticky="e")
        self.rmq_pass_entry = ttk.Entry(frame, show="*")
        self.rmq_pass_entry.grid(row=1, column=3, padx=5, pady=0, sticky="ew")
        self.rmq_pass_entry.insert(0, self.rabbitmq_config["password"])
        
        # 持久化队列
        self.rmq_durable_var = BooleanVar(value=self.rabbitmq_config["durable"])
        ttk.Checkbutton(
            frame, 
            text="持久化队列", 
            variable=self.rmq_durable_var
        ).grid(row=1, column=6, padx=5, pady=0, sticky="w")
        
        # 操作按钮
        btn_frame = Frame(frame)
        btn_frame.grid(row=1, column=6, columnspan=4, sticky="e", padx=5, pady=0)
        
        self.start_btn = ttk.Button(
            btn_frame, 
            text="启动消费" if self.rabbitmq_config["status"] != "运行中" else "停止消费",
            width=10,
            command=self._toggle_service
        )
        self.start_btn.pack(side=LEFT, padx=5)
        
        check_btn = ttk.Button(
            btn_frame, 
            text="检查队列", 
            width=10,
            command=self.check_rmq_queue
        )
        check_btn.pack(side=LEFT, padx=5)

    
    def _toggle_service(self):
        """切换服务状态"""
        if self.config_vars["status"].get() == "运行中":
            self.config_vars["status"].set("已停止")
            self.start_btn.config(text="启动服务")
        else:
            self.config_vars["status"].set("运行中")
            self.start_btn.config(text="停止服务")
        if self.rabbitmq_consumer and self.rabbitmq_consumer.is_alive():
            # 停止消费者
            self.rabbitmq_consumer.stop()
            self.rabbitmq_consumer = None
            self.rabbitmq_config["status"] = "已停止"
            self.start_btn.config(text="启动消费")
        else:
            # 启动消费者
            self.rabbitmq_consumer = RabbitMQConsumer(self.rabbitmq_config)
            self.rabbitmq_consumer.start()
            self.rabbitmq_config["status"] = "启动中"

    def check_rmq_queue(self):
        """检查RabbitMQ队列状态"""
        self.update_rmq_config()
        config = self.rabbitmq_config
        
        try:
            # 创建临时连接检查队列
            credentials = pika.PlainCredentials(
                config['username'], 
                config['password']
            )
            
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=config['host'],
                    port=int(config['port']),
                    virtual_host=config.get('virtual_host', '/'),
                    credentials=credentials
                )
            )
            
            channel = connection.channel()
            
            try:
                # 检查队列是否存在
                queue_info = channel.queue_declare(
                    queue=config['queue'], 
                    passive=True
                )
                
                # 显示队列信息
                queue_status = (
                    f"队列存在\n"
                    f"消息数: {queue_info.method.message_count}\n"
                    f"消费者数: {queue_info.method.consumer_count}\n"
                    f"持久化: {'是' if queue_info.method.durable else '否'}"
                )
                
                messagebox.showinfo("队列状态", queue_status)
                
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
MainWindow.register_config_tab(RMQConfigTab)
