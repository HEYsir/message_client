import socket


def get_local_ip_list():
    """获取本机所有网口的IPv4地址列表"""
    ip_list = set()
    hostname = socket.gethostname()
    try:
        # 获取主机名对应的所有IP
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ip_list.add(ip)
    except Exception:
        pass
    # 通过UDP socket获取本地出口IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if not ip.startswith("127."):
            ip_list.add(ip)
        s.close()
    except Exception:
        pass
    # 加入通配地址
    ip_list.add("127.0.0.1")
    return sorted(ip_list)
