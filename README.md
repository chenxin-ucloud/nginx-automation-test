# Nginx 核心指令自动化测试框架

## 项目概述

本项目是一个完整的Nginx核心指令自动化测试框架，基于Python + pytest构建，用于测试Nginx的各种配置指令。

## 测试覆盖范围

| 指令模块 | 用例数量 | 优先级分布 |
|---------|---------|-----------|
| proxy_set_header | 39 | P0: 8, P1: 15, P2: 16 |
| grpc_set_header | 22 | P0: 5, P1: 8, P2: 9 |
| proxy_pass_header / proxy_hide_header | ~30 | P0: 6, P1: 12, P2: 12 |
| add_header | 5 | P0: 2, P1: 2, P2: 1 |
| server | 14 | P0: 3, P1: 5, P2: 6 |
| server_name | 7 | P0: 2, P1: 3, P2: 2 |
| location | 1+ | P0: 1 |
| 性能/安全/边界 | ~105 | P1/P2为主 |

**总计: 223条测试用例**

## 环境拓扑

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Client    │────────▶│  Server-Nginx    │────────▶│  Backend-1      │
│ 192.168.2.51│         │  192.168.2.250   │         │ 192.168.2.202   │
└─────────────┘         │   (Proxy节点)    │         └─────────────────┘
                        │                  │
                        │                  │────────▶┌─────────────────┐
                        └──────────────────┘         │  Backend-2      │
                                                     │ 192.168.2.136   │
                                                     └─────────────────┘
```

## 快速开始

### 1. 环境初始化

```bash
./scripts/setup_env.sh
```

### 2. 部署后端Mock服务

```bash
./scripts/deploy_backend.sh
```

### 3. 运行测试

```bash
# 运行所有P0测试
./scripts/run_tests.sh -p P0

# 运行所有测试
./scripts/run_tests.sh -a

# 运行指定模块
./scripts/run_tests.sh -m proxy_set_header

# 运行指定文件
./scripts/run_tests.sh -f tests/test_server.py

# 并行运行
./scripts/run_tests.sh -a -n 4

# 失败重试
./scripts/run_tests.sh -a -r 2
```

## 目录结构

```
nginx-automation-test/
├── config/
│   ├── hosts.yml              # 机器配置信息
│   ├── nginx_templates/       # Nginx配置模板
│   └── test_data/             # 测试数据
├── tests/
│   ├── conftest.py            # pytest fixtures
│   ├── test_proxy_set_header.py
│   ├── test_grpc_set_header.py
│   ├── test_proxy_pass_header.py
│   ├── test_add_header.py
│   ├── test_server.py
│   ├── test_server_name.py
│   ├── test_location.py
│   └── test_performance.py
├── utils/
│   ├── __init__.py
│   ├── nginx_manager.py       # Nginx配置管理
│   ├── remote_executor.py     # 远程命令执行
│   ├── http_client.py         # HTTP请求工具
│   ├── backend_mock.py        # 后端服务Mock
│   └── validators.py          # 结果验证
├── scripts/
│   ├── setup_env.sh           # 环境初始化
│   ├── deploy_backend.sh      # 部署后端服务
│   └── run_tests.sh           # 测试执行入口
├── reports/                   # 测试报告输出
├── requirements.txt
├── pytest.ini
└── README.md
```

## 核心组件

### NginxManager
管理Nginx配置的备份、部署、验证和恢复。

### RemoteExecutor
通过SSH连接到远程机器执行命令和上传文件。

### BackendMock
Flask-based后端Mock服务，用于捕获和返回请求头信息。

### HttpClient
HTTP客户端，用于发送请求和验证响应。

### Validators
各种验证器，用于验证请求头、响应状态码等。

## 测试执行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行全部测试
pytest tests/ --html=reports/report.html --self-contained-html

# 按优先级执行
pytest tests/ -m "p0" -v
pytest tests/ -m "p0 or p1" -v
pytest tests/ -m "not p3" -v

# 按模块执行
pytest tests/test_proxy_set_header.py -v
pytest tests/test_add_header.py -v

# 并行执行
pytest tests/ -n auto -v

# 失败重试
pytest tests/ --reruns 2 --reruns-delay 1
```

## 测试标记

- `p0`: 核心功能测试
- `p1`: 重要功能测试
- `p2`: 一般功能测试
- `p3`: 低优先级测试
- `proxy_set_header`: proxy_set_header指令
- `grpc_set_header`: grpc_set_header指令
- `proxy_pass_header`: proxy_pass_header指令
- `add_header`: add_header指令
- `server`: server指令
- `server_name`: server_name指令
- `location`: location指令
- `performance`: 性能测试
- `security`: 安全测试

## 环境配置

编辑 `config/hosts.yml` 配置测试环境：

```yaml
test_env:
  client:
    host: "192.168.2.51"
    username: "root"
    password: "xin2024."
  nginx_server:
    host: "192.168.2.250"
    username: "root"
    password: "xin2024."
  backend_1:
    host: "192.168.2.202"
    username: "root"
    password: "xin2024."
  backend_2:
    host: "192.168.2.136"
    username: "root"
    password: "xin2024."
```

## 贡献指南

1. 添加新测试用例时，请遵循现有代码风格
2. 为测试方法添加适当的标记（@pytest.mark.p0等）
3. 更新CLAUDE.md文档
4. 确保测试在本地通过后再提交

## License

MIT
