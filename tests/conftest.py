"""
Pytest fixtures for Nginx automation tests
"""

import pytest
import yaml
import os
from pathlib import Path

from utils.remote_executor import RemoteExecutor, get_remote_executor
from utils.nginx_manager import NginxManager
from utils.backend_mock import RemoteBackendMock
from utils.http_client import HttpClient


# 加载配置
@pytest.fixture(scope="session")
def config():
    """加载测试配置"""
    config_path = Path(__file__).parent.parent / "config" / "hosts.yml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def nginx_config(config):
    """获取Nginx服务器配置"""
    return config['test_env']['nginx_server']


@pytest.fixture(scope="session")
def client_config(config):
    """获取客户端配置"""
    return config['test_env']['client']


@pytest.fixture(scope="session")
def backend_1_config(config):
    """获取后端节点1配置"""
    return config['test_env']['backend_1']


@pytest.fixture(scope="session")
def backend_2_config(config):
    """获取后端节点2配置"""
    return config['test_env']['backend_2']


@pytest.fixture(scope="session")
def network_config(config):
    """获取网络配置"""
    return config['network']


# SSH连接fixtures
@pytest.fixture(scope="function")
def nginx_ssh(nginx_config):
    """Nginx服务器SSH连接"""
    ssh = RemoteExecutor(
        host=nginx_config['host'],
        username=nginx_config['username'],
        password=nginx_config['password'],
        port=nginx_config['port']
    )
    ssh.connect()
    yield ssh
    ssh.disconnect()


@pytest.fixture(scope="function")
def client_ssh(client_config):
    """客户端SSH连接"""
    ssh = RemoteExecutor(
        host=client_config['host'],
        username=client_config['username'],
        password=client_config['password'],
        port=client_config['port']
    )
    ssh.connect()
    yield ssh
    ssh.disconnect()


@pytest.fixture(scope="function")
def backend_1_ssh(backend_1_config):
    """后端节点1 SSH连接"""
    ssh = RemoteExecutor(
        host=backend_1_config['host'],
        username=backend_1_config['username'],
        password=backend_1_config['password'],
        port=backend_1_config['port']
    )
    ssh.connect()
    yield ssh
    ssh.disconnect()


@pytest.fixture(scope="function")
def backend_2_ssh(backend_2_config):
    """后端节点2 SSH连接"""
    ssh = RemoteExecutor(
        host=backend_2_config['host'],
        username=backend_2_config['username'],
        password=backend_2_config['password'],
        port=backend_2_config['port']
    )
    ssh.connect()
    yield ssh
    ssh.disconnect()


# Nginx管理fixture
@pytest.fixture(scope="function")
def nginx_manager(nginx_ssh, nginx_config):
    """Nginx管理器"""
    return NginxManager(
        ssh_client=nginx_ssh,
        config_path=nginx_config['nginx_config_path'],
        backup_path=nginx_config['nginx_backup_path']
    )


# Mock服务fixtures
@pytest.fixture(scope="function")
def backend_1_mock(backend_1_ssh, backend_1_config):
    """后端节点1 Mock服务"""
    mock = RemoteBackendMock(backend_1_ssh, backend_1_config['mock_port'])
    mock.deploy()
    mock.start()
    yield mock
    mock.stop()


@pytest.fixture(scope="function")
def backend_2_mock(backend_2_ssh, backend_2_config):
    """后端节点2 Mock服务"""
    mock = RemoteBackendMock(backend_2_ssh, backend_2_config['mock_port'])
    mock.deploy()
    mock.start()
    yield mock
    mock.stop()


# HTTP客户端fixtures
@pytest.fixture(scope="function")
def http_client():
    """HTTP客户端"""
    client = HttpClient()
    yield client
    client.close()


@pytest.fixture(scope="function")
def nginx_client(nginx_config):
    """Nginx测试客户端"""
    from utils.http_client import NginxTestClient
    client = NginxTestClient(
        nginx_host=nginx_config['host'],
        nginx_port=80
    )
    yield client
    client.close()


# 基础测试类
class NginxBaseTest:
    """Nginx测试基类"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, nginx_manager, nginx_ssh):
        """每个测试用例的前置/后置处理"""
        self.nginx = nginx_manager
        self.ssh = nginx_ssh

        # 备份配置
        self.nginx.backup_config()

        yield

        # 恢复配置
        self.nginx.restore_config()
        self.nginx.reload()

    def deploy_and_reload(self, config: str) -> bool:
        """
        部署配置并重载Nginx

        Args:
            config: Nginx配置内容

        Returns:
            是否成功
        """
        # 验证语法
        if not self.nginx.validate_syntax(config):
            raise AssertionError("Nginx配置语法验证失败")

        # 部署配置
        if not self.nginx.deploy_config(config):
            raise AssertionError("Nginx配置部署失败")

        # 重载配置
        if not self.nginx.reload():
            raise AssertionError("Nginx配置重载失败")

        return True

    def deploy_config_with_upstream(self, server_config: str, upstream_servers: list = None) -> str:
        """
        构建包含upstream的完整配置

        Args:
            server_config: server块配置
            upstream_servers: upstream服务器列表

        Returns:
            完整配置内容
        """
        upstream_block = ""
        if upstream_servers:
            upstream_block = f"""
upstream backend_servers {{
    {'\n    '.join([f'server {s};' for s in upstream_servers])}
}}
"""

        full_config = f"""user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {{
    worker_connections 1024;
}}

http {{
    log_format main '$remote_addr - $remote_user [$time_local] \"$request\" '
                      '$status $body_bytes_sent \"$http_referer\" '
                      '\"$http_user_agent\" \"$http_x_forwarded_for\"';
    access_log /var/log/nginx/access.log main;

{upstream_block}

{server_config}
}}
"""
        return full_config
