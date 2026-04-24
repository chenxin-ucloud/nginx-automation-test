"""
Nginx自动化测试工具模块
"""

from .remote_executor import RemoteExecutor, RemoteExecutorPool, get_remote_executor, close_all_executors
from .nginx_manager import NginxManager, NginxConfigBuilder, NGINX_TEMPLATES
from .http_client import HttpClient, ResponseValidator, NginxTestClient
from .backend_mock import BackendMock, RemoteBackendMock
from .validators import (
    HeaderValidator, ResponseValidator as ConfigResponseValidator,
    ConfigValidator, ValidationError,
    assert_header_exists, assert_header_equals, assert_header_not_exists,
    assert_status_code, assert_body_contains, wait_for_condition
)

__all__ = [
    'RemoteExecutor',
    'RemoteExecutorPool',
    'get_remote_executor',
    'close_all_executors',
    'NginxManager',
    'NginxConfigBuilder',
    'NGINX_TEMPLATES',
    'HttpClient',
    'ResponseValidator',
    'NginxTestClient',
    'BackendMock',
    'RemoteBackendMock',
    'HeaderValidator',
    'ConfigResponseValidator',
    'ConfigValidator',
    'ValidationError',
    'assert_header_exists',
    'assert_header_equals',
    'assert_header_not_exists',
    'assert_status_code',
    'assert_body_contains',
    'wait_for_condition',
]
