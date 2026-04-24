"""
HTTP请求工具模块
用于发送HTTP/HTTPS请求并验证响应
"""

import requests
import time
import json
from typing import Dict, Optional, Union, List
from urllib.parse import urljoin


class HttpClient:
    """HTTP客户端"""

    def __init__(self, base_url: str = "", timeout: int = 30, retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.last_response: Optional[requests.Response] = None

    def set_base_url(self, base_url: str):
        """设置基础URL"""
        self.base_url = base_url.rstrip('/')

    def set_headers(self, headers: Dict[str, str]):
        """设置默认请求头"""
        self.session.headers.update(headers)

    def set_timeout(self, timeout: int):
        """设置超时时间"""
        self.timeout = timeout

    def _make_url(self, path: str) -> str:
        """构建完整URL"""
        if path.startswith('http'):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发送请求并处理重试"""
        full_url = self._make_url(url)

        # 设置超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout

        last_exception = None

        for attempt in range(self.retries):
            try:
                response = self.session.request(method, full_url, **kwargs)
                self.last_response = response
                return response
            except (requests.Timeout, requests.ConnectionError) as e:
                last_exception = e
                if attempt < self.retries - 1:
                    time.sleep(1 * (attempt + 1))  # 指数退避
                continue

        raise last_exception or requests.RequestException("请求失败")

    def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None,
            **kwargs) -> requests.Response:
        """发送GET请求"""
        return self._request('GET', url, params=params, headers=headers, **kwargs)

    def post(self, url: str, data=None, json=None, headers: Optional[Dict] = None,
             **kwargs) -> requests.Response:
        """发送POST请求"""
        return self._request('POST', url, data=data, json=json, headers=headers, **kwargs)

    def put(self, url: str, data=None, json=None, headers: Optional[Dict] = None,
            **kwargs) -> requests.Response:
        """发送PUT请求"""
        return self._request('PUT', url, data=data, json=json, headers=headers, **kwargs)

    def delete(self, url: str, headers: Optional[Dict] = None,
               **kwargs) -> requests.Response:
        """发送DELETE请求"""
        return self._request('DELETE', url, headers=headers, **kwargs)

    def head(self, url: str, headers: Optional[Dict] = None,
             **kwargs) -> requests.Response:
        """发送HEAD请求"""
        return self._request('HEAD', url, headers=headers, **kwargs)

    def options(self, url: str, headers: Optional[Dict] = None,
                **kwargs) -> requests.Response:
        """发送OPTIONS请求"""
        return self._request('OPTIONS', url, headers=headers, **kwargs)

    def patch(self, url: str, data=None, json=None, headers: Optional[Dict] = None,
              **kwargs) -> requests.Response:
        """发送PATCH请求"""
        return self._request('PATCH', url, data=data, json=json, headers=headers, **kwargs)

    def close(self):
        """关闭会话"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ResponseValidator:
    """响应验证器"""

    def __init__(self, response: requests.Response):
        self.response = response
        self.errors = []

    def status_code(self, expected: int) -> 'ResponseValidator':
        """验证状态码"""
        if self.response.status_code != expected:
            self.errors.append(
                f"状态码不匹配: 期望 {expected}, 实际 {self.response.status_code}")
        return self

    def status_code_in(self, expected_codes: List[int]) -> 'ResponseValidator':
        """验证状态码在指定列表中"""
        if self.response.status_code not in expected_codes:
            self.errors.append(
                f"状态码不在期望列表中: 期望 {expected_codes}, 实际 {self.response.status_code}")
        return self

    def header_exists(self, header_name: str) -> 'ResponseValidator':
        """验证响应头存在"""
        if header_name not in self.response.headers:
            self.errors.append(f"响应头不存在: {header_name}")
        return self

    def header_equals(self, header_name: str, expected_value: str) -> 'ResponseValidator':
        """验证响应头值"""
        actual = self.response.headers.get(header_name)
        if actual != expected_value:
            self.errors.append(
                f"响应头 {header_name} 值不匹配: 期望 '{expected_value}', 实际 '{actual}'")
        return self

    def header_contains(self, header_name: str, substring: str) -> 'ResponseValidator':
        """验证响应头包含子串"""
        actual = self.response.headers.get(header_name, '')
        if substring not in actual:
            self.errors.append(
                f"响应头 {header_name} 不包含 '{substring}': 实际 '{actual}'")
        return self

    def body_contains(self, substring: str) -> 'ResponseValidator':
        """验证响应体包含子串"""
        if substring not in self.response.text:
            self.errors.append(f"响应体不包含: '{substring}'")
        return self

    def body_equals(self, expected: str) -> 'ResponseValidator':
        """验证响应体完全匹配"""
        if self.response.text != expected:
            self.errors.append(f"响应体不匹配: 期望 '{expected}', 实际 '{self.response.text}'")
        return self

    def json_path_equals(self, path: str, expected_value) -> 'ResponseValidator':
        """验证JSON路径值"""
        try:
            data = self.response.json()
            keys = path.split('.')
            actual = data
            for key in keys:
                if isinstance(actual, dict):
                    actual = actual.get(key)
                elif isinstance(actual, list) and key.isdigit():
                    actual = actual[int(key)]
                else:
                    actual = None
                    break

            if actual != expected_value:
                self.errors.append(
                    f"JSON路径 {path} 值不匹配: 期望 {expected_value}, 实际 {actual}")
        except json.JSONDecodeError:
            self.errors.append("响应不是有效的JSON")
        except Exception as e:
            self.errors.append(f"JSON路径验证失败: {e}")
        return self

    def is_success(self) -> 'ResponseValidator':
        """验证请求成功 (2xx状态码)"""
        if not (200 <= self.response.status_code < 300):
            self.errors.append(f"请求不成功: 状态码 {self.response.status_code}")
        return self

    def is_redirect(self) -> 'ResponseValidator':
        """验证是重定向 (3xx状态码)"""
        if not (300 <= self.response.status_code < 400):
            self.errors.append(f"不是重定向: 状态码 {self.response.status_code}")
        return self

    def is_client_error(self) -> 'ResponseValidator':
        """验证是客户端错误 (4xx状态码)"""
        if not (400 <= self.response.status_code < 500):
            self.errors.append(f"不是客户端错误: 状态码 {self.response.status_code}")
        return self

    def is_server_error(self) -> 'ResponseValidator':
        """验证是服务器错误 (5xx状态码)"""
        if not (500 <= self.response.status_code < 600):
            self.errors.append(f"不是服务器错误: 状态码 {self.response.status_code}")
        return self

    def validate(self) -> bool:
        """执行验证，如果有错误则抛出异常"""
        if self.errors:
            raise AssertionError("\n".join(self.errors))
        return True


class NginxTestClient:
    """Nginx测试专用客户端"""

    def __init__(self, nginx_host: str, nginx_port: int = 80):
        self.http_client = HttpClient(base_url=f"http://{nginx_host}:{nginx_port}")
        self.nginx_host = nginx_host
        self.nginx_port = nginx_port

    def send_request_with_host(self, host: str, path: str = "/", **kwargs) -> requests.Response:
        """发送带Host头的请求"""
        headers = kwargs.pop('headers', {})
        headers['Host'] = host
        return self.http_client.get(path, headers=headers, **kwargs)

    def get_response_headers(self, path: str = "/", **kwargs) -> Dict[str, str]:
        """获取响应头"""
        response = self.http_client.get(path, **kwargs)
        return dict(response.headers)

    def check_header_from_backend(self, header_name: str, path: str = "/", **kwargs) -> Optional[str]:
        """
        通过后端Mock服务检查收到的请求头
        这需要后端服务返回它收到的请求头
        """
        response = self.http_client.get(path, **kwargs)
        try:
            data = response.json()
            headers = data.get('headers', {})
            return headers.get(header_name)
        except:
            return None

    def close(self):
        """关闭客户端"""
        self.http_client.close()


# 便捷函数
def simple_get(url: str, timeout: int = 30) -> requests.Response:
    """简单的GET请求"""
    return requests.get(url, timeout=timeout)


def simple_post(url: str, data=None, json=None, timeout: int = 30) -> requests.Response:
    """简单的POST请求"""
    return requests.post(url, data=data, json=json, timeout=timeout)
