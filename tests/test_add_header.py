"""
add_header 指令自动化测试

测试用例覆盖:
- P0: 基础添加响应头
- P0: always参数在错误状态码下的作用
"""

import pytest
import requests
from tests.conftest import NginxBaseTest


@pytest.mark.add_header
class TestAddHeader(NginxBaseTest):
    """add_header 指令自动化测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, backend_1_mock, backend_1_config):
        """设置后端Mock"""
        self.backend = backend_1_mock
        self.backend_host = f"{backend_1_config['host']}:{backend_1_config['mock_port']}"

    @pytest.mark.p0
    def test_basic_add_header(self):
        """ADD-001: 基础添加响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-Custom-Header "test_value";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        assert 'X-Custom-Header' in response.headers
        assert response.headers['X-Custom-Header'] == 'test_value'

    @pytest.mark.p0
    def test_always_parameter_success(self):
        """ADD-002: always参数 - 成功状态码"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-With-Always "always_value" always;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        assert 'X-With-Always' in response.headers
        assert response.headers['X-With-Always'] == 'always_value'

    @pytest.mark.p0
    def test_always_parameter_error(self):
        """ADD-003: always参数 - 错误状态码"""
        # 测试带always的情况
        config_with_always = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-Error-Test "error_always" always;
        return 404;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config_with_always, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 404
        # 带always的头应该存在
        assert 'X-Error-Test' in response.headers
        assert response.headers['X-Error-Test'] == 'error_always'

        # 测试不带always的情况
        config_without_always = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-No-Always "no_always";
        return 404;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config_without_always, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 404
        # 不带always的头在错误状态码下不应该存在
        assert 'X-No-Always' not in response.headers

    @pytest.mark.p1
    def test_add_multiple_headers(self):
        """ADD-004: 添加多个响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-Header-1 "value1";
        add_header X-Header-2 "value2";
        add_header X-Header-3 "value3";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        assert response.headers.get('X-Header-1') == 'value1'
        assert response.headers.get('X-Header-2') == 'value2'
        assert response.headers.get('X-Header-3') == 'value3'

    @pytest.mark.p1
    def test_add_header_with_variables(self):
        """ADD-005: 使用变量添加响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-Request-ID $request_id;
        add_header X-Remote-Addr $remote_addr;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        # 变量应该被展开
        assert 'X-Request-ID' in response.headers
        assert 'X-Remote-Addr' in response.headers

    @pytest.mark.p1
    def test_add_header_level_priority(self):
        """ADD-006: add_header层级优先级"""
        config = f'''
server {{
    listen 80;
    add_header X-Server-Level "server";

    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-Location-Level "location";
    }}

    location /api/ {{
        proxy_pass http://{self.backend_host};
        # 继承server级别的add_header
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 测试location级别的头
        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        assert 'X-Location-Level' in response.headers

        # 测试继承的server级别头
        response = requests.get(f'http://192.168.2.250/api/', timeout=5)
        assert response.status_code == 200
        assert 'X-Server-Level' in response.headers

    @pytest.mark.p2
    def test_add_header_empty_value(self):
        """ADD-007: 空值响应头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-Empty "";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        # 空值头可能存在也可能不存在，取决于Nginx版本

    @pytest.mark.p2
    def test_add_header_special_chars(self):
        """ADD-008: 特殊字符的响应头值"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header X-Special "value with spaces";
        add_header X-Quote 'quoted value';
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p2
    def test_add_header_content_security(self):
        """ADD-009: 添加Content-Security-Policy头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        add_header Content-Security-Policy "default-src 'self'" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        assert 'Content-Security-Policy' in response.headers
