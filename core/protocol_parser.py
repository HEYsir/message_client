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

    def extract_image_info(self, parsed_data: dict) -> Optional[ImageInfoType]:
        """提取图片信息"""
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
        try:
            if content_type == "application/xml":
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

                return {
                    "type": "XML",
                    "event_type": event_type,
                    "timestamp": timestamp,
                    "raw_content": data,
                }
            else:
                # elif content_type == "application/json":
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
                target_info_list.append(target_info)
            return target_info_list

        except Exception as e:
            print(f"解析目标信息失败: {e}")
            return None

    def extract_image_info(self, parsed_data: dict) -> Optional[ImageInfoType]:
        print("parsed_data")
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
