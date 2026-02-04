# 攀高报警
import json
from typing import Optional
from datetime import datetime
from core.protocol_parser import ProtocolParser, ParserRegistry, ImageInfoType


class AdvReachHeightParser(ProtocolParser):
    """TestAlarm协议解析器"""

    def parse(self, content_type, data) -> dict:
        """解析HTTP请求内容"""
        try:
            if content_type != "application/json":
                raise ValueError("Unsupported content type")

            json_data = json.loads(data)
            event_type = json_data.get("eventType", json_data.get("event_type", "N/A"))
            timestamp = json_data.get("dateTime", json_data.get("timestamp", datetime.now().isoformat()))

            return {
                "type": "JSON",
                "event_type": event_type,
                "timestamp": timestamp,
                "raw_content": data,
            }
        except Exception as e:
            return {
                "error": str(e),
                "type": "unknown",
                "event_type": "Parse Error",
                "timestamp": datetime.now().isoformat(),
            }

    def extract_image_info(self, parsed_data: dict) -> Optional[ImageInfoType]:
        print(parsed_data)
        try:
            json_data = json.loads(parsed_data["raw_content"])
            print(json_data)
            url = json_data["AdvReachHeight"]["BackgroundImage"]["resourcesContent"]

            if url is None:
                raise ValueError("No image URL found")
            rectList = []
            for target in json_data["AdvReachHeight"]["humanInfo"]:
                rectInfo = {
                    "rect": target["humanRect"],
                    "marks": [{"name": "targetID", "value": target.get("targetID")}],
                }
                rectList.append(rectInfo)

            # 生成唯一的文件名
            import uuid

            filename = f"image_{uuid.uuid4().hex[:8]}_{parsed_data['timestamp'].replace(':', '').replace('-', '')}.jpg"
            return {
                "url": url,
                "filename": filename,
                "targetList": rectList,
            }
        except Exception as e:
            print(f"提取图片信息失败: {e}")
        return None


ParserRegistry.register("advReachHeight", AdvReachHeightParser)
