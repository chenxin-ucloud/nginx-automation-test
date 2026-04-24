#!/bin/bash
# 后端Mock服务部署脚本
# 用于在后端机器上部署Mock服务

set -e

echo "=== 部署后端Mock服务 ==="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取后端机器配置
BACKEND1_IP="192.168.2.202"
BACKEND2_IP="192.168.2.136"
USERNAME="root"
PASSWORD="xin2024."
MOCK_PORT=8080

# 生成Mock服务脚本
cat > /tmp/mock_service.py << 'EOF'
#!/usr/bin/env python3
"""Backend Mock Service for Nginx Testing"""
import json
import time
import argparse
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)
received_requests = []
lock = threading.Lock()

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': time.time()})

@app.route('/clear', methods=['POST'])
def clear():
    """Clear recorded requests"""
    with lock:
        received_requests.clear()
    return jsonify({'status': 'cleared'})

@app.route('/requests')
def get_requests():
    """Get all recorded requests"""
    with lock:
        return jsonify({
            'count': len(received_requests),
            'requests': received_requests
        })

@app.route('/last-request')
def get_last_request():
    """Get last request"""
    with lock:
        if received_requests:
            return jsonify(received_requests[-1])
    return jsonify({'error': 'No requests'}), 404

@app.route('/echo', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def echo():
    """Echo endpoint - returns all request info"""
    request_info = {
        'path': request.path,
        'method': request.method,
        'headers': dict(request.headers),
        'args': dict(request.args),
        'form': dict(request.form) if request.form else {},
        'json': request.get_json(silent=True),
        'data': request.get_data(as_text=True),
        'remote_addr': request.remote_addr,
        'timestamp': time.time()
    }
    with lock:
        received_requests.append(request_info)
    return jsonify(request_info)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def catch_all(path):
    """Catch all requests"""
    request_info = {
        'path': request.path,
        'full_path': request.full_path,
        'method': request.method,
        'headers': dict(request.headers),
        'args': dict(request.args),
        'form': dict(request.form) if request.form else {},
        'json': request.get_json(silent=True),
        'data': request.get_data(as_text=True),
        'remote_addr': request.remote_addr,
        'timestamp': time.time()
    }
    with lock:
        received_requests.append(request_info)
    return jsonify(request_info)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    print(f"Starting mock server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)
EOF

# 部署到Backend-1
echo -e "${YELLOW}[1/2] 部署到 Backend-1 ($BACKEND1_IP)...${NC}"
python3 << EOF
import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='$BACKEND1_IP', username='$USERNAME', password='$PASSWORD')

# 上传脚本
sftp = client.open_sftp()
with sftp.file('/tmp/mock_service.py', 'w') as f:
    with open('/tmp/mock_service.py', 'r') as local_f:
        f.write(local_f.read())
sftp.close()

# 检查Python3和Flask
stdin, stdout, stderr = client.exec_command('python3 -c "import flask; print(\"OK\")" 2>&1')
if 'OK' not in stdout.read().decode():
    print("  安装Flask...")
    client.exec_command('pip3 install flask -q')

# 停止旧服务
client.exec_command('pkill -f mock_service.py')
time.sleep(1)

# 启动新服务
client.exec_command('nohup python3 /tmp/mock_service.py --port $MOCK_PORT > /tmp/mock.log 2>&1 &')
time.sleep(2)

# 验证服务
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:$MOCK_PORT/health')
if 'ok' in stdout.read().decode():
    print("  ✓ Mock服务启动成功")
else:
    print("  ✗ Mock服务启动失败")

client.close()
EOF

# 部署到Backend-2
echo -e "${YELLOW}[2/2] 部署到 Backend-2 ($BACKEND2_IP)...${NC}"
python3 << EOF
import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname='$BACKEND2_IP', username='$USERNAME', password='$PASSWORD')

# 上传脚本
sftp = client.open_sftp()
with sftp.file('/tmp/mock_service.py', 'w') as f:
    with open('/tmp/mock_service.py', 'r') as local_f:
        f.write(local_f.read())
sftp.close()

# 检查Python3和Flask
stdin, stdout, stderr = client.exec_command('python3 -c "import flask; print(\"OK\")" 2>&1')
if 'OK' not in stdout.read().decode():
    print("  安装Flask...")
    client.exec_command('pip3 install flask -q')

# 停止旧服务
client.exec_command('pkill -f mock_service.py')
time.sleep(1)

# 启动新服务
client.exec_command('nohup python3 /tmp/mock_service.py --port $MOCK_PORT > /tmp/mock.log 2>&1 &')
time.sleep(2)

# 验证服务
stdin, stdout, stderr = client.exec_command('curl -s http://localhost:$MOCK_PORT/health')
if 'ok' in stdout.read().decode():
    print("  ✓ Mock服务启动成功")
else:
    print("  ✗ Mock服务启动失败")

client.close()
EOF

echo -e "${GREEN}=== 后端Mock服务部署完成 ===${NC}"
echo ""
echo "Mock服务地址:"
echo "  Backend-1: http://$BACKEND1_IP:$MOCK_PORT"
echo "  Backend-2: http://$BACKEND2_IP:$MOCK_PORT"
