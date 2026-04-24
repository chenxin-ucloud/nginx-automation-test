"""
结果验证模块
用于验证测试结果的各种断言函数
"""

import re
import time
from typing import Dict, List, Optional, Any, Union, Callable


class ValidationError(Exception):
    """验证错误异常"""
    pass


class HeaderValidator:
    """请求/响应头验证器"""

    def __init__(self, headers: Dict[str, str]):
        # 统一转换为小写键便于比较
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.errors = []

    def exists(self, header_name: str) -> 'HeaderValidator':
        """验证头存在"""
        if header_name.lower() not in self.headers:
            self.errors.append(f"头 '{header_name}' 不存在")
        return self

    def not_exists(self, header_name: str) -> 'HeaderValidator':
        """验证头不存在"""
        if header_name.lower() in self.headers:
            self.errors.append(f"头 '{header_name}' 不应该存在，但值为: {self.headers[header_name.lower()]}")
        return self

    def equals(self, header_name: str, expected_value: str) -> 'HeaderValidator':
        """验证头值等于期望值"""
        actual = self.headers.get(header_name.lower())
        if actual != expected_value:
            self.errors.append(f"头 '{header_name}' 值不匹配: 期望 '{expected_value}', 实际 '{actual}'")
        return self

    def contains(self, header_name: str, substring: str) -> 'HeaderValidator':
        """验证头值包含子串"""
        actual = self.headers.get(header_name.lower(), '')
        if substring not in actual:
            self.errors.append(f"头 '{header_name}' 不包含 '{substring}': 实际 '{actual}'")
        return self

    def matches(self, header_name: str, pattern: str) -> 'HeaderValidator':
        """验证头值匹配正则表达式"""
        actual = self.headers.get(header_name.lower(), '')
        if not re.search(pattern, actual):
            self.errors.append(f"头 '{header_name}' 不匹配模式 '{pattern}': 实际 '{actual}'")
        return self

    def starts_with(self, header_name: str, prefix: str) -> 'HeaderValidator':
        """验证头值以指定前缀开头"""
        actual = self.headers.get(header_name.lower(), '')
        if not actual.startswith(prefix):
            self.errors.append(f"头 '{header_name}' 不以 '{prefix}' 开头: 实际 '{actual}'")
        return self

    def ends_with(self, header_name: str, suffix: str) -> 'HeaderValidator':
        """验证头值以指定后缀结尾"""
        actual = self.headers.get(header_name.lower(), '')
        if not actual.endswith(suffix):
            self.errors.append(f"头 '{header_name}' 不以 '{suffix}' 结尾: 实际 '{actual}'")
        return self

    def in_list(self, header_name: str, allowed_values: List[str]) -> 'HeaderValidator':
        """验证头值在允许列表中"""
        actual = self.headers.get(header_name.lower())
        if actual not in allowed_values:
            self.errors.append(f"头 '{header_name}' 值 '{actual}' 不在允许列表 {allowed_values} 中")
        return self

    def validate(self) -> bool:
        """执行验证，如果有错误则抛出异常"""
        if self.errors:
            raise ValidationError("\n".join(self.errors))
        return True


class ResponseValidator:
    """HTTP响应验证器"""

    def __init__(self, status_code: int, headers: Dict[str, str], body: str = ""):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.errors = []

    def status_is(self, expected: int) -> 'ResponseValidator':
        """验证状态码"""
        if self.status_code != expected:
            self.errors.append(f"状态码不匹配: 期望 {expected}, 实际 {self.status_code}")
        return self

    def status_in(self, expected_codes: List[int]) -> 'ResponseValidator':
        """验证状态码在列表中"""
        if self.status_code not in expected_codes:
            self.errors.append(f"状态码 {self.status_code} 不在期望列表 {expected_codes} 中")
        return self

    def status_is_success(self) -> 'ResponseValidator':
        """验证状态码为2xx"""
        if not (200 <= self.status_code < 300):
            self.errors.append(f"期望成功状态码 (2xx), 实际 {self.status_code}")
        return self

    def body_contains(self, substring: str) -> 'ResponseValidator':
        """验证响应体包含子串"""
        if substring not in self.body:
            self.errors.append(f"响应体不包含: '{substring}'")
        return self

    def body_equals(self, expected: str) -> 'ResponseValidator':
        """验证响应体完全匹配"""
        if self.body != expected:
            self.errors.append(f"响应体不匹配:\n期望: {repr(expected)}\n实际: {repr(self.body)}")
        return self

    def body_matches(self, pattern: str) -> 'ResponseValidator':
        """验证响应体匹配正则"""
        if not re.search(pattern, self.body):
            self.errors.append(f"响应体不匹配模式: '{pattern}'")
        return self

    def header(self, header_name: str) -> HeaderValidator:
        """获取头验证器"""
        return HeaderValidator(self.headers).exists(header_name)

    def validate(self) -> bool:
        """执行验证"""
        if self.errors:
            raise ValidationError("\n".join(self.errors))
        return True


class ConfigValidator:
    """Nginx配置验证器"""

    def __init__(self, config_content: str):
        self.config = config_content
        self.errors = []

    def contains_directive(self, directive: str) -> 'ConfigValidator':
        """验证配置包含指定指令"""
        if directive not in self.config:
            self.errors.append(f"配置中未找到指令: '{directive}'")
        return self

    def contains_block(self, block_name: str) -> 'ConfigValidator':
        """验证配置包含指定块"""
        pattern = rf'{re.escape(block_name)}\s*{{'
        if not re.search(pattern, self.config):
            self.errors.append(f"配置中未找到块: '{block_name}'")
        return self

    def matches_pattern(self, pattern: str) -> 'ConfigValidator':
        """验证配置匹配正则"""
        if not re.search(pattern, self.config):
            self.errors.append(f"配置不匹配模式: '{pattern}'")
        return self

    def validate(self) -> bool:
        """执行验证"""
        if self.errors:
            raise ValidationError("\n".join(self.errors))
        return True


# 便捷验证函数

def assert_header_exists(headers: Dict[str, str], header_name: str, msg: str = None):
    """断言头存在"""
    if header_name.lower() not in {k.lower(): v for k, v in headers.items()}:
        raise AssertionError(msg or f"头 '{header_name}' 不存在")


def assert_header_equals(headers: Dict[str, str], header_name: str, expected: str, msg: str = None):
    """断言头值等于期望值"""
    normalized = {k.lower(): v for k, v in headers.items()}
    actual = normalized.get(header_name.lower())
    if actual != expected:
        raise AssertionError(msg or f"头 '{header_name}' 值不匹配: 期望 '{expected}', 实际 '{actual}'")


def assert_header_not_exists(headers: Dict[str, str], header_name: str, msg: str = None):
    """断言头不存在"""
    if header_name.lower() in {k.lower(): v for k, v in headers.items()}:
        raise AssertionError(msg or f"头 '{header_name}' 不应该存在")


def assert_status_code(actual: int, expected: int, msg: str = None):
    """断言状态码"""
    if actual != expected:
        raise AssertionError(msg or f"状态码不匹配: 期望 {expected}, 实际 {actual}")


def assert_body_contains(body: str, substring: str, msg: str = None):
    """断言响应体包含子串"""
    if substring not in body:
        raise AssertionError(msg or f"响应体不包含: '{substring}'")


def wait_for_condition(condition_func: Callable[[], bool], timeout: int = 10,
                       interval: float = 0.5, msg: str = "条件未满足") -> bool:
    """等待条件满足"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    raise TimeoutError(f"{msg} (超时 {timeout}秒)")


def validate_backend_received_header(backend_headers: Dict[str, str],
                                     header_name: str,
                                     expected_value: Optional[str] = None) -> bool:
    """
    验证后端收到了指定的请求头

    Args:
        backend_headers: 后端收到的请求头
        header_name: 要验证的头名称
        expected_value: 期望值，None表示只验证存在性

    Returns:
        验证是否通过
    """
    validator = HeaderValidator(backend_headers)

    if expected_value is None:
        validator.exists(header_name)
    else:
        validator.equals(header_name, expected_value)

    try:
        validator.validate()
        return True
    except ValidationError:
        return False
