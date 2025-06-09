from confluent_kafka import Consumer, KafkaException
import threading
from core.message_bus import MessageBus
from core.protocol_parser import ParserRegistry
from core.image_handler import ImageHandler

class KafkaConsumer(threading.Thread):
    def __init__(self, config: dict):
        super().__init__(daemon=True)
        self.config = config
        self.message_bus = MessageBus()
        self.image_handler = ImageHandler(config.get('download_dir', './downloads'))
        self._stop_event = threading.Event()
        self.consumer = None
        
    def stop(self):
        """停止消费者"""
        self._stop_event.set()
        if self.consumer:
            self.consumer.close()
            
    def run(self):
        """启动Kafka消费者"""
        try:
            # 创建消费者配置
            conf = {
                'bootstrap.servers': self.config['bootstrap_servers'],
                'group.id': self.config['group_id'],
                'auto.offset.reset': self.config['auto_offset_reset']
            }
            
            # 添加安全配置
            if self.config.get('sasl_username') and self.config.get('sasl_password'):
                conf.update({
                    'security.protocol': 'SASL_PLAINTEXT',
                    'sasl.mechanism': 'PLAIN',
                    'sasl.username': self.config['sasl_username'],
                    'sasl.password': self.config['sasl_password']
                })
                
            if self.config.get('ssl_ca_location'):
                conf['ssl.ca.location'] = self.config['ssl_ca_location']
                conf['security.protocol'] = 'SSL'
            
            # 创建消费者
            self.consumer = Consumer(conf)
            topics = [t.strip() for t in self.config['topics'].split(',')]
            self.consumer.subscribe(topics)
            
            self.message_bus.publish("service.status", {
                "source": "Kafka",
                "config_name": self.config['name'],
                "status": "运行中"
            })
            
            while not self._stop_event.is_set():
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaException._PARTITION_EOF:
                        continue
                    else:
                        self.message_bus.publish("service.status", {
                            "source": "Kafka",
                            "config_name": self.config['name'],
                            "status": f"错误: {msg.error()}"
                        })
                        continue
                
                # 获取对应的解析器
                parser = ParserRegistry.get_parser(self.config.get('protocol', 'hikvision'))
                if parser:
                    # 解析消息
                    parsed_data = parser.parse(msg.value())
                    
                    # 提取图片信息
                    image_info = parser.extract_image_info(parsed_data)
                    if image_info:
                        self.image_handler.async_download(
                            image_info['url'],
                            image_info['filename']
                        )
                    
                    # 发布消息到消息总线
                    message = {
                        "source": "Kafka",
                        "config_name": self.config['name'],
                        "timestamp": parsed_data['timestamp'],
                        "bootstrap_servers": self.config['bootstrap_servers'],
                        "topic": msg.topic(),
                        "partition": msg.partition(),
                        "offset": msg.offset(),
                        "parsed_data": parsed_data,
                        "raw_data": msg.value()
                    }
                    self.message_bus.publish("message.received", message)
                
        except Exception as e:
            self.message_bus.publish("service.status", {
                "source": "Kafka",
                "config_name": self.config['name'],
                "status": f"错误: {str(e)}"
            })
            
        finally:
            if self.consumer:
                self.consumer.close()
                
            self.message_bus.publish("service.status", {
                "source": "Kafka",
                "config_name": self.config['name'],
                "status": "已停止"
            })

