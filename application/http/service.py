import asyncio
import threading
from aiohttp import web
from datetime import datetime
from core.message_bus import MessageBus


class HTTPServer(threading.Thread):
    def __init__(self, config: dict):
        super().__init__(daemon=True)
        self.config = config
        self.message_bus = MessageBus()
        self._stop_event = threading.Event()
        self.server = None
        self.runner = None
        
    def stop(self):
        """停止HTTP服务器"""
        self._stop_event.set()
        
    async def handle_request(self, request):
        """处理HTTP请求"""
        try:
            client_ip = request.remote
            post_data = await request.read()
            content_type = request.content_type
            if not post_data:
                return web.Response(text="No data received", status=400)
            
            # 发布消息到消息总线
            message = {
                "source": "HTTP",
                "config_name": self.config['name'],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip": client_ip,
                "url": f"http://{self.config['host']}:{self.config['port']}/alarm",
                "content_type": content_type,
                "raw_data": post_data
            }
            self.message_bus.publish("message.received", message)
                
            return web.Response(text="OK", status=200)
            
        except Exception as e:
            error_message = {
                "source": "HTTP",
                "config_name": self.config['name'],
                "type": "error",
                "error": str(e)
            }
            self.message_bus.publish("service.status", error_message)
            return web.Response(text=str(e), status=500)
    
    def run(self):
        """启动HTTP服务器"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            app = web.Application()
            app.router.add_post("/httpalarm", self.handle_request)
            
            self.runner = web.AppRunner(app)
            loop.run_until_complete(self.runner.setup())
            
            self.server = web.TCPSite(
                self.runner, 
                self.config['host'], 
                self.config['port']
            )
            loop.run_until_complete(self.server.start())
            
            self.message_bus.publish("service.status", {
                "source": "HTTP",
                "config_name": self.config['name'],
                "status": "运行中"
            })
            
            while not self._stop_event.is_set():
                loop.run_until_complete(asyncio.sleep(0.1))
                
        except Exception as e:
            self.message_bus.publish("service.status", {
                "source": "HTTP",
                "config_name": self.config['name'],
                "status": f"错误: {str(e)}"
            })
            
        finally:
            if self.runner:
                loop.run_until_complete(self.runner.cleanup())
            loop.close()
            
            self.message_bus.publish("service.status", {
                "source": "HTTP",
                "config_name": self.config['name'],
                "status": "已停止"
            })