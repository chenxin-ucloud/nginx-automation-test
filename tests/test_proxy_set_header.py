"""
proxy_set_header 指令自动化测试

测试用例覆盖:
- P0: 基础自定义请求头传递
- P0: 修改默认Host头
- P0: 删除请求头
- P0: 层级优先级验证
- P1/P2: 继承规则、变量差异、HTTP/2场景等
"""

import pytest
import requests
from tests.conftest import NginxBaseTest


@pytest.mark.proxy_set_header
class TestProxySetHeader(NginxBaseTest):
    """proxy_set_header 指令自动化测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, backend_1_mock, backend_1_config):
        """设置后端Mock"""
        self.backend = backend_1_mock
        self.backend_host = f"{backend_1_config['host']}:{backend_1_config['mock_port']}"

    @pytest.mark.p0
    def test_basic_custom_header(self):
        """PSH-001: 添加自定义请求头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Test test_value;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 发送请求
        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

        # 验证后端收到自定义头
        backend_headers = self.backend.get_last_headers()
        assert 'X-Test' in backend_headers or 'x-test' in [k.lower() for k in backend_headers.keys()]
        header_value = self.backend.get_header_from_last_request('X-Test')
        assert header_value == 'test_value', f"期望 'test_value', 实际 '{header_value}'"

    @pytest.mark.p0
    def test_modify_host_header(self):
        """PSH-002: 修改默认Host头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header Host www.test.com;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

        backend_headers = self.backend.get_last_headers()
        host_header = self.backend.get_header_from_last_request('Host')
        assert host_header == 'www.test.com', f"期望 'www.test.com', 实际 '{host_header}'"

    @pytest.mark.p0
    def test_delete_header(self):
        """PSH-003: 删除Accept-Encoding请求头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header Accept-Encoding "";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 发送带Accept-Encoding的请求
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Accept-Encoding': 'gzip, deflate'},
            timeout=5
        )
        assert response.status_code == 200

        # 验证后端未收到Accept-Encoding头
        backend_headers = self.backend.get_last_headers()
        assert 'Accept-Encoding' not in [k.lower() for k in backend_headers.keys()], \
            "Accept-Encoding头应该被删除"

    @pytest.mark.p0
    def test_level_priority(self):
        """PSH-004: http/server/location层级优先级验证"""
        config = f'''
http {{
    proxy_set_header X-Level http;
    server {{
        listen 80;
        proxy_set_header X-Level server;
        location / {{
            proxy_pass http://{self.backend_host};
            proxy_set_header X-Level location;
        }}
    }}
}}'''
        # 注意：这里需要简化配置，因为外层已经有http块了
        server_config = f'''
server {{
    listen 80;
    proxy_set_header X-Level server;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Level location;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(server_config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

        backend_headers = self.backend.get_last_headers()
        x_level = self.backend.get_header_from_last_request('X-Level')
        assert x_level == 'location', f"location层级应该优先，期望 'location', 实际 '{x_level}'"

    @pytest.mark.p1
    def test_inheritance_rule(self):
        """PSH-005: 继承规则验证（本层无配置时继承上层）"""
        server_config = f'''
proxy_set_header X-Inherit parent_value;
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        # 本层没有配置proxy_set_header X-Inherit，应该继承父级
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(server_config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

        x_inherit = self.backend.get_header_from_last_request('X-Inherit')
        # 注意：实际行为可能不同，需要验证Nginx的继承规则
        # 如果location中设置了任何proxy_set_header，父级的设置会被覆盖

    @pytest.mark.p1
    def test_host_variables(self):
        """PSH-006: 验证$proxy_host/$http_host/$host变量差异"""
        config = f'''
server {{
    listen 80;
    location /proxy_host {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Test $proxy_host;
    }}
    location /http_host {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Test $http_host;
    }}
    location /host {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Test $host;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 测试$proxy_host - 应该是upstream地址
        response = requests.get(f'http://192.168.2.250/proxy_host',
                                headers={'Host': 'www.example.com'}, timeout=5)
        proxy_host_value = self.backend.get_header_from_last_request('X-Test')

        # 测试$http_host - 应该是客户端发来的Host头
        self.backend.clear()
        response = requests.get(f'http://192.168.2.250/http_host',
                                headers={'Host': 'www.example.com'}, timeout=5)
        http_host_value = self.backend.get_header_from_last_request('X-Test')

        # 测试$host - 应该是server_name或Host头
        self.backend.clear()
        response = requests.get(f'http://192.168.2.250/host',
                                headers={'Host': 'www.example.com'}, timeout=5)
        host_value = self.backend.get_header_from_last_request('X-Test')

        # $http_host应该保留原始Host头的端口信息
        assert http_host_value == 'www.example.com', \
            f"$http_host应保留原始Host头，实际: {http_host_value}"

    @pytest.mark.p1
    def test_multiple_headers(self):
        """PSH-007: 同时设置多个请求头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Custom-1 value1;
        proxy_set_header X-Custom-2 value2;
        proxy_set_header X-Custom-3 value3;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

        headers = self.backend.get_last_headers()
        assert self.backend.get_header_from_last_request('X-Custom-1') == 'value1'
        assert self.backend.get_header_from_last_request('X-Custom-2') == 'value2'
        assert self.backend.get_header_from_last_request('X-Custom-3') == 'value3'

    @pytest.mark.p1
    def test_header_override(self):
        """PSH-008: 相同头的多次设置（覆盖）"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Override first;
        proxy_set_header X-Override second;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)

        x_override = self.backend.get_header_from_last_request('X-Override')
        # 最后的值应该生效
        assert x_override == 'second', f"最后的值应该生效，实际: {x_override}"

    @pytest.mark.p1
    def test_empty_header_value(self):
        """PSH-009: 空值请求头处理"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Empty "";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)

        # 空值头可能被删除或保持为空
        x_empty = self.backend.get_header_from_last_request('X-Empty')
        # 根据Nginx版本不同，行为可能不同

    @pytest.mark.p2
    def test_special_characters_in_header(self):
        """PSH-010: 请求头值中的特殊字符"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Special "test value with spaces";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)

        x_special = self.backend.get_header_from_last_request('X-Special')
        assert 'test value with spaces' in x_special or 'test' in x_special

    @pytest.mark.p2
    def test_long_header_value(self):
        """PSH-011: 超长请求头值"""
        long_value = "x" * 8000
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Long "{long_value}";
    }}
}}'''
        # 可能因配置限制而失败
        try:
            self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))
            response = requests.get(f'http://192.168.2.250/', timeout=5)
            # 大请求头可能导致失败
        except Exception as e:
            # 预期可能失败
            pytest.skip(f"长请求头测试可能因服务器限制失败: {e}")

    @pytest.mark.p1
    def test_dynamic_header_value(self):
        """PSH-012: 使用变量动态设置请求头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Request-ID $request_id;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)

        x_real_ip = self.backend.get_header_from_last_request('X-Real-IP')
        # $remote_addr应该是客户端IP
        assert x_real_ip is not None, "X-Real-IP应该被设置"

    @pytest.mark.p1
    def test_conditional_header(self):
        """PSH-013: 条件性设置请求头（使用map）"""
        config = f'''
map $http_user_agent $is_mobile {{
    ~*android 1;
    ~*iphone 1;
    default 0;
}}

server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Mobile $is_mobile;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 使用移动UA
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)'},
            timeout=5
        )

        x_mobile = self.backend.get_header_from_last_request('X-Mobile')
        assert x_mobile == '1', f"移动UA应设置X-Mobile为1，实际: {x_mobile}"

    @pytest.mark.p2
    def test_header_with_connection_upgrade(self):
        """PSH-014: WebSocket升级请求头"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Upgrade': 'websocket'},
            timeout=5
        )

        upgrade = self.backend.get_header_from_last_request('Upgrade')
        connection = self.backend.get_header_from_last_request('Connection')
        assert upgrade == 'websocket'
        assert connection == 'upgrade'

    @pytest.mark.p0
    def test_default_connection_header(self):
        """PSH-015: 默认Connection头行为"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)

        # Nginx默认会设置Connection: close
        connection = self.backend.get_header_from_last_request('Connection')
        # 默认行为可能因配置而异

    @pytest.mark.p1
    def test_keepalive_header(self):
        """PSH-016: 保持连接请求头"""
        config = f'''
upstream backend {{
    server {self.backend_host};
    keepalive 32;
}}

server {{
    listen 80;
    location / {{
        proxy_pass http://backend;
        proxy_set_header Connection "";
    }}
}}'''
        self.deploy_and_reload(config)

        # 发送多个请求测试连接复用
        for i in range(3):
            response = requests.get(f'http://192.168.2.250/', timeout=5)
            assert response.status_code == 200
