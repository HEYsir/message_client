import tkinter as tk
from tkinter import ttk, PanedWindow, Frame, LEFT, RIGHT, VERTICAL, HORIZONTAL
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import re


class ImagePopup:
    """图片弹窗管理类"""

    def __init__(self, parent_window):
        """初始化图片弹窗

        Args:
            parent_window: 父窗口，用于弹窗定位和事件绑定
        """
        self.parent = parent_window
        self.popup = None
        self.current_popup_image = None
        self.popup_resize_timer = None
        self.selected_rect_index = None
        self.show_all_rects_flag = False
        self.current_rects = []

        # 创建弹窗
        self.create_popup()

    def create_popup(self):
        """创建图片弹窗窗口"""
        # 创建顶层窗口
        self.popup = tk.Toplevel(self.parent)
        self.popup.title("图片详情")
        self.popup.geometry("1200x800")
        self.popup.withdraw()  # 初始隐藏
        self.popup.minsize(800, 600)  # 设置最小尺寸

        # 创建主容器
        main_container = tk.Frame(self.popup)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建水平分割布局
        popup_paned = PanedWindow(main_container, orient=HORIZONTAL)
        popup_paned.pack(fill=tk.BOTH, expand=True)

        # 图片显示区域（左侧）- 可自适应大小
        popup_image_frame = ttk.LabelFrame(popup_paned, text="图片预览")
        popup_paned.add(popup_image_frame, minsize=400, stretch="always")

        # 创建图片显示容器
        image_container = tk.Frame(popup_image_frame)
        image_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 图片显示画布 - 用于自适应显示
        self.popup_image_canvas = tk.Canvas(image_container, bg="white", highlightthickness=0)
        self.popup_image_canvas.pack(fill=tk.BOTH, expand=True)

        # 在画布上创建图片显示区域
        self.popup_image_container = tk.Frame(self.popup_image_canvas, bg="white")
        self.popup_image_canvas.create_window(
            (0, 0), window=self.popup_image_container, anchor="nw", tags="image_window"
        )

        # 图片显示标签
        self.popup_image_label = tk.Label(
            self.popup_image_container,
            text="暂无图片",
            font=("Arial", 12),
            bg="white",
            relief="sunken",
        )
        self.popup_image_label.pack(fill=tk.BOTH, expand=True)

        # 图片信息标签
        self.popup_image_info_label = tk.Label(image_container, text="", font=("Arial", 10), fg="gray", bg="white")
        self.popup_image_info_label.pack(fill=tk.X, padx=10, pady=5)

        # 矩形框和标签侧边栏（右侧）- 固定大小
        self.create_rect_sidebar(popup_paned)

        # 关闭按钮
        close_button = ttk.Button(main_container, text="关闭", command=self.close)
        close_button.pack(side=tk.BOTTOM, pady=10)

        # 绑定窗口大小变化事件
        self.popup.bind("<Configure>", self.on_popup_resize)

        # 弹窗关闭事件
        self.popup.protocol("WM_DELETE_WINDOW", self.close)

    def create_rect_sidebar(self, parent):
        """创建矩形框和标签侧边栏"""
        sidebar_frame = ttk.LabelFrame(parent, text="检测目标列表")
        parent.add(sidebar_frame, minsize=250)

        # 控制按钮区域
        control_frame = ttk.Frame(sidebar_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # 显示全部按钮
        self.show_all_btn = ttk.Button(control_frame, text="显示全部", command=self.show_all_rects)
        self.show_all_btn.pack(side=LEFT, padx=2)

        # 隐藏全部按钮
        self.hide_all_btn = ttk.Button(control_frame, text="隐藏全部", command=self.hide_all_rects)
        self.hide_all_btn.pack(side=LEFT, padx=2)

        # 矩形框列表
        list_frame = ttk.Frame(sidebar_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=tk.Y)

        # 矩形框列表
        self.rect_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, yscrollcommand=scrollbar.set)
        self.rect_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.rect_listbox.yview)

        # 绑定选择事件
        self.rect_listbox.bind("<<ListboxSelect>>", self.on_rect_select)

    def update_rect_sidebar(self, image_info):
        """更新矩形框侧边栏"""
        # 清空当前列表
        self.rect_listbox.delete(0, tk.END)
        self.current_rects = []

        # 检查是否有矩形框信息
        if "targetList" in image_info and image_info["targetList"]:
            for i, target_info in enumerate(image_info["targetList"]):
                # 提取标记信息
                marks = target_info.get("marks", [])
                mark_text = ""
                if marks:
                    # 显示所有标记，而不只是值为 'true' 的标记
                    mark_display = [f"{mark['name']}:{mark['value']}" for mark in marks]
                    if mark_display:
                        mark_text = f" - {', '.join(mark_display)}"
                if target_info.get("rect"):
                    self.rect_listbox.insert(tk.END, f"目标 {i+1}{mark_text}")
                    self.current_rects.append(target_info)
                elif target_info.get("CoordinateList"):
                    coord_count = len(target_info["CoordinateList"])
                    self.rect_listbox.insert(tk.END, f"目标 {i+1}{mark_text}")
                    self.current_rects.append(target_info)

        # 重置选择状态 - 但保留当前选择状态
        # 只有在没有选择且没有显示全部时才重置
        if self.selected_rect_index is not None and self.rect_listbox.size() > 0:
            # 保持当前选择状态，但确保索引在有效范围内
            if self.selected_rect_index < self.rect_listbox.size():
                self.rect_listbox.selection_set(self.selected_rect_index)
            else:
                # 如果索引超出范围，重置选择状态
                self.selected_rect_index = None
                self.show_all_rects_flag = False
        elif self.show_all_rects_flag:
            # 显示全部模式，保持状态
            pass
        else:
            # 重置选择状态
            self.selected_rect_index = None
            self.show_all_rects_flag = False

    def on_rect_select(self, event):
        """矩形框选择事件处理"""
        selection = self.rect_listbox.curselection()
        if not selection:
            # 如果没有选择，则设置为不显示任何矩形框
            self.selected_rect_index = None
            self.show_all_rects_flag = False
            return

        index = selection[0]
        self.selected_rect_index = index
        self.show_all_rects_flag = False

        # 重新显示图片，只显示选中的矩形框
        if self.current_popup_image:
            self.display_image(self.current_popup_image)

    def show_all_rects(self):
        """显示所有矩形框"""
        self.selected_rect_index = None
        self.show_all_rects_flag = True

        # 重新显示图片，显示所有矩形框
        if self.current_popup_image:
            self.display_image(self.current_popup_image)

    def hide_all_rects(self):
        """隐藏所有矩形框"""
        self.selected_rect_index = None
        self.show_all_rects_flag = False

        # 重新显示图片，不显示任何矩形框
        if self.current_popup_image:
            self.display_image(self.current_popup_image)

    def on_popup_resize(self, event):
        """弹窗大小变化事件处理（带防抖机制）"""
        # 取消之前的定时器
        if self.popup_resize_timer:
            self.parent.after_cancel(self.popup_resize_timer)

        # 设置新的定时器（防抖延迟200毫秒）
        self.popup_resize_timer = self.parent.after(200, self._delayed_popup_resize)

    def _delayed_popup_resize(self):
        """延迟执行的弹窗大小变化处理"""
        try:
            if hasattr(self, "current_popup_image") and self.current_popup_image:
                # 检查弹窗是否仍然存在
                if not self.popup or not self.popup.winfo_exists():
                    return

                # 检查图片文件是否仍然存在
                image_path = self.current_popup_image.get("filename")
                if not image_path or not os.path.exists(image_path):
                    return

                # 重新显示图片以适应新的大小
                self.display_image(self.current_popup_image)
        except Exception as e:
            print(f"弹窗大小变化处理错误: {e}")
        finally:
            self.popup_resize_timer = None

    def show(self, image_info):
        """显示图片弹窗"""
        if not self.popup:
            self.create_popup()

        self.popup.deiconify()
        self.popup.lift()
        self.popup.focus_force()

        # 显示图片和矩形框
        self.display_image(image_info)

    def display_image(self, image_info):
        """在弹窗中显示图片（自适应窗口大小并按原始比例铺满）"""
        image_path = image_info["filename"]
        if not image_path or not os.path.exists(image_path):
            self.popup_image_label.config(image="", text="暂无图片")
            self.popup_image_info_label.config(text="")
            return

        try:
            # 存储当前图片信息，用于窗口大小变化时重新显示
            self.current_popup_image = image_info

            # 加载图片
            image = Image.open(image_path)
            original_width, original_height = image.size

            # 获取当前画布可用尺寸
            canvas_width = self.popup_image_canvas.winfo_width()
            canvas_height = self.popup_image_canvas.winfo_height()

            # 如果画布尺寸为1（初始化状态），使用默认尺寸
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 600
                canvas_height = 400

            # 计算保持原始比例的缩放比例
            scale_x = canvas_width / original_width
            scale_y = canvas_height / original_height
            scale = min(scale_x, scale_y, 1.0)  # 不超过原始大小

            # 计算新尺寸，保持原始比例
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)

            # 调整图片大小
            if scale < 1.0:
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 更新矩形框侧边栏
            self.update_rect_sidebar(image_info)

            # 如果有 targetList，根据选择状态绘制矩形框
            if "targetList" in image_info and image_info["targetList"]:
                # 创建可绘制的图像副本
                drawable_image = image.copy()
                draw = ImageDraw.Draw(drawable_image)

                # 尝试加载字体，如果失败则使用默认字体
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except:
                    font = ImageFont.load_default()

                # 根据选择状态绘制矩形框
                if self.show_all_rects_flag:
                    # 显示所有矩形框
                    for i, target_info in enumerate(image_info["targetList"]):
                        self.draw_rect(draw, target_info, drawable_image, font, i, scale)
                elif self.selected_rect_index is not None:
                    # 只显示选中的矩形框
                    if self.selected_rect_index < len(image_info["targetList"]):
                        target_info = image_info["targetList"][self.selected_rect_index]
                        self.draw_rect(
                            draw,
                            target_info,
                            drawable_image,
                            font,
                            self.selected_rect_index,
                            scale,
                        )
                else:
                    # 默认不显示矩形框
                    pass

                # 使用绘制后的图像
                image = drawable_image

            # 转换为Tkinter可显示的格式
            photo = ImageTk.PhotoImage(image)

            # 更新图片标签
            self.popup_image_label.config(image=photo, text="")
            self.popup_image_label.image = photo  # 保持引用

            # 调整容器大小以适应图片
            self.popup_image_container.config(width=new_width, height=new_height)
            self.popup_image_canvas.config(scrollregion=(0, 0, new_width, new_height))

            # 将图片窗口居中显示
            canvas_width = self.popup_image_canvas.winfo_width()
            canvas_height = self.popup_image_canvas.winfo_height()
            x_offset = max(0, (canvas_width - new_width) // 2)
            y_offset = max(0, (canvas_height - new_height) // 2)
            self.popup_image_canvas.coords("image_window", x_offset, y_offset)

            # 更新图片信息
            file_size = os.path.getsize(image_path)
            file_size_kb = file_size / 1024

            target_info = ""
            if "targetList" in image_info and image_info["targetList"]:
                rect_count = len(image_info["targetList"])
                target_info = f" | 检测到 {rect_count} 个目标"

            display_width, display_height = image.size
            image_info_text = f"原始尺寸: {original_width}x{original_height} | 显示尺寸: {display_width}x{display_height} | 大小: {file_size_kb:.1f}KB{target_info}"
            self.popup_image_info_label.config(text=image_info_text)

        except Exception as e:
            print(f"显示弹窗图片失败: {e}")
            import traceback

            traceback.print_exc()
            self.popup_image_label.config(image="", text="显示失败")
            self.popup_image_info_label.config(text="")

    def draw_rect(self, draw, target_info, image, font, index, scale=1.0):
        """在弹窗中绘制单个矩形框及其标记信息和坐标点区域"""
        if target_info.get("rect"):
            rect_data = target_info["rect"]
            marks = target_info.get("marks", [])

            # 将相对坐标转换为绝对坐标（考虑缩放比例）
            x1 = int(rect_data["x"] * image.width)
            y1 = int(rect_data["y"] * image.height)
            x2 = int((rect_data["x"] + rect_data["width"]) * image.width)
            y2 = int((rect_data["y"] + rect_data["height"]) * image.height)

            # 绘制矩形框（红色边框）
            draw.rectangle([x1, y1, x2, y2], outline="red", width=2)

            # 绘制标记信息
            text_y = y1 - 20 if y1 > 30 else y2 + 5
            for j, mark in enumerate(marks):
                text = f"{mark['name']}: {mark['value']}"
                # 绘制文本背景
                bbox = draw.textbbox((x1, text_y + j * 15), text, font=font)
                draw.rectangle(bbox, fill="red")
                # 绘制文本
                draw.text((x1, text_y + j * 15), text, fill="white", font=font)

        elif target_info.get("CoordinateList"):
            # 绘制CoordinateList坐标点区域
            self.draw_coordinate_list(draw, target_info["CoordinateList"], image, index)

    def draw_coordinate_list(self, draw, coordinate_list, image, index):
        """绘制CoordinateList坐标点区域

        Args:
            draw: ImageDraw对象
            coordinate_list: 坐标点列表 [{"x": x, "y": y}, ...]
            image: PIL图像对象
            index: 目标索引
        """
        if not coordinate_list or len(coordinate_list) < 2:
            return

    def close(self):
        """关闭弹窗"""
        if self.popup:
            self.popup.withdraw()
            # 重置选择状态，以便下次打开时显示默认状态
            self.selected_rect_index = None
            self.show_all_rects_flag = False

    def is_visible(self):
        """检查弹窗是否可见"""
        if not self.popup:
            return False
        return self.popup.state() == "normal"

    def destroy(self):
        """销毁弹窗"""
        if self.popup:
            self.popup.destroy()
            self.popup = None
