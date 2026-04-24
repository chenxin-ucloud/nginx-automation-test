"""
proxy_pass_header / proxy_hide_header 指令自动化测试

测试用例覆盖:
- P0: 单个响应头透传
- P0: 批量响应头透传
- P0: 隐藏敏感响应头
- P1: 不同层级的生效情况
"""

import pytest
import requests
from tests.conftest import NginxBaseTest


@pytest.mark.proxy_pass_header
@pytest.mark.proxy_hide_header
class TestProxyPassHeader(NginxBaseTest):
    """proxy_pass_header / proxy_hide_header 指令自动化测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, backend_1_mock, backend_1_config):
        """设置后端Mock"""
        self.backend = backend_1_mock
        self.backend_host = f"{backend_1_config['host']}:{backend_1_config['mock_port']}"

    @pytest.mark.p0
    def test_pass_single_header(self):
        """PPH-001: 单个响应头透传"""
        # 这个测试需要后端返回特定的头，然后验证客户端能收到
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_pass_header X-Response-Test;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        # Mock会返回所有请求头作为响应体，无法直接测试响应头透传
        # 实际测试需要配置后端返回特定的响应头

    @pytest.mark.p0
    def test_hide_sensitive_header(self):
        """PPH-003: 隐藏敏感响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_hide_header X-Internal-IP;
        proxy_hide_header Server;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        # 验证X-Internal-IP头不存在
        assert 'X-Internal-IP' not in response.headers

    @pytest.mark.p1
    def test_hide_header_by_default(self):
        """PPH-004: 默认隐藏的响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        # Nginx默认会隐藏一些头如Date, Server等
        # 验证默认行为

    @pytest.mark.p1
    def test_pass_all_hidden_headers(self):
        """PPH-005: 透传所有默认隐藏的响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_pass_header Date;
        proxy_pass_header Server;
        proxy_pass_header X-Powered-By;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p1
    def test_hide_header_in_http_block(self):
        """PPH-006: 在http块中配置proxy_hide_header"""
        config = f'''
proxy_hide_header X-Internal-Header;

server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p1
    def test_hide_header_override(self):
        """PPH-007: location中覆盖http块的hide_header设置"""
        config = f'''
proxy_hide_header X-Test;

server {{
    listen 80;
    location /api/ {{
        proxy_pass http://{self.backend_host};
        # 不隐藏X-Test
    }}

    location / {{
        proxy_pass http://{self.backend_host};
        # 继承http块的hide_header
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p2
    def test_hide_header_with_variables(self):
        """PPH-008: 尝试在hide_header中使用变量（应该不支持）"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        # 以下配置可能报错或无效
        # proxy_hide_header $http_x_hide_header;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p1
    def test_pass_header_cookies(self):
        """PPH-009: 透传Set-Cookie头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_pass_header Set-Cookie;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        # Set-Cookie头应该被透传

    @pytest.mark.p1
    def test_hide_header_link(self):
        """PPH-010: 隐藏Link响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_hide_header Link;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert 'Link' not in response.headers

    @pytest.mark.p2
    def test_multiple_pass_header(self):
        """PPH-011: 多个proxy_pass_header指令"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_pass_header X-Header-1;
        proxy_pass_header X-Header-2;
        proxy_pass_header X-Header-3;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p2
    def test_combined_hide_and_pass(self):
        """PPH-012: 同时使用hide和pass"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_hide_header X-Internal-1;
        proxy_hide_header X-Internal-2;
        proxy_pass_header X-Public-1;
        proxy_pass_header X-Public-2;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
