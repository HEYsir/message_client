from cx_Freeze import setup, Executable
import sys
import os
import site

def get_real_site_packages():
    # 虚拟环境优先用 getsitepackages
    if hasattr(sys, 'base_prefix') and sys.prefix != sys.base_prefix:
        return site.getsitepackages()[1]
    # 非虚拟环境用 getusersitepackages
    return site.getusersitepackages()

site_packages = get_real_site_packages()
ck_libs_src = os.path.join(site_packages, 'confluent_kafka.libs')
ck_libs_dst = os.path.join('lib', 'confluent_kafka.libs')

include_files = [
    "application", "core", "ui"
]
if os.path.exists(ck_libs_src):
    include_files.append((ck_libs_src, ck_libs_dst))
else:
    print(f"警告：未找到 {ck_libs_src}，confluent_kafka 相关功能可能无法用！")

build_exe_options = {
    "packages": [
        "os", "importlib", "tkinter", "ui", "core", "application", "concurrent", "asyncio", "json", "html", "re", "xml", "requests", "confluent_kafka", "pika", "pytz", "aiohttp", "pyperclip",
        "application.http", "application.kafka", "application.rmq",
        "application.http.service", "application.kafka.service", "application.rmq.service"
    ],
    "includes": [
        # 强制包含所有动态发现的tab页面及其父包
        "application.http.ui_config_tab", "application.kafka.ui_config_tab", "application.rmq.ui_config_tab",
        "application.http", "application.kafka", "application.rmq",
        "ui.base_tab", "ui.main_window"
    ],
    "include_files": include_files,
    "excludes": [],
    "zip_include_packages": []  # 不压缩包，便于动态import
}

# 调试模式：带控制台窗口，print输出可见
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name = "AlarmServer",
    version = "1.0",
    description = "报警服务监控工具",
    options = {"build_exe": build_exe_options},
    executables = [Executable("main.py", base=base, target_name="AlarmServer.exe")]
)
