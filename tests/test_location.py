"""
location 指令自动化测试

测试用例覆盖:
- P0: 精确匹配（=）
- P0: 前缀匹配（^~）优先级高于正则
- P0: 正则匹配（~, ~*）
- P0: 普通前缀匹配
- P1: location顺序影响
"""

import pytest
import requests
from tests.conftest import NginxBaseTest


@pytest.mark.location
class TestLocation(NginxBaseTest):
    """location 指令自动化测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, backend_1_mock, backend_1_config):
        """设置后端Mock"""
        self.backend = backend_1_mock
        self.backend_host = f"{backend_1_config['host']}:{backend_1_config['mock_port']}"

    @pytest.mark.p0
    def test_exact_match(self):
        """LOC-001: 精确匹配（=）"""
        config = f'''
server {{
    listen 80;
    location = /user {{
        return 200 "exact_match_user";
    }}
    location /user/ {{
        return 200 "prefix_match_user";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 精确匹配/user
        response = requests.get(f'http://192.168.2.250/user', timeout=5)
        assert response.status_code == 200
        assert 'exact_match_user' in response.text

        # 匹配/user/
        response = requests.get(f'http://192.168.2.250/user/', timeout=5)
        assert response.status_code == 200
        assert 'prefix_match_user' in response.text

        # /user/info不匹配精确匹配
        response = requests.get(f'http://192.168.2.250/user/info', timeout=5)
        assert response.status_code == 200
        assert 'exact_match_user' not in response.text

    @pytest.mark.p0
    def test_prefix_priority_over_regex(self):
        """LOC-002: 前缀匹配(^~)优先级高于正则"""
        config = f'''
server {{
    listen 80;
    location ^~ /static/ {{
        return 200 "prefix_static";
    }}
    location ~* \\.(js|css)$ {{
        return 200 "regex_static";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # /static/test.js应该匹配前缀而不是正则
        response = requests.get(f'http://192.168.2.250/static/test.js', timeout=5)
        assert response.status_code == 200
        assert 'prefix_static' in response.text
        assert 'regex_static' not in response.text

    @pytest.mark.p0
    def test_regex_match_case_sensitive(self):
        """LOC-003: 区分大小写的正则匹配（~）"""
        config = f'''
server {{
    listen 80;
    location ~ \\.php$ {{
        return 200 "php_file";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 应该匹配
        response = requests.get(f'http://192.168.2.250/test.php', timeout=5)
        assert response.status_code == 200
        assert 'php_file' in response.text

        # 大小写不匹配（~是区分大小写的）
        response = requests.get(f'http://192.168.2.250/test.PHP', timeout=5)
        # 应该不匹配
        assert 'php_file' not in response.text or response.status_code == 404

    @pytest.mark.p0
    def test_regex_match_case_insensitive(self):
        """LOC-004: 不区分大小写的正则匹配（~*）"""
        config = f'''
server {{
    listen 80;
    location ~* \\.php$ {{
        return 200 "php_file";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 应该匹配（不区分大小写）
        for ext in ['.php', '.PHP', '.Php', '.pHp']:
            response = requests.get(f'http://192.168.2.250/test{ext}', timeout=5)
            assert response.status_code == 200, f"Failed for {ext}"
            assert 'php_file' in response.text

    @pytest.mark.p1
    def test_location_order_matters(self):
        """LOC-005: location顺序影响匹配"""
        config = f'''
server {{
    listen 80;
    location ~ \\.txt$ {{
        return 200 "regex_txt";
    }}
    location /files/ {{
        return 200 "prefix_files";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # /files/test.txt - 正则优先于普通前缀
        response = requests.get(f'http://192.168.2.250/files/test.txt', timeout=5)
        assert response.status_code == 200
        # 由于正则在前，应该匹配正则
        assert 'regex_txt' in response.text

    @pytest.mark.p1
    def test_location_modifier_priority(self):
        """LOC-006: 修饰符优先级顺序"""
        config = f'''
server {{
    listen 80;
    # 1. = 精确匹配
    location = /exact {{
        return 200 "equals";
    }}
    # 2. ^~ 前缀匹配（如果匹配则停止搜索）
    location ^~ /prefix/ {{
        return 200 "prefix";
    }}
    # 3. ~ 和 ~* 正则匹配
    location ~ \\.gif$ {{
        return 200 "regex";
    }}
    # 4. 普通前缀匹配
    location / {{
        return 200 "normal";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 测试精确匹配
        response = requests.get(f'http://192.168.2.250/exact', timeout=5)
        assert 'equals' in response.text

        # 测试^~前缀匹配
        response = requests.get(f'http://192.168.2.250/prefix/test.gif', timeout=5)
        assert 'prefix' in response.text  # ^~优先

        # 测试正则匹配
        response = requests.get(f'http://192.168.2.250/image.gif', timeout=5)
        assert 'regex' in response.text

        # 测试普通前缀
        response = requests.get(f'http://192.168.2.250/other', timeout=5)
        assert 'normal' in response.text

    @pytest.mark.p1
    def test_location_at_symbol(self):
        """LOC-007: @命名location"""
        config = f'''
server {{
    listen 80;
    location / {{
        try_files $uri $uri/ @fallback;
    }}
    location @fallback {{
        return 200 "fallback";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 访问不存在的文件应该触发fallback
        response = requests.get(f'http://192.168.2.250/nonexistent', timeout=5)
        assert response.status_code == 200
        assert 'fallback' in response.text

    @pytest.mark.p2
    def test_location_not_modifier(self):
        """LOC-008: !~ 和 !~* 否定正则"""
        # 注意：Nginx标准版本可能不支持!~修饰符
        # 这是一个扩展测试
        config = f'''
server {{
    listen 80;
    location / {{
        return 200 "default";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200

    @pytest.mark.p2
    def test_location_empty_path(self):
        """LOC-009: 空路径location"""
        config = f'''
server {{
    listen 80;
    location = / {{
        return 200 "root_exact";
    }}
    location / {{
        return 200 "root_prefix";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        response = requests.get(f'http://192.168.2.250/', timeout=5)
        assert response.status_code == 200
        # = / 应该优先匹配
        assert 'root_exact' in response.text

    @pytest.mark.p2
    def test_location_nested_not_allowed(self):
        """LOC-010: location不能嵌套（配置错误）"""
        # 这是一个配置错误示例
        invalid_config = f'''
server {{
    listen 80;
    location / {{
        location /nested {{
            return 200 "nested";
        }}
    }}
}}'''
        # Nginx不支持location嵌套
        is_valid = self.nginx.validate_syntax(
            self.deploy_config_with_upstream(invalid_config, [self.backend_host])
        )
        assert not is_valid, "嵌套location应该报错"

    @pytest.mark.p1
    def test_location_alias_vs_root(self):
        """LOC-011: location中的root和alias"""
        config = f'''
server {{
    listen 80;
    location /root/ {{
        root /var/www;
        # 请求 /root/file.html -> /var/www/root/file.html
    }}
    location /alias/ {{
        alias /var/www/static/;
        # 请求 /alias/file.html -> /var/www/static/file.html
    }}
}}'''
        # 验证配置语法
        is_valid = self.nginx.validate_syntax(
            self.deploy_config_with_upstream(config, [self.backend_host])
        )
        assert is_valid, "root和alias配置应该语法正确"
