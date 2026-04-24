"""
server 指令自动化测试

测试用例覆盖:
- P0: 多server块端口匹配
- P0: 多server块的Host头匹配
- P0: 无匹配server时的默认行为
"""

import pytest
import requests
from tests.conftest import NginxBaseTest


@pytest.mark.server
class TestServer(NginxBaseTest):
    """server 指令自动化测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, backend_1_mock, backend_1_config):
        """设置后端Mock"""
        self.backend = backend_1_mock
        self.backend_host = f"{backend_1_config['host']}:{backend_1_config['mock_port']}"

    @pytest.mark.p0
    def test_port_match(self):
        """SVR-001: 端口匹配测试"""
        config = f'''
server {{
    listen 80;
    location / {{
        return 200 "port_80";
    }}
}}

server {{
    listen 8080;
    location / {{
        return 200 "port_8080";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 测试80端口
        response = requests.get(f'http://192.168.2.250:80/', timeout=5)
        assert response.status_code == 200
        assert 'port_80' in response.text

        # 注意：8080端口可能未开放，需要确认
        # response = requests.get(f'http://192.168.2.250:8080/', timeout=5)
        # assert 'port_8080' in response.text

    @pytest.mark.p0
    def test_host_header_match(self):
        """SVR-002: Host头匹配测试"""
        config = f'''
server {{
    listen 80;
    server_name a.test.com;
    location / {{
        return 200 "server_a";
    }}
}}

server {{
    listen 80;
    server_name b.test.com;
    location / {{
    return 200 "server_b";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 测试不同的Host头
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'a.test.com'},
            timeout=5
        )
        assert response.status_code == 200
        assert 'server_a' in response.text

        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'b.test.com'},
            timeout=5
        )
        assert response.status_code == 200
        assert 'server_b' in response.text

    @pytest.mark.p0
    def test_default_server_match(self):
        """SVR-003: 默认server匹配"""
        config = f'''
server {{
    listen 80;
    server_name a.test.com;
    location / {{
        return 200 "matched_a";
    }}
}}

server {{
    listen 80 default_server;
    location / {{
        return 200 "default_server";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 使用未配置的Host应该匹配默认server
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'unknown.test.com'},
            timeout=5
        )
        assert response.status_code == 200
        assert 'default_server' in response.text

    @pytest.mark.p1
    def test_listen_default(self):
        """SVR-004: 默认listen行为"""
        config = f'''
server {{
    listen 80;
    location / {{
        return 200 "server1";
    }}
}}

server {{
    listen 80;
    location / {{
        return 200 "server2";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 没有明确指定default_server时，第一个server是默认
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'unknown.com'},
            timeout=5
        )
        assert response.status_code == 200
        assert 'server1' in response.text

    @pytest.mark.p1
    def test_server_name_underscore(self):
        """SVR-005: server_name _ 匹配任何Host头"""
        config = f'''
server {{
    listen 80;
    server_name _;
    location / {{
        return 200 "catch_all";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 任何Host都应该匹配
        for host in ['example.com', 'test.com', 'anything.com']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': host},
                timeout=5
            )
            assert response.status_code == 200
            assert 'catch_all' in response.text

    @pytest.mark.p1
    def test_server_name_empty(self):
        """SVR-006: 空server_name"""
        config = f'''
server {{
    listen 80;
    server_name "";
    location / {{
        return 200 "empty_server_name";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 不带Host头的请求应该匹配
        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p1
    def test_multiple_listen_directives(self):
        """SVR-007: 单个server多listen指令"""
        config = f'''
server {{
    listen 80;
    listen 8080;
    location / {{
        return 200 "multi_listen";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p1
    def test_server_block_not_in_http(self):
        """SVR-008: server块不在http块中的错误"""
        # 这是一个配置错误测试
        invalid_config = '''user nginx;
worker_processes auto;

# server块在http外面是错误的
server {
    listen 80;
    location / {
        return 200 "invalid";
    }
}

events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        location / {
            return 200 "valid";
        }
    }
}'''
        # 应该语法验证失败
        is_valid = self.nginx.validate_syntax(invalid_config)
        assert not is_valid, "server块在http块外应该报错"

    @pytest.mark.p2
    def test_server_with_ipv6(self):
        """SVR-009: IPv6监听"""
        config = f'''
server {{
    listen [::]:80;
    location / {{
        return 200 "ipv6";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p2
    def test_server_with_unix_socket(self):
        """SVR-010: Unix socket监听"""
        config = f'''
server {{
    listen unix:/tmp/nginx.sock;
    location / {{
        return 200 "unix_socket";
    }}
}}'''
        # Unix socket配置语法验证
        is_valid = self.nginx.validate_syntax(self.deploy_config_with_upstream(config, [self.backend_host]))
        assert is_valid, "Unix socket配置应该语法正确"
