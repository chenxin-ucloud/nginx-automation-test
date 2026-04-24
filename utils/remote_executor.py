"""
SSH远程执行模块
用于通过SSH连接到远程机器执行命令和上传文件
"""

import paramiko
import time
from typing import Dict, Optional
from contextlib import contextmanager


class RemoteExecutor:
    """SSH远程执行器"""

    def __init__(self, host: str, username: str, password: str, port: int = 22, timeout: int = 30):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None

    def connect(self) -> bool:
        """建立SSH连接"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )
            return True
        except Exception as e:
            print(f"SSH连接失败 {self.host}: {e}")
            return False

    def disconnect(self):
        """关闭SSH连接"""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        if self.client:
            self.client.close()
            self.client = None

    def exec(self, command: str, timeout: int = 30, sudo: bool = False) -> Dict:
        """
        执行远程命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            sudo: 是否使用sudo

        Returns:
            Dict包含 stdout, stderr, returncode
        """
        if not self.client:
            if not self.connect():
                return {'stdout': '', 'stderr': 'Connection failed', 'returncode': -1}

        if sudo and self.username != 'root':
            command = f"echo '{self.password}' | sudo -S {command}"

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()

            return {
                'stdout': stdout.read().decode('utf-8', errors='ignore'),
                'stderr': stderr.read().decode('utf-8', errors='ignore'),
                'returncode': exit_code
            }
        except Exception as e:
            return {'stdout': '', 'stderr': str(e), 'returncode': -1}

    def upload(self, content: str, remote_path: str) -> bool:
        """上传字符串内容到远程文件"""
        if not self.client:
            if not self.connect():
                return False

        try:
            if not self.sftp:
                self.sftp = self.client.open_sftp()

            with self.sftp.file(remote_path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"上传文件失败 {remote_path}: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传本地文件到远程"""
        if not self.client:
            if not self.connect():
                return False

        try:
            if not self.sftp:
                self.sftp = self.client.open_sftp()

            self.sftp.put(local_path, remote_path)
            return True
        except Exception as e:
            print(f"上传文件失败 {local_path} -> {remote_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """下载远程文件到本地"""
        if not self.client:
            if not self.connect():
                return False

        try:
            if not self.sftp:
                self.sftp = self.client.open_sftp()

            self.sftp.get(remote_path, local_path)
            return True
        except Exception as e:
            print(f"下载文件失败 {remote_path}: {e}")
            return False

    def check_service(self, service_name: str) -> bool:
        """检查服务状态"""
        result = self.exec(f"systemctl is-active {service_name}")
        return result['returncode'] == 0 and 'active' in result['stdout']

    def restart_service(self, service_name: str) -> bool:
        """重启服务"""
        result = self.exec(f"systemctl restart {service_name}", sudo=True)
        return result['returncode'] == 0

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class RemoteExecutorPool:
    """远程执行器连接池"""

    def __init__(self):
        self._executors: Dict[str, RemoteExecutor] = {}

    def get_executor(self, name: str, host: str, username: str, password: str, port: int = 22) -> RemoteExecutor:
        """获取或创建执行器"""
        key = f"{name}@{host}"
        if key not in self._executors:
            self._executors[key] = RemoteExecutor(host, username, password, port)
        return self._executors[key]

    def close_all(self):
        """关闭所有连接"""
        for executor in self._executors.values():
            executor.disconnect()
        self._executors.clear()


# 全局连接池
_pool = RemoteExecutorPool()


def get_remote_executor(name: str, host: str, username: str, password: str, port: int = 22) -> RemoteExecutor:
    """获取远程执行器"""
    return _pool.get_executor(name, host, username, password, port)


def close_all_executors():
    """关闭所有远程连接"""
    _pool.close_all()
