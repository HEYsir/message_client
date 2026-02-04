import sys
import os
import importlib
from typing import Dict, Type, Optional, TypedDict, List
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


class RectType(TypedDict):
    """矩形标注数据类型"""

    x: float
    y: float
    width: float
    height: float


class MarkType(TypedDict):
    """标记项数据类型"""

    name: str
    value: str


class CoordinateType(TypedDict):
    """坐标点数据类型"""

    x: int
    y: int


class targetType(TypedDict):
    rect: Optional[RectType]
    CoordinateList: Optional[List[CoordinateType]]
    marks: Optional[List[MarkType]]


class ImageInfoType(TypedDict):
    """标注数据类型"""

    url: str
    filename: str
    targetList: List[targetType]


class ProtocolParser:
    """协议解析器基类"""

    def __init__(self):
        self.content_type = ""

    def parse(self, content_type, content: bytes) -> dict:
        """解析消息内容"""
        raise NotImplementedError

    def extra_parse(self, serial_root) -> dict:
        """解析消息内容"""
        raise NotImplementedError

    def extract_image_info_list(self, parsed_data: dict) -> List[Optional[ImageInfoType]]:
        """提取所有图片信息列表"""
        # 默认实现，返回单个图片的列表
        image_info = self.extract_image_info(parsed_data)
        if image_info:
            return [image_info]
        return []


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
        if parser_class is None:
            parser_class = cls._parsers.get("basealarm")
        if parser_class:
            return parser_class()
        return None


class BaseAlarmParser(ProtocolParser):
    """TestAlarm协议解析器"""

    def parse(self, content_type, data) -> dict:
        """解析HTTP请求内容"""
        self.content_type = content_type
        type = "unknown"
        event_type = "Parse Error"
        try:
            if content_type == "application/xml":
                type = "XML"
                root = ET.fromstring(data)
                ns = {"ns": "http://www.isapi.org/ver20/XMLSchema"}

                # 提取事件类型
                event_type_elem = root.find(".//ns:eventType", ns)
                if event_type_elem is None:
                    event_type_elem = root.find(".//eventType")
                event_type = event_type_elem.text if event_type_elem is not None else "N/A"

                # 提取时间戳
                timestamp_elem = root.find(".//ns:dateTime", ns)
                if timestamp_elem is None:
                    timestamp_elem = root.find(".//dateTime")

                if timestamp_elem is None:
                    timestamp_elem = root.find(".//ns:timeStamp", ns) or root.find(".//timeStamp")

                timestamp = timestamp_elem.text if timestamp_elem is not None else datetime.now().isoformat()
            else:
                type = "JSON"
                root = json.loads(data)
                event_type = root.get("eventType", root.get("event_type", "N/A"))
                timestamp = root.get("dateTime", root.get("timestamp", datetime.now().isoformat()))
            sub_type = self.extra_parse(root)
            return {
                "type": type,
                "event_type": event_type,
                "timestamp": timestamp,
                "raw_content": data,
            } | sub_type
        except Exception as e:
            return {
                "error": str(e),
                "type": type,
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "raw_content": data,
            }

    def extra_parse(self, serial_root) -> dict:
        return {}

    # 周界、室内目标识别
    def get_identify_info(self, content: str) -> List[MarkType]:
        mark_list = []
        try:
            root = ET.fromstring(content)
            ns = {"ns": "http://www.isapi.org/ver20/XMLSchema"}

            # 查找DetectionRegionEntry
            human_entry_list = root.findall(".//ns:humanInfoList", ns)
            if human_entry_list is None:
                return mark_list

            # 解析区域信息
            for human_entry in human_entry_list:
                target_info = {}
                # 解析TargetRect
                identify_list = human_entry.find(".//ns:identifyList", ns)
                if identify_list is None:
                    continue
                for identify_elem in identify_list:
                    # 获取positionX和positionY
                    candidate_list = identify_elem.find(".//ns:candidateList", ns)
                    if candidate_list is None:
                        continue
                    for candidate_elem in candidate_list:
                        FDID = candidate_elem.find(".//ns:FDID", ns)
                        similarity = candidate_elem.find(".//ns:similarity", ns)
                        if FDID is None or similarity is None:
                            continue
                        mark_list.append({"name": "人脸ID", "value": FDID.text})
                        mark_list.append({"name": "相似度", "value": similarity.text})
            return mark_list

        except Exception as e:
            print(f"解析目标信息失败: {e}")
            return []

    def get_target_info(self, content: str) -> Optional[targetType]:
        """
        解析获取RegionCoordinatesList中的坐标点信息

        XML结构示例：
        <DetectionRegionList>
            <DetectionRegionEntry>
                <regionID>2</regionID>
                <sensitivityLevel>0</sensitivityLevel>
                <RegionCoordinatesList>
                    <RegionCoordinates>
                        <positionX>341</positionX>
                        <positionY>681</positionY>
                    </RegionCoordinates>
                    <RegionCoordinates>
                        <positionX>626</positionX>
                        <positionY>681</positionY>
                    </RegionCoordinates>
                    <RegionCoordinates>
                        <positionX>341</positionX>
                        <positionY>987</positionY>
                    </RegionCoordinates>
                    <RegionCoordinates>
                        <positionX>626</positionX>
                        <positionY>987</positionY>
                    </RegionCoordinates>
                </RegionCoordinatesList>
                <detectionTarget>human</detectionTarget>
                <TargetRect>
                    <X>0.342</X>
                    <Y>0.681</Y>
                    <width>0.285</width>
                    <height>0.306</height>
                </TargetRect>
                <sceneID>0</sceneID>
                <isRegionCoordinatesListChange>false</isRegionCoordinatesListChange>
            </DetectionRegionEntry>
        </DetectionRegionList>
        """
        try:
            root = ET.fromstring(content)
            ns = {"ns": "http://www.isapi.org/ver20/XMLSchema"}

            # 查找DetectionRegionEntry
            detection_region_entry_list = root.findall(".//ns:DetectionRegionEntry", ns)
            if detection_region_entry_list is None:
                # 尝试不使用命名空间
                detection_region_entry_list = root.findall(".//DetectionRegionEntry")

            if detection_region_entry_list is None:
                return None

            # 解析区域信息
            target_info_list = []
            for detection_region_entry in detection_region_entry_list:
                target_info = {}
                # 解析TargetRect
                target_rect_elem = detection_region_entry.find(".//ns:TargetRect", ns)
                if target_rect_elem is None:
                    target_rect_elem = detection_region_entry.find(".//TargetRect")
                if target_rect_elem is not None:
                    target_rect = {}

                    # 获取X坐标
                    x_elem = target_rect_elem.find(".//ns:X", ns)
                    if x_elem is None:
                        x_elem = target_rect_elem.find(".//X")
                    target_rect["x"] = float(x_elem.text) if x_elem is not None else 0.0

                    # 获取Y坐标
                    y_elem = target_rect_elem.find(".//ns:Y", ns)
                    if y_elem is None:
                        y_elem = target_rect_elem.find(".//Y")
                    target_rect["y"] = float(y_elem.text) if y_elem is not None else 0.0

                    # 获取width
                    width_elem = target_rect_elem.find(".//ns:width", ns)
                    if width_elem is None:
                        width_elem = target_rect_elem.find(".//width")
                    target_rect["width"] = float(width_elem.text) if width_elem is not None else 0.0

                    # 获取height
                    height_elem = target_rect_elem.find(".//ns:height", ns)
                    if height_elem is None:
                        height_elem = target_rect_elem.find(".//height")
                    target_rect["height"] = float(height_elem.text) if height_elem is not None else 0.0

                    target_info["rect"] = target_rect

                # 解析RegionCoordinatesList中的坐标点
                region_coordinates_list = detection_region_entry.find(".//ns:RegionCoordinatesList", ns)
                if region_coordinates_list is None:
                    region_coordinates_list = detection_region_entry.find(".//RegionCoordinatesList")
                if region_coordinates_list is not None:
                    coordinates = []
                    # 查找所有RegionCoordinates节点
                    region_coordinates = region_coordinates_list.findall(".//ns:RegionCoordinates", ns)
                    if not region_coordinates:
                        region_coordinates = region_coordinates_list.findall(".//RegionCoordinates")

                    for coord_elem in region_coordinates:
                        # 获取positionX和positionY
                        position_x_elem = coord_elem.find(".//ns:positionX", ns)
                        if position_x_elem is None:
                            position_x_elem = coord_elem.find(".//positionX")

                        position_y_elem = coord_elem.find(".//ns:positionY", ns)
                        if position_y_elem is None:
                            position_y_elem = coord_elem.find(".//positionY")

                        if position_x_elem is None or position_y_elem is None:
                            continue
                        coordinates.append(
                            {
                                "x": int(position_x_elem.text),
                                "y": int(position_y_elem.text),
                            }
                        )
                    target_info["CoordinateList"] = coordinates

                regionID = detection_region_entry.find(".//ns:regionID", ns)
                target_info["marks"] = [{"name": "检测区域", "value": regionID.text}]

                mark_list = self.get_identify_info(content)
                target_info["marks"].extend(mark_list)

                target_info_list.append(target_info)
            return target_info_list

        except Exception as e:
            print(f"解析目标信息失败: {e}")
            return None

    def extract_image_info(self, parsed_data: dict) -> Optional[ImageInfoType]:
        """提取图片信息，自动判断raw_content是XML还是JSON格式"""
        try:
            raw_content = parsed_data["raw_content"]

            # 判断raw_content是XML还是JSON格式
            content_type = self._detect_content_type(raw_content)

            if content_type == "XML":
                return self._extract_image_info_from_xml(parsed_data)
            elif content_type == "JSON":
                return self._extract_image_info_from_json(parsed_data)
            else:
                print(f"无法识别的格式: {content_type}")
                return None

        except Exception as e:
            print(f"提取图片信息失败: {e}")
        return None

    def _detect_content_type(self, raw_content: bytes) -> str:
        """检测raw_content的数据格式是XML还是JSON"""
        try:
            content_str = raw_content.decode("utf-8", errors="ignore").strip()

            # 检查是否是XML格式
            if content_str.startswith("<?xml") or content_str.startswith("<"):
                try:
                    ET.fromstring(content_str)
                    return "XML"
                except ET.ParseError:
                    pass

            # 检查是否是JSON格式
            if content_str.startswith("{") or content_str.startswith("["):
                try:
                    json.loads(content_str)
                    return "JSON"
                except json.JSONDecodeError:
                    pass

            # 如果都无法解析，尝试根据内容特征判断
            if "<" in content_str and ">" in content_str:
                return "XML"
            elif "{" in content_str and "}" in content_str:
                return "JSON"
            else:
                return "UNKNOWN"

        except Exception as e:
            print(f"检测内容格式失败: {e}")
            return "UNKNOWN"

    def _extract_image_info_from_xml(self, parsed_data: dict) -> Optional[ImageInfoType]:
        """从XML格式中提取图片信息"""
        try:
            root = ET.fromstring(parsed_data["raw_content"])
            ns = {"ns": "http://www.isapi.org/ver20/XMLSchema"}

            url = root.find(".//ns:visibleLightURL", ns)
            if url is None:
                # 尝试不使用命名空间
                url = root.find(".//visibleLightURL")
            if url is None:
                url = root.find(".//ns:bkgUrl", ns)
                if url is None:
                    url = root.find(".//bkgUrl")
            if url is not None and url.text:
                # 生成唯一的文件名
                import uuid

                filename = (
                    f"image_{uuid.uuid4().hex[:8]}_{parsed_data['timestamp'].replace(':', '').replace('-', '')}.jpg"
                )
                return {
                    "url": url.text,
                    "filename": filename,
                    "targetList": self.get_target_info(parsed_data["raw_content"]),
                }
        except Exception as e:
            print(f"从XML提取图片信息失败: {e}")
        return None

    def _extract_image_info_from_json(self, parsed_data: dict) -> Optional[ImageInfoType]:
        """从JSON格式中提取图片信息"""
        # 转换为大驼峰（帕斯卡命名法）
        event_type_camelCase = parsed_data["event_type"]
        event_type = event_type_camelCase[0].upper() + event_type_camelCase[1:]
        try:
            json_data = json.loads(parsed_data["raw_content"])
            event_json = json_data.get(event_type)
            url = event_json["BackgroundImage"]["resourcesContent"]

            if url is None:
                raise ValueError("No image URL found")
            rectList = []
            target_key, rect_key = (
                ("humanInfo", "humanRect") if "humanInfo" in event_json else ("targetList", "targetRect")
            )
            for target in event_json[target_key]:
                rectInfo = {
                    "rect": target[rect_key],
                    "marks": [],
                }
                if "targetID" in target:
                    rectInfo["marks"].append({"name": "targetID", "value": target["targetID"]})

                rectList.append(rectInfo)

            # 生成唯一的文件名
            import uuid

            timestamp = event_json["timeStamp"] if "timeStamp" in event_json else parsed_data["timestamp"]
            filename = f"image_{uuid.uuid4().hex[:8]}_{timestamp.replace(':', '').replace('-', '')}.jpg"
            return {
                "url": url,
                "filename": filename,
                "targetList": rectList,
            }
        except Exception as e:
            print(f"提取图片信息失败: {e}")
        return None


# 注册解析器
ParserRegistry.register("basealarm", BaseAlarmParser)


def discover_protocol():
    """自动发现并导入所有协议，兼容cx_Freeze打包路径"""
    # 1. 优先用 sys._MEIPASS（PyInstaller），2. 用 sys.executable 目录（cx_Freeze），3. 用 __file__ 目录（源码）
    if hasattr(sys, "_MEIPASS"):
        protocol_path = Path(sys._MEIPASS) / "protocol"
    else:
        print(f"froze:{getattr(sys, "frozen", False)}")
        if getattr(sys, "frozen", False):
            print(sys.executable)
            base_dir = Path(sys.executable).parent
            protocol_path = base_dir / "lib/protocol"
        else:
            print(Path(__file__))
            base_dir = Path(__file__).resolve().parent.parent
            protocol_path = Path(base_dir) / "protocol"

    print(f"[discover_protocol] search protocol dir: {protocol_path}")
    if not os.path.exists(protocol_path):
        print(f"Warning: protocol directory not found at {protocol_path}")
        return
    for item in os.listdir(protocol_path):
        module_name = os.path.splitext(item)[0]
        module_path = f"protocol.{module_name}"
        print(f"[discover_protocol] Try import: {module_path}")
        try:
            importlib.import_module(module_path)
            print(f"[discover_protocol] Successfully imported: {module_path}")
        except (ImportError, SyntaxError) as e:
            print(f"Error: Could not load config tab from {module_path}: {e}")


discover_protocol()
