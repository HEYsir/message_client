import threading
import pika
from core.message_bus import MessageBus
from core.protocol_parser import ParserRegistry
from core.image_handler import ImageHandler

class RabbitMQConsumer(threading.Thread):
    def __init__(self, config: dict):
        super().__init__(daemon=True)
        self.config = config
        self.message_bus = MessageBus()
        self.image_handler = ImageHandler(config.get('download_dir', './downloads'))
        self._stop_event = threading.Event()
        
    def stop(self):
        self._stop_event.set()
        
    def run(self):
        try:
            credentials = pika.PlainCredentials(
                self.config['username'],
                self.config['password']
            )
            
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.config['host'],
                    port=int(self.config['port']),
                    virtual_host=self.config.get('virtual_host', '/'),
                    credentials=credentials
                )
            )
            
            channel = connection.channel()
            
            def callback(ch, method, properties, body):
                # 获取对应的解析器
                parser = ParserRegistry.get_parser(self.config.get('protocol', 'hikvision'))
                if parser:
                    # 解析消息
                    parsed_data = parser.parse(body)
                    
                    # 提取图片信息
                    image_info = parser.extract_image_info(parsed_data)
                    if image_info:
                        self.image_handler.async_download(
                            image_info['url'],
                            image_info['filename']
                        )
                    
                    # 发布消息到消息总线
                    message = {
                        "source": "RabbitMQ",
                        "config_name": self.config['name'],
                        "timestamp": parsed_data['timestamp'],
                        "parsed_data": parsed_data,
                        "raw_data": body
                    }
                    self.message_bus.publish("message.received", message)
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
            channel.basic_consume(
                queue=self.config['queue'],
                on_message_callback=callback
            )
            
            channel.start_consuming()
            
        except Exception as e:
            error_message = {
                "source": "RabbitMQ",
                "config_name": self.config['name'],
                "type": "error",
                "error": str(e)
            }
            self.message_bus.publish("service.status", error_message)