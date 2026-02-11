#!/usr/bin/env python3
"""
测试图片弹窗的缩放和移动功能
"""

import tkinter as tk
import os
from PIL import Image, ImageDraw

# 添加项目路径到Python路径
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.image_popup import ImagePopup


def create_test_image():
    """创建一个测试图片"""
    # 创建一个简单的测试图片
    width, height = 800, 600
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    # 绘制一些测试图形
    draw.rectangle([100, 100, 300, 300], outline="red", width=3)
    draw.ellipse([400, 200, 600, 400], outline="blue", width=3)
    draw.text((50, 50), "测试图片 - Ctrl+滚轮缩放，Ctrl+鼠标移动", fill="black")

    # 保存图片
    test_image_path = "test_image.png"
    image.save(test_image_path)
    return test_image_path


def main():
    """主测试函数"""
    # 创建主窗口
    root = tk.Tk()
    root.title("图片弹窗测试")
    root.geometry("400x300")

    # 创建测试图片
    test_image_path = create_test_image()

    # 创建图片弹窗实例
    image_popup = ImagePopup(root)

    def show_popup():
        """显示图片弹窗"""
        image_info = {
            "filename": test_image_path,
            "targetList": [
                {
                    "rect": {"x": 0.125, "y": 0.167, "width": 0.25, "height": 0.333},
                    "marks": [{"name": "类型", "value": "矩形"}, {"name": "置信度", "value": "0.95"}],
                },
                {
                    "rect": {"x": 0.5, "y": 0.333, "width": 0.25, "height": 0.333},
                    "marks": [{"name": "类型", "value": "圆形"}, {"name": "置信度", "value": "0.88"}],
                },
            ],
        }
        image_popup.show(image_info)

    # 创建测试按钮
    test_button = tk.Button(root, text="打开图片弹窗", command=show_popup, font=("Arial", 14), padx=20, pady=10)
    test_button.pack(expand=True)

    # 添加使用说明
    instruction_label = tk.Label(
        root,
        text="使用说明：\n"
        "1. 点击按钮打开图片弹窗\n"
        "2. 按住Ctrl键 + 鼠标滚轮：放大/缩小图片\n"
        "3. 按住Ctrl键 + 鼠标拖动：移动图片\n"
        "4. 侧边栏可以切换显示不同的检测目标",
        font=("Arial", 10),
        justify=tk.LEFT,
        pady=20,
    )
    instruction_label.pack()

    def cleanup():
        """清理资源"""
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", cleanup)

    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()
