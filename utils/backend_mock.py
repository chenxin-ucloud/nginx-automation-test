"""
后端Mock服务模块
用于模拟后端服务器，捕获和返回请求信息
"""

import json
import threading
import time
from typing import Dict, List, Optional, Callable
from flask import Flask, request, jsonify
import logging


class BackendMock:
    """后端服务Mock - 用于捕获和返回请求头信息"""

    def __init__(self, port: int = 8080, host: str = '0.0.0.0'):
        self.app = Flask(__name__)
        self.port = port
        self.host = host
        self.server_thread: Optional[threading.Thread] = None
        self.received_requests: List[Dict] = []
        self._lock = threading.Lock()

        # 禁用Flask默认日志
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self.app.logger.setLevel(logging.ERROR)

        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""

        @self.app.route('/health')
        def health():
            """健康检查端点"""
            return jsonify({'status': 'ok', 'timestamp': time.time()})

        @self.app.route('/clear', methods=['POST'])
        def clear_requests():
            """清空记录的请求"""
            with self._lock:
                self.received_requests.clear()
            return jsonify({'status': 'cleared'})

        @self.app.route('/requests', methods=['GET'])
        def get_requests():
            """获取所有记录的请求"""
            with self._lock:
                return jsonify({
                    'count': len(self.received_requests),
                    'requests': self.received_requests
                })

        @self.app.route('/last-request', methods=['GET'])
        def get_last_request():
            """获取最后一条请求"""
            with self._lock:
                if self.received_requests:
                    return jsonify(self.received_requests[-1])
                return jsonify({'error': 'No requests recorded'}), 404

        @self.app.route('/echo', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
        def echo():
            """回声端点 - 返回请求的所有信息"""
            request_info = self._capture_request()
            with self._lock:
                self.received_requests.append(request_info)
            return jsonify(request_info)

        @self.app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
        @self.app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
        def catch_all(path):
            """捕获所有请求"""
            request_info = self._capture_request()
            with self._lock:
                self.received_requests.append(request_info)
            return jsonify(request_info)

    def _capture_request(self) -> Dict:
        """捕获当前请求的所有信息"""
        headers = dict(request.headers)
        # 移除一些Flask自动添加的头
        headers.pop('Content-Length', None)

        return {
            'path': request.path,
            'full_path': request.full_path,
            'method': request.method,
            'headers': headers,
            'args': dict(request.args),
            'form': dict(request.form) if request.form else {},
            'json': request.get_json(silent=True),
            'data': request.get_data(as_text=True),
            'remote_addr': request.remote_addr,
            'timestamp': time.time()
        }

    def start(self, threaded: bool = True) -> bool:
        """
        启动Mock服务

        Args:
            threaded: 是否在后台线程中运行
        """
        if threaded:
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            # 等待服务器启动
            time.sleep(1)
            return self.server_thread.is_alive()
        else:
            self._run_server()
            return True

    def _run_server(self):
        """运行服务器"""
        self.app.run(host=self.host, port=self.port, threaded=True, debug=False)

    def stop(self):
        """停止Mock服务（在线程模式下仅标记，无法真正停止Flask开发服务器）"""
        # Flask的开发服务器没有干净的停止方法
        pass

    def clear(self):
        """清空记录的请求"""
        with self._lock:
            self.received_requests.clear()

    def get_requests(self) -> List[Dict]:
        """获取所有记录的请求"""
        with self._lock:
            return self.received_requests.copy()

    def get_last_request(self) -> Optional[Dict]:
        """获取最后一条请求"""
        with self._lock:
            return self.received_requests[-1] if self.received_requests else None

    def get_last_headers(self) -> Dict[str, str]:
        """获取最后一条请求的请求头"""
        last_request = self.get_last_request()
        return last_request.get('headers', {}) if last_request else {}

    def get_request_count(self) -> int:
        """获取记录的请求数量"""
        with self._lock:
            return len(self.received_requests)

    def wait_for_request(self, timeout: int = 10) -> Optional[Dict]:
        """等待并获取一条请求"""
        start_time = time.time()
        initial_count = self.get_request_count()

        while time.time() - start_time < timeout:
            current_count = self.get_request_count()
            if current_count > initial_count:
                return self.get_last_request()
            time.sleep(0.1)

        return None

    def get_header_from_last_request(self, header_name: str) -> Optional[str]:
        """从最后一条请求中获取指定头的值"""
        headers = self.get_last_headers()
        # 尝试多种大小写形式
        for key in headers:
            if key.lower() == header_name.lower():
                return headers[key]
        return None


class RemoteBackendMock:
    """
    远程后端Mock服务管理器
    用于在远程机器上部署和管理Mock服务
    """

    def __init__(self, ssh_client, mock_port: int = 8080):
        self.ssh = ssh_client
        self.mock_port = mock_port
        self.remote_script_path = "/tmp/backend_mock.py"
        self.process_id: Optional[int] = None

    def deploy(self) -> bool:
        """部署Mock服务脚本到远程机器"""
        script_content = self._generate_mock_script()
        return self.ssh.upload(script_content, self.remote_script_path)

    def start(self) -> bool:
        """在远程机器上启动Mock服务"""
        # 检查端口是否被占用
        result = self.ssh.exec(f"lsof -ti:{self.mock_port}")
        if result['stdout'].strip():
            # 杀掉占用端口的进程
            self.ssh.exec(f"kill -9 {result['stdout'].strip()}")
            time.sleep(1)

        # 启动服务
        result = self.ssh.exec(
            f"nohup python3 {self.remote_script_path} --port {self.mock_port} > /tmp/mock.log 2>&1 &"
        )

        # 等待服务启动
        time.sleep(2)

        # 检查服务是否运行
        result = self.ssh.exec(f"lsof -ti:{self.mock_port}")
        if result['stdout'].strip():
            self.process_id = int(result['stdout'].strip().split('\n')[0])
            return True
        return False

    def stop(self) -> bool:
        """停止远程Mock服务"""
        if self.process_id:
            result = self.ssh.exec(f"kill -9 {self.process_id}")
            return result['returncode'] == 0

        # 尝试通过端口查找并停止
        result = self.ssh.exec(f"lsof -ti:{self.mock_port} | xargs kill -9")
        return result['returncode'] == 0

    def clear_requests(self) -> bool:
        """清空远程Mock记录的请求"""
        result = self.ssh.exec(
            f"curl -X POST http://localhost:{self.mock_port}/clear")
        return result['returncode'] == 0

    def get_requests(self) -> List[Dict]:
        """获取远程Mock记录的请求"""
        result = self.ssh.exec(
            f"curl -s http://localhost:{self.mock_port}/requests")
        if result['returncode'] == 0:
            try:
                data = json.loads(result['stdout'])
                return data.get('requests', [])
            except json.JSONDecodeError:
                return []
        return []

    def get_last_request(self) -> Optional[Dict]:
        """获取远程Mock最后一条请求"""
        result = self.ssh.exec(
            f"curl -s http://localhost:{self.mock_port}/last-request")
        if result['returncode'] == 0:
            try:
                return json.loads(result['stdout'])
            except json.JSONDecodeError:
                return None
        return None

    def get_last_headers(self) -> Dict[str, str]:
        """获取远程Mock最后一条请求的请求头"""
        last_request = self.get_last_request()
        return last_request.get('headers', {}) if last_request else {}

    def _generate_mock_script(self) -> str:
        """生成远程Mock服务脚本"""
        return '''#!/usr/bin/env python3
"""Backend Mock Service"""
import json
import time
import argparse
from flask import Flask, request, jsonify

app = Flask(__name__)
received_requests = []

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/clear', methods=['POST'])
def clear():
    received_requests.clear()
    return jsonify({'status': 'cleared'})

@app.route('/requests')
def get_requests():
    return jsonify({
        'count': len(received_requests),
        'requests': received_requests
    })

@app.route('/last-request')
def get_last_request():
    if received_requests:
        return jsonify(received_requests[-1])
    return jsonify({'error': 'No requests'}), 404

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def catch_all(path):
    request_info = {
        'path': request.path,
        'method': request.method,
        'headers': dict(request.headers),
        'args': dict(request.args),
        'form': dict(request.form) if request.form else {},
        'json': request.get_json(silent=True),
        'remote_addr': request.remote_addr,
        'timestamp': time.time()
    }
    received_requests.append(request_info)
    return jsonify(request_info)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, threaded=True)
'''


# 便捷函数
def create_local_mock(port: int = 8080) -> BackendMock:
    """创建本地Mock服务"""
    return BackendMock(port=port)
