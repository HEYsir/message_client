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

        # 图片缩放和移动相关变量
        self.image_scale = 1.0  # 当前缩放比例
        self.image_offset_x = 0  # X轴偏移
        self.image_offset_y = 0  # Y轴偏移
        self.is_dragging = False  # 是否正在拖拽
        self.last_drag_x = 0  # 上次拖拽X坐标
        self.last_drag_y = 0  # 上次拖拽Y坐标
        self.original_image_size = (0, 0)  # 原始图片尺寸
        self.current_photo_image = None  # 当前显示的图片对象
        self.is_ctrl_pressed = False  # Ctrl键是否按下
        self.zoom_timer = None  # 缩放防抖定时器

        # 预缩放缓存相关变量
        self.original_image_cache = None  # 原始图片缓存（PIL Image对象）
        self.scaled_image_cache = None  # 缩放后的图片缓存（PIL Image对象）
        self.cached_scale = 1.0  # 缓存的缩放比例

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

        # 绑定键盘和鼠标事件
        self.bind_events()

    def bind_events(self):
        """绑定键盘和鼠标事件"""
        # 绑定键盘事件到弹窗和画布
        for widget in [self.popup, self.popup_image_canvas]:
            widget.bind("<KeyPress-Control_L>", self.on_ctrl_press)
            widget.bind("<KeyPress-Control_R>", self.on_ctrl_press)
            widget.bind("<KeyRelease-Control_L>", self.on_ctrl_release)
            widget.bind("<KeyRelease-Control_R>", self.on_ctrl_release)
            widget.focus_set()  # 设置焦点

        # 绑定鼠标滚轮事件到画布和图片容器
        for widget in [self.popup_image_canvas, self.popup_image_container, self.popup_image_label]:
            widget.bind("<MouseWheel>", self.on_mouse_wheel)
            widget.bind("<ButtonPress-1>", self.on_mouse_press)
            widget.bind("<B1-Motion>", self.on_mouse_drag)
            widget.bind("<ButtonRelease-1>", self.on_mouse_release)

        # 确保弹窗可以接收键盘事件
        self.popup.focus_force()

        print("事件绑定完成：画布、容器、标签都绑定了鼠标事件")

    def on_ctrl_press(self, event):
        """Ctrl键按下事件"""
        print("Ctrl键按下")
        self.is_ctrl_pressed = True
        print(f"Ctrl状态: {self.is_ctrl_pressed}")

    def on_ctrl_release(self, event):
        """Ctrl键释放事件"""
        print("Ctrl键释放")
        self.is_ctrl_pressed = False
        print(f"Ctrl状态: {self.is_ctrl_pressed}")

    def on_mouse_wheel(self, event):
        """鼠标滚轮事件 - 缩放图片（即时更新，无防抖）"""
        print(f"鼠标滚轮事件: delta={event.delta}, Ctrl状态={self.is_ctrl_pressed}")

        if not self.is_ctrl_pressed or not self.current_popup_image:
            print("条件不满足: Ctrl未按下或无图片")
            return

        # 取消之前的缩放定时器
        if self.zoom_timer:
            self.parent.after_cancel(self.zoom_timer)
            self.zoom_timer = None

        # 缩放因子
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        print(f"缩放因子: {zoom_factor}")

        # 限制缩放范围
        new_scale = self.image_scale * zoom_factor
        if new_scale < 0.1:  # 最小缩放10%
            new_scale = 0.1
        elif new_scale > 5.0:  # 最大缩放500%
            new_scale = 5.0

        print(f"当前缩放: {self.image_scale}, 新缩放: {new_scale}")

        if new_scale != self.image_scale:
            # 计算鼠标位置相对于图片的坐标
            canvas_x = self.popup_image_canvas.canvasx(event.x)
            canvas_y = self.popup_image_canvas.canvasy(event.y)

            # 获取图片窗口位置
            window_x, window_y = self.popup_image_canvas.coords("image_window")

            # 计算鼠标在图片中的相对位置
            mouse_rel_x = (canvas_x - window_x) / self.image_scale
            mouse_rel_y = (canvas_y - window_y) / self.image_scale

            # 更新缩放比例
            self.image_scale = new_scale

            # 重新计算偏移，使鼠标点保持在同一位置
            self.image_offset_x = canvas_x - mouse_rel_x * self.image_scale
            self.image_offset_y = canvas_y - mouse_rel_y * self.image_scale

            # print(f"更新缩放: {self.image_scale}, 偏移: ({self.image_offset_x}, {self.image_offset_y})")

            # 立即更新图片显示，无延迟
            self.display_image(self.current_popup_image, reset_scale=False)

    def on_mouse_press(self, event):
        """鼠标按下事件 - 开始拖拽"""
        print(f"鼠标按下: Ctrl状态={self.is_ctrl_pressed}, 有图片={self.current_popup_image is not None}")

        if not self.is_ctrl_pressed or not self.current_popup_image:
            print("条件不满足，不开始拖拽")
            return

        self.is_dragging = True
        self.last_drag_x = event.x
        self.last_drag_y = event.y

        print(f"开始拖拽: 起始位置=({self.last_drag_x}, {self.last_drag_y})")

        # 更改鼠标光标为移动图标
        self.popup_image_canvas.config(cursor="fleur")

    def on_mouse_drag(self, event):
        """鼠标拖拽事件 - 移动图片（优化版，减少重绘）"""
        if not self.is_dragging or not self.current_popup_image or not self.is_ctrl_pressed:
            # 如果Ctrl键释放了，结束拖拽
            if self.is_dragging and not self.is_ctrl_pressed:
                self.is_dragging = False
                self.popup_image_canvas.config(cursor="")
            return

        # 计算移动距离
        dx = event.x - self.last_drag_x
        dy = event.y - self.last_drag_y

        # 更新偏移
        self.image_offset_x += dx
        self.image_offset_y += dy

        # 更新最后位置
        self.last_drag_x = event.x
        self.last_drag_y = event.y

        # 优化：只更新位置，不重绘图片（除非需要绘制矩形框）
        if self.show_all_rects_flag or self.selected_rect_index is not None:
            # 如果有矩形框需要显示，需要重新绘制图片
            self.display_image(self.current_popup_image, reset_scale=False)
        else:
            # 没有矩形框，只更新位置
            self._update_image_position_only()

        # 阻止事件传播，避免触发其他重绘
        return "break"

    def on_mouse_release(self, event):
        """鼠标释放事件 - 结束拖拽"""
        self.is_dragging = False
        # 恢复默认鼠标光标
        self.popup_image_canvas.config(cursor="")

    def _update_image_position_only(self):
        """只更新图片位置，不重绘图片（优化移动性能）"""
        if not self.current_popup_image or not self.current_photo_image:
            return

        # 直接更新图片窗口位置
        self.popup_image_canvas.coords("image_window", self.image_offset_x, self.image_offset_y)

        # 更新图片信息（仅位置信息）
        if hasattr(self, "original_image_size") and self.original_image_size:
            original_width, original_height = self.original_image_size
            scaled_width = int(original_width * self.image_scale)
            scaled_height = int(original_height * self.image_scale)

            target_info = ""
            if "targetList" in self.current_popup_image and self.current_popup_image["targetList"]:
                rect_count = len(self.current_popup_image["targetList"])
                target_info = f" | 检测到 {rect_count} 个目标"

            image_info_text = f"原始尺寸: {original_width}x{original_height} | 显示尺寸: {scaled_width}x{scaled_height} | 缩放: {self.image_scale:.1f}x | 偏移: ({int(self.image_offset_x)}, {int(self.image_offset_y)}){target_info}"
            self.popup_image_info_label.config(text=image_info_text)

    def _update_image_position(self):
        """更新图片位置（仅移动，不重新加载图片）"""
        if not self.current_popup_image or not self.current_photo_image:
            return

        # 直接更新图片窗口位置
        self.popup_image_canvas.coords("image_window", self.image_offset_x, self.image_offset_y)

        # 更新图片信息（仅位置信息）
        if hasattr(self, "original_image_size") and self.original_image_size:
            original_width, original_height = self.original_image_size
            scaled_width = int(original_width * self.image_scale)
            scaled_height = int(original_height * self.image_scale)

            target_info = ""
            if "targetList" in self.current_popup_image and self.current_popup_image["targetList"]:
                rect_count = len(self.current_popup_image["targetList"])
                target_info = f" | 检测到 {rect_count} 个目标"

            image_info_text = f"原始尺寸: {original_width}x{original_height} | 显示尺寸: {scaled_width}x{scaled_height} | 缩放: {self.image_scale:.1f}x | 偏移: ({int(self.image_offset_x)}, {int(self.image_offset_y)}){target_info}"
            self.popup_image_info_label.config(text=image_info_text)

    def update_image_display(self):
        """更新图片显示（根据缩放和偏移）"""
        if not self.current_popup_image:
            return

        try:
            image_path = self.current_popup_image["filename"]
            if not os.path.exists(image_path):
                return

            # 加载原始图片
            image = Image.open(image_path)
            original_width, original_height = image.size
            self.original_image_size = (original_width, original_height)

            # 计算缩放后的尺寸
            scaled_width = int(original_width * self.image_scale)
            scaled_height = int(original_height * self.image_scale)

            # 调整图片大小
            if self.image_scale != 1.0:
                image = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

            # 如果有 targetList，绘制矩形框
            if "targetList" in self.current_popup_image and self.current_popup_image["targetList"]:
                drawable_image = image.copy()
                draw = ImageDraw.Draw(drawable_image)

                try:
                    font = ImageFont.truetype("simsun.ttc", 12)
                except:
                    font = ImageFont.load_default()

                # 根据选择状态绘制矩形框
                if self.show_all_rects_flag:
                    for i, target_info in enumerate(self.current_popup_image["targetList"]):
                        self.draw_rect(draw, target_info, drawable_image, font, i, self.image_scale)
                elif self.selected_rect_index is not None:
                    if self.selected_rect_index < len(self.current_popup_image["targetList"]):
                        target_info = self.current_popup_image["targetList"][self.selected_rect_index]
                        self.draw_rect(
                            draw, target_info, drawable_image, font, self.selected_rect_index, self.image_scale
                        )

                image = drawable_image

            # 转换为Tkinter格式
            photo = ImageTk.PhotoImage(image)

            # 更新图片标签
            self.popup_image_label.config(image=photo, text="")
            self.popup_image_label.image = photo
            self.current_photo_image = photo

            # 调整容器大小
            self.popup_image_container.config(width=scaled_width, height=scaled_height)
            self.popup_image_canvas.config(scrollregion=(0, 0, scaled_width, scaled_height))

            # 更新图片窗口位置
            self.popup_image_canvas.coords("image_window", self.image_offset_x, self.image_offset_y)

            # 更新图片信息
            file_size = os.path.getsize(image_path)
            file_size_kb = file_size / 1024

            target_info = ""
            if "targetList" in self.current_popup_image and self.current_popup_image["targetList"]:
                rect_count = len(self.current_popup_image["targetList"])
                target_info = f" | 检测到 {rect_count} 个目标"

            image_info_text = f"原始尺寸: {original_width}x{original_height} | 显示尺寸: {scaled_width}x{scaled_height} | 缩放: {self.image_scale:.1f}x | 大小: {file_size_kb:.1f}KB{target_info}"
            self.popup_image_info_label.config(text=image_info_text)

        except Exception as e:
            print(f"更新图片显示失败: {e}")
            import traceback

            traceback.print_exc()

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

        # 重新显示图片，只显示选中的矩形框，保持当前缩放状态
        if self.current_popup_image:
            self.display_image(self.current_popup_image, reset_scale=False)

    def show_all_rects(self):
        """显示所有矩形框"""
        self.selected_rect_index = None
        self.show_all_rects_flag = True

        # 重新显示图片，显示所有矩形框，保持当前缩放状态
        if self.current_popup_image:
            self.display_image(self.current_popup_image, reset_scale=False)

    def hide_all_rects(self):
        """隐藏所有矩形框"""
        self.selected_rect_index = None
        self.show_all_rects_flag = False

        # 重新显示图片，不显示任何矩形框，保持当前缩放状态
        if self.current_popup_image:
            self.display_image(self.current_popup_image, reset_scale=False)

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

                # 窗口大小变化时不重置缩放状态，只重新显示图片
                self.display_image(self.current_popup_image, reset_scale=False)
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

    def display_image(self, image_info, reset_scale=True):
        """在弹窗中显示图片（支持缩放和移动功能)

        Args:
            image_info: 图片信息字典
            reset_scale: 是否重置缩放状态（默认True，窗口大小变化时重置）
        """
        image_path = image_info["filename"]
        if not image_path or not os.path.exists(image_path):
            self.popup_image_label.config(image="", text="暂无图片")
            self.popup_image_info_label.config(text="")
            return

        try:
            # 检查是否是新图片（需要重置缩放状态）
            is_new_image = self.current_popup_image is None or self.current_popup_image.get(
                "filename"
            ) != image_info.get("filename")

            # 存储当前图片信息
            self.current_popup_image = image_info

            # 只有在真正需要重置时才重置缩放状态
            if reset_scale and is_new_image:
                self.image_scale = 1.0
                self.image_offset_x = 0
                self.image_offset_y = 0
                # 清除缓存
                self.original_image_cache = None
                self.scaled_image_cache = None
                self.cached_scale = 1.0
                # print("重置缩放状态（新图片）")
            else:
                # 保持当前缩放和偏移
                # print(f"保持缩放状态: scale={self.image_scale}, offset=({self.image_offset_x}, {self.image_offset_y})")
                pass

            # 如果缓存为空或者是新图片，加载原始图片
            if self.original_image_cache is None or is_new_image:
                self.original_image_cache = Image.open(image_path)
                self.original_image_size = self.original_image_cache.size

            # 更新矩形框侧边栏
            self.update_rect_sidebar(image_info)

            # 计算缩放后的尺寸
            scaled_width = int(self.original_image_size[0] * self.image_scale)
            scaled_height = int(self.original_image_size[1] * self.image_scale)

            # 使用预缩放缓存机制
            if self.scaled_image_cache is None or self.cached_scale != self.image_scale:
                # 重新缩放图片
                if self.image_scale != 1.0:
                    self.scaled_image_cache = self.original_image_cache.resize(
                        (scaled_width, scaled_height), Image.Resampling.LANCZOS
                    )
                else:
                    self.scaled_image_cache = self.original_image_cache.copy()
                self.cached_scale = self.image_scale

            # 创建绘制副本
            drawable_image = self.scaled_image_cache.copy()
            draw = ImageDraw.Draw(drawable_image)

            # 如果有 targetList，根据选择状态绘制矩形框
            if "targetList" in image_info and image_info["targetList"]:
                # 尝试加载支持UTF-8的字体
                try:
                    font = ImageFont.truetype("simsun.ttc", 12)  # 宋体
                except:
                    font = ImageFont.load_default()

                # 根据选择状态绘制矩形框
                if self.show_all_rects_flag:
                    # 显示所有矩形框
                    for i, target_info in enumerate(image_info["targetList"]):
                        self.draw_rect(draw, target_info, drawable_image, font, i, self.image_scale)
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
                            self.image_scale,
                        )

            # 转换为Tkinter可显示的格式
            photo = ImageTk.PhotoImage(drawable_image)

            # 更新图片标签
            old_photo = self.current_photo_image
            self.current_photo_image = photo
            self.popup_image_label.config(image=photo, text="")
            self.popup_image_label.image = photo  # 保持引用

            # 清理旧图片引用
            if old_photo:
                del old_photo

            # 调整容器大小以适应图片
            self.popup_image_container.config(width=scaled_width, height=scaled_height)
            self.popup_image_canvas.config(scrollregion=(0, 0, scaled_width, scaled_height))

            # 更新图片窗口位置（考虑偏移）
            self.popup_image_canvas.coords("image_window", self.image_offset_x, self.image_offset_y)

            # 更新图片信息
            file_size = os.path.getsize(image_path)
            file_size_kb = file_size / 1024

            target_info = ""
            if "targetList" in image_info and image_info["targetList"]:
                rect_count = len(image_info["targetList"])
                target_info = f" | 检测到 {rect_count} 个目标"

            image_info_text = f"原始尺寸: {self.original_image_size[0]}x{self.original_image_size[1]} | 显示尺寸: {scaled_width}x{scaled_height} | 缩放: {self.image_scale:.1f}x | 大小: {file_size_kb:.1f}KB{target_info}"
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

        # 将坐标点转换为图片像素坐标，并确保在图片范围内
        points = []
        for coord in coordinate_list:
            # 假设坐标点是相对于图片宽高的比例值（0-1之间）
            if 0 <= coord["x"] <= 1 and 0 <= coord["y"] <= 1:
                # 相对坐标转换
                x = int(coord["x"] * image.width)
                y = int(coord["y"] * image.height)
            else:
                # 绝对坐标（直接使用）
                x = int(coord["x"] * image.width / 1000)
                y = int(coord["y"] * image.height / 1000)

            # 确保坐标点在图片范围内
            x = max(0, min(x, image.width - 1))
            y = max(0, min(y, image.height - 1))

            points.append((x, y))

        # 使用凸包算法对坐标点进行排序，避免多边形交叉
        def convex_hull(points):
            """计算点的凸包（使用Graham Scan算法）"""
            if len(points) <= 3:
                return points

            # 找到最左下角的点作为起点
            start = min(points, key=lambda p: (p[1], p[0]))

            # 计算每个点相对于起点的极角
            def polar_angle(p):
                import math

                dx = p[0] - start[0]
                dy = p[1] - start[1]
                return math.atan2(dy, dx)

            # 按极角排序，极角相同的按距离排序
            sorted_points = sorted(
                points, key=lambda p: (polar_angle(p), (p[0] - start[0]) ** 2 + (p[1] - start[1]) ** 2)
            )

            # 构建凸包
            hull = [start]
            for p in sorted_points:
                if p == start:
                    continue
                while len(hull) > 1:
                    # 检查是否是右转
                    a, b = hull[-2], hull[-1]
                    cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
                    if cross >= 0:  # 右转或共线
                        break
                    hull.pop()
                hull.append(p)

            return hull

        # 使用凸包算法排序坐标点
        if len(points) >= 3:
            points = convex_hull(points)
        else:
            # 对于2个点，保持原有顺序
            pass

        # 坐标点颜色，根据索引使用不同颜色
        colors = ["red", "blue", "green", "orange", "purple", "brown", "pink", "gray"]
        color = colors[index % len(colors)]

        # 绘制坐标点
        point_radius = 4
        for idx, point in enumerate(points):
            x, y = point
            # 绘制实心圆点
            draw.ellipse(
                [x - point_radius, y - point_radius, x + point_radius, y + point_radius],
                fill=color,
                outline=color,
                width=2,
            )
            # 在每个点上显示点的编号
            draw.text(
                (x - point_radius, y - point_radius),
                str(idx + 1),
                fill="white",
                font=ImageFont.load_default(),
            )

        # 如果只有2个点，绘制直线
        if len(points) == 2:
            draw.line([points[0], points[1]], fill=color, width=2)

        # 如果有3个或更多点，绘制多边形区域
        elif len(points) >= 3:
            # 按顺时针或逆时针顺序连接所有点形成闭合区域
            # 这里使用PIL的polygon方法会自动处理闭合
            draw.polygon(points, outline=color, width=2)

        # 在第一个点附近显示目标编号
        if points:
            first_point = points[0]
            text = f"target {index+1}"
            # 计算文本位置（避免超出图片边界）
            text_x = first_point[0] + 10
            text_y = first_point[1] - 15

            # 确保文本在图片范围内
            text_x = max(5, min(text_x, image.width - 50))
            text_y = max(15, min(text_y, image.height - 5))

            # 绘制文本背景
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((text_x, text_y), text, font=font)
            draw.rectangle(bbox, fill=color)
            # 绘制文本
            draw.text((text_x, text_y), text, fill="white", font=font)

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
