from confluent_kafka import Producer
import socket
import json

class FastKafkaProducer:
    """Reusable Kafka producer utility (migrated from kafka_producter.py)"""
    def __init__(self, bootstrap_servers, client_id=None, **kwargs):
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': client_id or socket.gethostname(),
        }
        self.config.update(kwargs)
        self.producer = Producer(self.config)

    def send(self, topic, value, key=None, on_delivery=None):
        if isinstance(value, (dict, list)):
            value = json.dumps(value).encode('utf-8')
        elif isinstance(value, str):
            value = value.encode('utf-8')
        self.producer.produce(
            topic=topic,
            key=key,
            value=value,
            callback=on_delivery
        )
        self.producer.poll(0)

    def flush(self):
        self.producer.flush()

    @staticmethod
    def default_delivery_report(err, msg):
        if err is not None:
            print(f'[Kafka] Delivery failed: {err}')
        else:
            print(f'[Kafka] Delivered to {msg.topic()} [{msg.partition()}] offset {msg.offset()}')
