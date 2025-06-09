from typing import Dict, Type, Optional
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import uuid

class ProtocolParser:
    """协议解析器基类"""
    def parse(self, content: bytes) -> dict:
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

class HIKVisionParser(ProtocolParser):
    """海康威视协议解析器"""
    def parse(self, content: bytes) -> dict:
        try:
            # 尝试解析XML
            root = ET.fromstring(content)
            ns = {"ns": "http://www.isapi.org/ver20/XMLSchema"}
            
            event_type = root.find('.//ns:eventType', ns)
            task_id = root.find('.//ns:taskInfo/ns:taskID', ns)
            timestamp = root.find('.//ns:timeStamp', ns)
            
            return {
                "type": "XML",
                "protocol": "hikvision",
                "event_type": event_type.text if event_type is not None else "N/A",
                "task_id": task_id.text if task_id is not None else str(uuid.uuid4()),
                "timestamp": timestamp.text if timestamp is not None else datetime.now().isoformat(),
                "raw_content": content
            }
        except:
            return {
                "type": "ERROR",
                "protocol": "hikvision",
                "error": "Invalid XML format"
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
ParserRegistry.register("hikvision", HIKVisionParser)