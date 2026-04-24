#!/bin/bash
# 环境初始化脚本
# 用于初始化测试环境，包括安装依赖、配置机器等

set -e

echo "=== Nginx 自动化测试环境初始化 ==="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python版本
echo -e "${YELLOW}[1/5] 检查Python版本...${NC}"
python3 --version || { echo -e "${RED}错误: 未安装Python3${NC}"; exit 1; }

# 安装Python依赖
echo -e "${YELLOW}[2/5] 安装Python依赖...${NC}"
pip3 install -r requirements.txt || pip install -r requirements.txt

# 检查SSH连接
echo -e "${YELLOW}[3/5] 检查SSH连接...${NC}"
python3 << 'EOF'
import yaml
import paramiko
import sys

with open('config/hosts.yml', 'r') as f:
    config = yaml.safe_load(f)

all_connected = True
for name, host_config in config['test_env'].items():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host_config['host'],
            port=host_config['port'],
            username=host_config['username'],
            password=host_config['password'],
            timeout=10
        )
        print(f"  ✓ {name} ({host_config['host']}) - 连接成功")
        client.close()
    except Exception as e:
        print(f"  ✗ {name} ({host_config['host']}) - 连接失败: {e}")
        all_connected = False

sys.exit(0 if all_connected else 1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: SSH连接检查失败${NC}"
    exit 1
fi

# 检查Nginx状态
echo -e "${YELLOW}[4/5] 检查Nginx服务器状态...${NC}"
python3 << 'EOF'
import yaml
import paramiko

with open('config/hosts.yml', 'r') as f:
    config = yaml.safe_load(f)

nginx_config = config['test_env']['nginx_server']
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    hostname=nginx_config['host'],
    port=nginx_config['port'],
    username=nginx_config['username'],
    password=nginx_config['password']
)

# 检查Nginx是否安装
stdin, stdout, stderr = client.exec_command('nginx -v')
output = stdout.read().decode() + stderr.read().decode()
if 'nginx version' in output:
    print(f"  ✓ Nginx已安装: {output.strip()}")
else:
    print(f"  ✗ Nginx未安装")

# 检查Nginx状态
stdin, stdout, stderr = client.exec_command('systemctl is-active nginx')
status = stdout.read().decode().strip()
if status == 'active':
    print(f"  ✓ Nginx服务运行中")
else:
    print(f"  ! Nginx服务未运行，尝试启动...")
    client.exec_command('systemctl start nginx')

client.close()
EOF

# 创建必要的目录
echo -e "${YELLOW}[5/5] 创建测试目录...${NC}"
mkdir -p reports
mkdir -p logs

echo -e "${GREEN}=== 环境初始化完成 ===${NC}"
echo ""
echo "使用说明:"
echo "  1. 运行所有测试: ./scripts/run_tests.sh"
echo "  2. 运行P0测试: pytest tests/ -m p0 -v"
echo "  3. 运行单个测试文件: pytest tests/test_proxy_set_header.py -v"
