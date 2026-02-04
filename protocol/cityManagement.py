# 渣土车报警协议
import json
from typing import Optional
from datetime import datetime
from core.protocol_parser import BaseAlarmParser, ParserRegistry, ImageInfoType


class CityManagement(BaseAlarmParser):
    """TestAlarm协议解析器"""

    def extra_parse(self, serial_root) -> dict:
        """解析HTTP请求内容"""
        try:
            result_list = serial_root.get("Result")
            if result_list and isinstance(result_list, list) and len(result_list) > 0:
                result = result_list[0]
                if isinstance(result, dict):
                    sub_event = result.get("subEventType")

            return {"sub_event": sub_event}
        except Exception as e:
            return {"sub_event": "Parse Error"}

    def extract_image_info(self, parsed_data: dict) -> Optional[ImageInfoType]:
        try:
            json_data = json.loads(parsed_data["raw_content"])
            url = json_data["CommonBackgroundImage"]["resourcesContent"]

            if url is None:
                raise ValueError("No image URL found")
            rectList = []
            for result in json_data["Result"]:
                for target in result["Target"]:
                    rectInfo = {
                        "rect": target["Rect"],
                        "marks": [
                            {"name": "targetID", "value": target["targetID"]},
                        ],
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


ParserRegistry.register("cityManagement", CityManagement)
