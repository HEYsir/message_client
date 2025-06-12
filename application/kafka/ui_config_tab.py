from tkinter import *
from tkinter import ttk
from ui.base_tab import BaseConfigTab
from ui.main_window import MainWindow
from application.kafka.service import KafkaConsumer

class KafkaConfigTab(BaseConfigTab):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kafka_consumer = None  # 用于管理 Server 实例
    
    @classmethod
    def get_tab_name(cls) -> str:
        return "Kafka 消费"
    
    def _init_config_vars(self):
        """初始化配置变量"""
        super()._init_config_vars()

        self.kafka_config = {
            "name": "Kafka服务",
            "bootstrap_servers": "10.41.63.199:9092",
            "topics": "STATIC_HUMAN_EXCEPTION_TOPIC",
            "group_id": "test123456789",
            "auto_offset_reset": "earliest",
            "sasl_username": "",
            "sasl_password": "",
            "ssl_ca_location": "",
            "download_dir": "./kafka_downloads",
            "kafka_ssl_entry":"",
            "status": "已停止"
        }
    
    def create_tab_content(self):
        """创建Kafka服务配置界面"""
        # 主框架
        self.style = ttk.Style()
        self.style.configure('Red.TFrame', background='red')
        # 使用自定义样式创建main_frame
        # frame = ttk.Frame(self.frame, style='Red.TFrame')
        frame = ttk.Frame(self.frame)
        frame.pack(fill="both", padx=10)

        # 服务地址
        ttk.Label(frame, text="服务地址:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.kafka_servers_entry = ttk.Entry(frame)
        self.kafka_servers_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.kafka_servers_entry.insert(0, self.kafka_config["bootstrap_servers"])

        # 主题
        ttk.Label(frame, text="主题:").grid(row=1, column=0, padx=5, pady=0, sticky="e")
        self.kafka_topics_entry = ttk.Entry(frame)
        self.kafka_topics_entry.grid(row=1, column=1, padx=5, pady=(0,5), sticky="ew")
        self.kafka_topics_entry.insert(0, self.kafka_config["topics"])

        # SASL认证勾选框
        self.sasl_checkbox_var = BooleanVar(value=False)
        self.sasl_checkbox = ttk.Checkbutton(
            frame, text="SASL认证", variable=self.sasl_checkbox_var, command=self.toggle_sasl_fields
        )
        self.sasl_checkbox.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        # SASL用户名
        ttk.Label(frame, text="SASL用户名:").grid(row=0, column=3, padx=5, pady=5, sticky="e")
        self.kafka_user_entry = ttk.Entry(frame)
        self.kafka_user_entry.grid(row=0, column=4, padx=5, pady=5, sticky="ew")
        self.kafka_user_entry.insert(0, self.kafka_config.get("sasl_username", ""))
        # SASL密码
        ttk.Label(frame, text="SASL密码:").grid(row=1, column=3, padx=5, pady=0, sticky="e")
        self.kafka_pass_entry = ttk.Entry(frame, show="*")
        self.kafka_pass_entry.grid(row=1, column=4, padx=5, pady=0, sticky="ew")
        self.kafka_pass_entry.insert(0, self.kafka_config.get("sasl_password", ""))
        
        # TLS证书勾选框
        self.tls_checkbox_var = BooleanVar(value=False)
        self.tls_checkbox = ttk.Checkbutton(
            frame, text="TLS认证", variable=self.tls_checkbox_var, command=self.toggle_tls_fields
        )
        self.tls_checkbox.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        # SSL CA路径
        kafka_ssl_entry = ttk.Entry(frame, state='readonly')
        kafka_ssl_entry.grid(row=1, column=5, columnspan=2, padx=5, pady=5, sticky="ew")
        kafka_ssl_entry.insert(0, self.kafka_config.get("ssl_ca_location", ""))
        # 浏览按钮
        self.ssl_browse_btn = ttk.Button(
            frame, 
            text="CA路径", 
            width=8,
            command=lambda: self.browse_file(kafka_ssl_entry)
        )
        self.ssl_browse_btn.grid(row=0, column=6, padx=5, pady=0)
        
        # 操作按钮
        btn_frame = Frame(frame)
        btn_frame.grid(row=1, column=7, sticky="e", padx=5, pady=0)
        self.start_btn = ttk.Button(
            btn_frame, 
            text="启动消费" if self.kafka_config["status"] != "运行中" else "停止消费",
            width=10,
            command=self._toggle_service
        )
        self.start_btn.pack(side=LEFT, padx=5)
        
        # 初始隐藏SASL和TLS相关字段
        self.toggle_sasl_fields()
        self.toggle_tls_fields()

    def _toggle_service(self):
        """切换服务状态"""
        if self.kafka_consumer and self.kafka_consumer.is_alive():
            # 停止消费者
            self.kafka_consumer.stop()
            self.kafka_consumer = None
            self.kafka_config["status"] = "已停止"
            self.start_btn.config(text="启动消费")
        else:
            # 启动消费者
            self.kafka_consumer = KafkaConsumer(self.kafka_config)
            self.kafka_consumer.start()
            self.kafka_config["status"] = "运行中"
            self.start_btn.config(text="停止消费")
            
    def toggle_sasl_fields(self):
        """显示或隐藏SASL相关字段"""
        state = "normal" if self.sasl_checkbox_var.get() else "disabled"
        self.kafka_user_entry.config(state=state)
        self.kafka_pass_entry.config(state=state)

    def toggle_tls_fields(self):
        """显示或隐藏TLS相关字段"""
        state = "normal" if self.tls_checkbox_var.get() else "disabled"
        self.ssl_browse_btn.config(state=state)

    def update_status(self, status: str):
        """更新服务状态"""
        self.kafka_config["status"] = status
# 注册配置页面
MainWindow.register_config_tab(KafkaConfigTab)
