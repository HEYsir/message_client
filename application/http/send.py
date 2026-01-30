import http.client
import urllib.parse
import ssl
import json
import hashlib
import base64
import random
import string
from time import perf_counter


class FastHTTPPost:
    """High-performance HTTP utility supporting multiple methods"""

    def __init__(self, url, timeout=10, max_redirects=3):
        self.url = url
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.auth_info = None
        self._parse_url()

    def _parse_url(self):
        parsed = urllib.parse.urlparse(self.url)
        self.scheme = parsed.scheme
        self.host = parsed.netloc.split(":")[0]
        self.port = parsed.port or (443 if self.scheme == "https" else 80)
        self.path = parsed.path + ("?" + parsed.query if parsed.query else "")

    def _create_connection(self):
        if self.scheme == "https":
            context = ssl.create_default_context()
            return http.client.HTTPSConnection(self.host, port=self.port, timeout=self.timeout, context=context)
        return http.client.HTTPConnection(self.host, port=self.port, timeout=self.timeout)

    def _send_request(self, method, data=None, json_data=None, headers=None):
        start_time = perf_counter()
        redirect_count = 0
        auth_attempts = 0
        body, final_headers = self._prepare_payload(data, json_data, headers, method)

        while redirect_count <= self.max_redirects and auth_attempts <= 1:
            conn = self._create_connection()
            try:
                conn.request(method, self.path, body=body, headers=final_headers)
                resp = conn.getresponse()

                # 处理认证挑战
                if resp.status == 401 and auth_attempts == 0:
                    auth_header = resp.getheader("WWW-Authenticate")
                    if auth_header and "Digest" in auth_header:
                        self.auth_info = self._parse_auth_challenge(auth_header)
                        if self.auth_info and headers and "Authorization" in headers:
                            # 重新构建认证头
                            auth_data = headers.get("Authorization")
                            if "Digest" in auth_data:
                                username = self._extract_username_from_auth(auth_data)
                                password = self._extract_password_from_auth(auth_data)
                                if username and password:
                                    final_headers["Authorization"] = self._build_digest_auth_header(
                                        method, self.path, username, password, self.auth_info
                                    )
                                    auth_attempts += 1
                                    continue

                if resp.status in (301, 302, 307, 308):
                    location = resp.getheader("Location")
                    if not location:
                        break
                    self.url = location
                    self._parse_url()
                    redirect_count += 1
                    continue

                content = resp.read()
                return resp.status, dict(resp.getheaders()), content
            finally:
                conn.close()
        raise Exception("Too many redirects or authentication failed")

    def get(self, headers=None):
        return self._send_request("GET", headers=headers)

    def post(self, data=None, json_data=None, headers=None):
        return self._send_request("POST", data=data, json_data=json_data, headers=headers)

    def put(self, data=None, json_data=None, headers=None):
        return self._send_request("PUT", data=data, json_data=json_data, headers=headers)

    def delete(self, headers=None):
        return self._send_request("DELETE", headers=headers)

    def _prepare_payload(self, data, json_data, headers, method):
        final_headers = headers.copy() if headers else {}
        body = b""

        # 对于需要请求体的方法，准备payload
        if method in ["POST", "PUT"]:
            if json_data is not None:
                body = json.dumps(json_data).encode("utf-8")
                final_headers["Content-Type"] = "application/json"
            elif data is not None:
                body = data if isinstance(data, bytes) else str(data).encode("utf-8")
            else:
                body = b""

        # 如果有请求体，设置Content-Length
        if body and "Content-Length" not in final_headers:
            final_headers["Content-Length"] = str(len(body))

        return body, final_headers

    def _parse_auth_challenge(self, auth_header):
        """解析WWW-Authenticate头"""
        if not auth_header or "Digest" not in auth_header:
            return None

        auth_info = {}
        # 提取Digest认证参数
        parts = auth_header.split("Digest ")[1]
        for part in parts.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                auth_info[key] = value
        return auth_info

    def _extract_username_from_auth(self, auth_header):
        """从Authorization头提取用户名"""
        if "username=" in auth_header:
            parts = auth_header.split("username=")[1].split(",")[0].strip('"')
            return parts
        return None

    def _extract_password_from_auth(self, auth_header):
        """从Authorization头提取密码信息"""
        # 从Authorization头中解析密码信息
        # 注意：在实际应用中，密码应该从安全存储中获取，这里只是简化处理
        if "password=" in auth_header:
            parts = auth_header.split("password=")[1].split(",")[0].strip('"')
            return parts
        return "password"  # 默认密码

    def _build_digest_auth_header(self, method, uri, username, password, auth_info):
        """构建Digest认证头"""
        realm = auth_info.get("realm", "")
        nonce = auth_info.get("nonce", "")
        qop = auth_info.get("qop", "")

        # 生成随机客户端nonce
        cnonce = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        nc = "00000001"  # 请求计数器

        # 计算HA1
        ha1_data = f"{username}:{realm}:{password}"
        ha1 = hashlib.md5(ha1_data.encode()).hexdigest()

        # 计算HA2
        ha2_data = f"{method}:{uri}"
        ha2 = hashlib.md5(ha2_data.encode()).hexdigest()

        # 计算response
        if qop:
            response_data = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
        else:
            response_data = f"{ha1}:{nonce}:{ha2}"

        response = hashlib.md5(response_data.encode()).hexdigest()

        # 构建Authorization头
        auth_header = f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}"'
        auth_header += f', response="{response}"'

        if qop:
            auth_header += f', qop={qop}, nc={nc}, cnonce="{cnonce}"'

        if "opaque" in auth_info:
            auth_header += f', opaque="{auth_info["opaque"]}"'

        return auth_header
