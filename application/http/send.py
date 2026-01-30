import http.client
import urllib.parse
import ssl
import json
from time import perf_counter


class FastHTTPPost:
    """High-performance HTTP utility supporting multiple methods"""

    def __init__(self, url, timeout=10, max_redirects=3):
        self.url = url
        self.timeout = timeout
        self.max_redirects = max_redirects
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
        body, final_headers = self._prepare_payload(data, json_data, headers, method)
        while redirect_count <= self.max_redirects:
            conn = self._create_connection()
            try:
                conn.request(method, self.path, body=body, headers=final_headers)
                resp = conn.getresponse()
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
        raise Exception("Too many redirects")

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
