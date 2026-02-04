# 渣土车报警协议
import json
from typing import Optional
from datetime import datetime
from core.protocol_parser import BaseAlarmParser, ParserRegistry, ImageInfoType


class MuckTruckParser(BaseAlarmParser):
    """TestAlarm协议解析器"""

    def extract_image_info(self, parsed_data: dict) -> Optional[ImageInfoType]:
        try:
            json_data = json.loads(parsed_data["raw_content"])
            url = json_data["MuckTruckTargetAnalysisEvent"]["analysisResultList"][0]["pictureFile"]["resourcesContent"]

            if url is None:
                raise ValueError("No image URL found")
            rectList = []
            for target in json_data["MuckTruckTargetAnalysisEvent"]["analysisResultList"][0]["targetList"]:
                if "yes" != target["muckTruck"]["valueString"]:
                    continue

                rectInfo = {
                    "rect": target["targetRect"],
                    "marks": [
                        {"name": "cover", "value": target["coverPlate"]["valueString"]},
                        {
                            "name": "Dirty",
                            "value": target["vehicleDirty"]["valueString"],
                        },
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


ParserRegistry.register("MuckTruckTargetAnalysisEvent", MuckTruckParser)
