from typing import Dict, Type, Optional
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import uuid

class ProtocolParser:
    """协议解析器基类"""
    def parse(self, content_type, content: bytes) -> dict:
        """解析消息内容"""
        raise NotImplementedError
        
    def extract_image_info(self, parsed_data: dict) -> Optional[dict]:
        """提取图片信息"""
        raise NotImplementedError

class ParserRegistry:
    """解析器注册中心"""
    _parsers: Dict[str, Type[ProtocolParser]] = {}
    
    @classmethod
    def register(cls, protocol: str, parser: Type[ProtocolParser]):
        """注册解析器"""
        cls._parsers[protocol] = parser
    
    @classmethod
    def get_parser(cls, protocol: str) -> Optional[ProtocolParser]:
        """获取解析器实例"""
        parser_class = cls._parsers.get(protocol)
        if parser_class:
            return parser_class()
        return None

class BaseAlarmParser(ProtocolParser):
    """TestAlarm协议解析器"""
    def parse(self, content_type, data) -> dict:
        """解析HTTP请求内容"""
        try:
            if content_type == "application/xml":
                root = ET.fromstring(data)
                ns = {'ns': 'http://www.isapi.org/ver20/XMLSchema'}
                
                # 提取事件类型
                event_type_elem = root.find('.//ns:eventType', ns)
                if event_type_elem is None:
                    event_type_elem = root.find('.//eventType')
                event_type = event_type_elem.text if event_type_elem is not None else "N/A"
                
                # 提取时间戳
                timestamp_elem = root.find('.//ns:dateTime', ns)
                if timestamp_elem is None:
                    timestamp_elem = root.find('.//dateTime')
                
                if timestamp_elem is None:
                    timestamp_elem = root.find('.//ns:timeStamp', ns) or root.find('.//timeStamp')
                
                timestamp = timestamp_elem.text if timestamp_elem is not None else datetime.now().isoformat()
                
                return {
                    "type": "XML",
                    "event_type": event_type,
                    "timestamp": timestamp,
                    "raw_content": data
                }
            
            elif content_type == "application/json":
                json_data = json.loads(data)
                event_type = json_data.get("eventType", json_data.get("event_type", "N/A"))
                timestamp = json_data.get("dateTime", json_data.get("timestamp", datetime.now().isoformat()))
                
                return {
                    "type": "JSON",
                    "event_type": event_type,
                    "timestamp": timestamp,
                    "raw_content": data
                }
        except Exception as e:
            return {
                "error": str(e),
                "type": "unknown",
                "event_type": "Parse Error",
                "timestamp": datetime.now().isoformat()
            }

    
    def extract_image_info(self, parsed_data: dict) -> Optional[dict]:
        try:
            root = ET.fromstring(parsed_data["raw_content"])
            ns = {"ns": "http://www.isapi.org/ver20/XMLSchema"}
            
            url = root.find('.//ns:visibleLightURL', ns)
            if url is not None:
                return {
                    "url": url.text,
                    "filename": f"{parsed_data['task_id']}_{parsed_data['timestamp']}.jpg"
                }
        except:
            pass
        return None

# 注册解析器
ParserRegistry.register("basealarm", BaseAlarmParser)