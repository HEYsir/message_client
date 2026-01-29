from tkinter import Tk
from ui.main_window import MainWindow


def main():
    # 创建主窗口
    root = Tk()
    app = MainWindow(root)
    # 窗口关闭事件已经在MainWindow类中注册，这里不再重复注册
    root.mainloop()


if __name__ == "__main__":
    main()
