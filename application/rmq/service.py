import threading
import pika
from datetime import datetime
from core.message_bus import MessageBus

class RabbitMQConsumer(threading.Thread):
    def __init__(self, config: dict):
        super().__init__(daemon=True)
        self.config = config
        self.message_bus = MessageBus()
        self._stop_event = threading.Event()
        self.consumer = None
        
    def stop(self):
        self._stop_event.set()
        
    def run(self):
        connection = None
        channel = None
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
                # 发布消息到消息总线
                message = {
                    "source":self.config['name'],
                    "timestamp": properties.timestamp.strftime("%Y-%m-%d %H:%M:%S") if properties.timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "content_type": properties.content_type,
                    "raw_data": body,
                    "rmq_extra" :{
                        "exchange": method.exchange,
                        "routing_key": method.routing_key,
                        "redelivered": method.redelivered,
                        "delivery_tag": method.delivery_tag,
                        "properties": {
                            "content_encoding": properties.content_encoding,
                            "headers": properties.headers,
                            "delivery_mode": properties.delivery_mode,
                            "priority": properties.priority,
                            "correlation_id": properties.correlation_id,
                            "reply_to": properties.reply_to,
                            "expiration": properties.expiration,
                            "message_id": properties.message_id,
                            "timestamp": properties.timestamp,
                            "type": properties.type,
                            "user_id": properties.user_id,
                            "app_id": properties.app_id,
                            "cluster_id": properties.cluster_id
                        },
                    },
                }
                self.message_bus.publish("message.received", message)
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
            channel.basic_consume(
                queue=self.config['queue'],
                on_message_callback=callback
            )
            channel.start_consuming()
            print("RabbitMQ consumer stopped.")
            
        except Exception as e:
            error_message = {
                "source": "RabbitMQ",
                "config_name": self.config['name'],
                "type": "error",
                "error": str(e)
            }
            self.message_bus.publish("service.status", error_message)
        finally:
            if channel:
                channel.close()
            if connection:
                connection.close()