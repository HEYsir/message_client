from typing import Callable, Dict, List
import queue

class MessageBus:
    """消息总线，用于处理消息的发布和订阅"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageBus, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化消息总线"""
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_queue = queue.Queue()

    def subscribe(self, topic: str, callback: Callable) -> None:
        """订阅指定主题的消息"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """取消订阅指定主题的消息"""
        if topic in self.subscribers and callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)

    def publish(self, topic: str, message: dict) -> None:
        """发布消息到指定主题"""
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary")
        self.message_queue.put((topic, message))
        
    def process_messages(self) -> None:
        """处理队列中的消息"""
        while not self.message_queue.empty():
            topic, message = self.message_queue.get()
            if topic not in self.subscribers:
                continue
            for callback in self.subscribers[topic]:
                try:
                    callback(message)
                except Exception as e:
                    print(f"Error processing message: {e}")