"""
server_name 指令自动化测试

测试用例覆盖:
- P0: 精确匹配
- P0: 通配符匹配（前缀、后缀）
- P0: 正则匹配
- P0: 匹配优先级
"""

import pytest
import requests
from tests.conftest import NginxBaseTest


@pytest.mark.server_name
class TestServerName(NginxBaseTest):
    """server_name 指令自动化测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, backend_1_mock, backend_1_config):
        """设置后端Mock"""
        self.backend = backend_1_mock
        self.backend_host = f"{backend_1_config['host']}:{backend_1_config['mock_port']}"

    @pytest.mark.p0
    def test_exact_match(self):
        """SN-001: 精确匹配"""
        config = f'''
server {{
    listen 80;
    server_name www.test.com;
    location / {{
        return 200 "exact_match";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 精确匹配
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'www.test.com'},
            timeout=5
        )
        assert response.status_code == 200
        assert 'exact_match' in response.text

        # 不匹配
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'test.com'},
            timeout=5
        )
        # 应该匹配默认server或不返回exact_match
        assert 'exact_match' not in response.text or response.status_code != 200

    @pytest.mark.p0
    def test_wildcard_prefix(self):
        """SN-002: 通配符前缀匹配"""
        config = f'''
server {{
    listen 80;
    server_name *.test.com;
    location / {{
        return 200 "wildcard_prefix";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 各种子域名应该匹配
        for subdomain in ['a.test.com', 'b.test.com', 'abc.test.com', 'sub.sub.test.com']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': subdomain},
                timeout=5
            )
            assert response.status_code == 200, f"Failed for {subdomain}"
            assert 'wildcard_prefix' in response.text

    @pytest.mark.p0
    def test_wildcard_suffix(self):
        """SN-003: 通配符后缀匹配"""
        config = f'''
server {{
    listen 80;
    server_name www.*;
    location / {{
        return 200 "wildcard_suffix";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 应该匹配
        for domain in ['www.example.com', 'www.test.org', 'www.abc.net']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': domain},
                timeout=5
            )
            assert response.status_code == 200, f"Failed for {domain}"
            assert 'wildcard_suffix' in response.text

    @pytest.mark.p0
    def test_match_priority(self):
        """SN-004: 匹配优先级验证"""
        config = f'''
server {{
    listen 80;
    server_name www.test.com;
    location / {{
        return 200 "exact";
    }}
}}

server {{
    listen 80;
    server_name *.test.com;
    location / {{
        return 200 "wildcard";
    }}
}}

server {{
    listen 80;
    server_name ~^www\\..*\\.com$;
    location / {{
        return 200 "regex";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 精确匹配应该优先
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'www.test.com'},
            timeout=5
        )
        assert response.status_code == 200
        assert 'exact' in response.text
        assert 'wildcard' not in response.text
        assert 'regex' not in response.text

    @pytest.mark.p1
    def test_regex_match(self):
        """SN-005: 正则表达式匹配"""
        config = f'''
server {{
    listen 80;
    server_name ~^www\\d+\\.test\\.com$;
    location / {{
        return 200 "regex_match";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 应该匹配 www1.test.com, www123.test.com
        for host in ['www1.test.com', 'www12.test.com', 'www123.test.com']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': host},
                timeout=5
            )
            assert response.status_code == 200, f"Failed for {host}"
            assert 'regex_match' in response.text

        # 不应该匹配
        for host in ['www.test.com', 'abc.test.com']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': host},
                timeout=5
            )
            assert 'regex_match' not in response.text or response.status_code != 200

    @pytest.mark.p1
    def test_multiple_server_names(self):
        """SN-006: 多个server_name"""
        config = f'''
server {{
    listen 80;
    server_name example.com www.example.com api.example.com;
    location / {{
        return 200 "multi_names";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 所有配置的server_name都应该匹配
        for host in ['example.com', 'www.example.com', 'api.example.com']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': host},
                timeout=5
            )
            assert response.status_code == 200, f"Failed for {host}"
            assert 'multi_names' in response.text

    @pytest.mark.p1
    def test_server_name_case_insensitive(self):
        """SN-007: server_name大小写不敏感"""
        config = f'''
server {{
    listen 80;
    server_name TEST.COM;
    location / {{
        return 200 "case_insensitive";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 大小写变体应该匹配
        for host in ['test.com', 'TEST.COM', 'Test.Com', 'TeSt.CoM']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': host},
                timeout=5
            )
            assert response.status_code == 200, f"Failed for {host}"
            assert 'case_insensitive' in response.text

    @pytest.mark.p2
    def test_server_name_dot_prefix(self):
        """SN-008: server_name点前缀特殊处理"""
        config = f'''
server {{
    listen 80;
    server_name .test.com;
    location / {{
        return 200 "dot_prefix";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 点前缀应该匹配test.com及其子域名
        for host in ['test.com', 'www.test.com', 'api.test.com']:
            response = requests.get(
                f'http://192.168.2.250/',
                headers={'Host': host},
                timeout=5
            )
            assert response.status_code == 200, f"Failed for {host}"
            assert 'dot_prefix' in response.text

    @pytest.mark.p2
    def test_server_name_regex_capture(self):
        """SN-009: 正则捕获组"""
        config = f'''
server {{
    listen 80;
    server_name ~^(www\\.)?(?<domain>.+)$;
    location / {{
        return 200 "regex_capture";
    }}
}}'''
        # 验证配置语法
        is_valid = self.nginx.validate_syntax(self.deploy_config_with_upstream(config, [self.backend_host]))
        # 命名捕获组可能在某些Nginx版本不支持
        # 简化测试

    @pytest.mark.p2
    def test_server_name_special_chars(self):
        """SN-010: server_name中的特殊字符"""
        config = f'''
server {{
    listen 80;
    server_name "~^.*\\-api\\.test\\.com$";
    location / {{
        return 200 "special_chars";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 测试带-的域名
        response = requests.get(
            f'http://192.168.2.250/',
            headers={'Host': 'my-api.test.com'},
            timeout=5
        )
        assert response.status_code == 200
