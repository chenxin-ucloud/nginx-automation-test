"""
Nginx配置管理模块
用于管理Nginx配置的备份、部署、验证和恢复
"""

import os
import time
from typing import Optional
from .remote_executor import RemoteExecutor


class NginxManager:
    """Nginx配置管理器"""

    def __init__(self, ssh_client: RemoteExecutor, config_path: str = "/etc/nginx/nginx.conf",
                 backup_path: str = "/etc/nginx/nginx.conf.bak"):
        self.ssh = ssh_client
        self.config_path = config_path
        self.backup_path = backup_path
        self.temp_test_path = "/tmp/nginx_test.conf"

    def backup_config(self) -> bool:
        """备份当前Nginx配置"""
        result = self.ssh.exec(f"cp {self.config_path} {self.backup_path}")
        if result['returncode'] != 0:
            # 如果文件不存在，创建一个空备份
            result = self.ssh.exec(f"touch {self.backup_path}")
        return result['returncode'] == 0

    def restore_config(self) -> bool:
        """恢复Nginx配置到备份版本"""
        result = self.ssh.exec(f"cp {self.backup_path} {self.config_path}")
        return result['returncode'] == 0

    def deploy_config(self, config_content: str) -> bool:
        """
        部署新的Nginx配置

        Args:
            config_content: Nginx配置文件内容

        Returns:
            是否部署成功
        """
        # 先验证语法
        if not self.validate_syntax(config_content):
            return False

        # 上传配置
        if not self.ssh.upload(config_content, self.config_path):
            return False

        return True

    def validate_syntax(self, config_content: str) -> bool:
        """
        验证Nginx配置语法

        Args:
            config_content: 要验证的配置内容

        Returns:
            语法是否正确
        """
        # 上传临时配置文件
        if not self.ssh.upload(config_content, self.temp_test_path):
            return False

        # 测试语法
        result = self.ssh.exec(f"nginx -t -c {self.temp_test_path}")

        # 清理临时文件
        self.ssh.exec(f"rm -f {self.temp_test_path}")

        return result['returncode'] == 0

    def reload(self) -> bool:
        """重载Nginx配置"""
        result = self.ssh.exec("nginx -t && nginx -s reload")
        return result['returncode'] == 0

    def restart(self) -> bool:
        """重启Nginx服务"""
        result = self.ssh.exec("systemctl restart nginx")
        return result['returncode'] == 0

    def start(self) -> bool:
        """启动Nginx服务"""
        result = self.ssh.exec("systemctl start nginx")
        return result['returncode'] == 0

    def stop(self) -> bool:
        """停止Nginx服务"""
        result = self.ssh.exec("systemctl stop nginx")
        return result['returncode'] == 0

    def check_status(self) -> dict:
        """检查Nginx状态"""
        result = self.ssh.exec("systemctl status nginx")
        is_running = result['returncode'] == 0 and 'active (running)' in result['stdout']

        # 获取进程信息
        pid_result = self.ssh.exec("pgrep -x nginx | wc -l")
        worker_count = int(pid_result['stdout'].strip()) if pid_result['returncode'] == 0 else 0

        return {
            'running': is_running,
            'worker_count': worker_count,
            'raw_output': result['stdout']
        }

    def get_config(self) -> str:
        """获取当前Nginx配置内容"""
        result = self.ssh.exec(f"cat {self.config_path}")
        return result['stdout'] if result['returncode'] == 0 else ""

    def get_error_log(self, lines: int = 50) -> str:
        """获取Nginx错误日志"""
        result = self.ssh.exec(f"tail -n {lines} /var/log/nginx/error.log")
        return result['stdout'] if result['returncode'] == 0 else ""

    def get_access_log(self, lines: int = 50) -> str:
        """获取Nginx访问日志"""
        result = self.ssh.exec(f"tail -n {lines} /var/log/nginx/access.log")
        return result['stdout'] if result['returncode'] == 0 else ""

    def clear_logs(self) -> bool:
        """清空Nginx日志"""
        result = self.ssh.exec("> /var/log/nginx/access.log && > /var/log/nginx/error.log")
        return result['returncode'] == 0

    def wait_for_reload(self, timeout: int = 10) -> bool:
        """等待Nginx重载完成"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.check_status()
            if status['running']:
                return True
            time.sleep(0.5)
        return False


class NginxConfigBuilder:
    """Nginx配置构建器"""

    def __init__(self):
        self.config_lines = []

    def add_line(self, line: str, indent: int = 0):
        """添加配置行"""
        self.config_lines.append("    " * indent + line)
        return self

    def add_block(self, name: str, content_func, indent: int = 0):
        """添加配置块"""
        self.add_line(f"{name} {{", indent)
        content_func(self, indent + 1)
        self.add_line("}", indent)
        return self

    def build(self) -> str:
        """构建完整配置"""
        return "\n".join(self.config_lines)

    @staticmethod
    def create_basic_config(upstream_servers: list, listen_port: int = 80) -> str:
        """创建基础Nginx配置"""
        builder = NginxConfigBuilder()

        # 全局配置
        builder.add_line("user nginx;")
        builder.add_line("worker_processes auto;")
        builder.add_line("error_log /var/log/nginx/error.log;")
        builder.add_line("pid /run/nginx.pid;")
        builder.add_line("")

        # events块
        builder.add_block("events", lambda b, i: b.add_line("worker_connections 1024;", i))
        builder.add_line("")

        # http块
        def http_content(b, i):
            b.add_line("log_format main '$remote_addr - $remote_user [$time_local] \"$request\" '", i)
            b.add_line("                  '$status $body_bytes_sent \"$http_referer\" '", i)
            b.add_line("                  '\"$http_user_agent\" \"$http_x_forwarded_for\"';", i)
            b.add_line("access_log /var/log/nginx/access.log main;", i)
            b.add_line("")

            # upstream块
            if upstream_servers:
                b.add_block("upstream backend_servers", lambda b2, i2: [
                    b2.add_line(f"server {server};", i2) for server in upstream_servers
                ], i)
                b.add_line("")

            # server块
            def server_content(b2, i2):
                b2.add_line(f"listen {listen_port};", i2)
                b2.add_line("server_name _;", i2)
                b2.add_line("")
                b2.add_line("location / {", i2)
                b2.add_line("    proxy_pass http://backend_servers;" if upstream_servers else "    proxy_pass http://127.0.0.1:8080;", i2)
                b2.add_line("    proxy_set_header Host $host;", i2)
                b2.add_line("    proxy_set_header X-Real-IP $remote_addr;", i2)
                b2.add_line("    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;", i2)
                b2.add_line("}", i2)

            b.add_block("server", server_content, i)

        builder.add_block("http", http_content)

        return builder.build()


# 常用配置模板
NGINX_TEMPLATES = {
    'basic': '''user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://{backend};
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}''',

    'upstream': '''user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    upstream backend_servers {
        {upstream_servers}
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://backend_servers;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}''',

    'grpc': '''user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;

    server {
        listen {port} http2;
        server_name localhost;

        location / {
            grpc_pass grpc://{grpc_backend};
            {grpc_headers}
        }
    }
}'''
}
