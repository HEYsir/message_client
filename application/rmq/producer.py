import pika
import json

class FastRMQProducer:
    """Reusable RabbitMQ producer utility (migrated from rmq_send.py)"""
    def __init__(self, host, port=5672, username=None, password=None, virtual_host='/', heartbeat=600, blocked_connection_timeout=300):
        if username:
            credentials = pika.PlainCredentials(username, password)
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=virtual_host,
                credentials=credentials,
                heartbeat=heartbeat,
                blocked_connection_timeout=blocked_connection_timeout
            )
        else:
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=virtual_host,
                heartbeat=heartbeat,
                blocked_connection_timeout=blocked_connection_timeout
            )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def send(self, queue, message, durable=True):
        if isinstance(message, (dict, list)):
            body = json.dumps(message).encode('utf-8')
        elif isinstance(message, str):
            body = message.encode('utf-8')
        else:
            body = message
        self.channel.queue_declare(queue=queue, durable=durable, exclusive=False, auto_delete=False)
        self.channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2 if durable else 1)
        )

    def close(self):
        if self.connection:
            self.connection.close()
