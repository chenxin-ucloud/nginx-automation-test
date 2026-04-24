# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a comprehensive Nginx core directives automation testing framework based on Python + pytest. The framework supports 223 test cases covering 8 directive modules.

## Test Environment Topology

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Client    │────────▶│  Server-Nginx    │────────▶│  Backend-1      │
│ 192.168.2.51│         │  192.168.2.250   │         │ 192.168.2.202   │
└─────────────┘         │   (Proxy Node)   │         └─────────────────┘
                        │                  │
                        │                  │────────▶┌─────────────────┐
                        └──────────────────┘         │  Backend-2      │
                                                     │ 192.168.2.136   │
                                                     └─────────────────┘
```

**Machine Credentials:**
- Username: `root`
- Password: `xin2024.`

## Common Commands

### Environment Setup
```bash
# Initialize environment and check SSH connections
./scripts/setup_env.sh

# Deploy backend mock services
./scripts/deploy_backend.sh
```

### Run Tests
```bash
# Run all P0 tests (default)
./scripts/run_tests.sh

# Run all tests
./scripts/run_tests.sh -a

# Run by priority
./scripts/run_tests.sh -p P0
./scripts/run_tests.sh -p "P0 or P1"

# Run specific module
./scripts/run_tests.sh -m proxy_set_header

# Run specific test file
./scripts/run_tests.sh -f tests/test_server.py

# Run with parallel execution
./scripts/run_tests.sh -a -n 4

# Run with retry on failure
./scripts/run_tests.sh -a -r 2
```

### Direct pytest Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests with HTML report
pytest tests/ --html=reports/report.html --self-contained-html

# Run by marker
pytest tests/ -m "p0" -v
pytest tests/ -m "proxy_set_header" -v
pytest tests/ -m "not p3" -v

# Run specific test
pytest tests/test_proxy_set_header.py::TestProxySetHeader::test_basic_custom_header -v

# Parallel execution
pytest tests/ -n auto -v

# With retry
pytest tests/ --reruns 2 --reruns-delay 1
```

## Architecture Overview

### Core Components

1. **RemoteExecutor** (`utils/remote_executor.py`)
   - SSH-based remote command execution using paramiko
   - Supports command execution, file upload/download
   - Connection pooling for efficiency

2. **NginxManager** (`utils/nginx_manager.py`)
   - Configuration backup, deployment, and restore
   - Syntax validation (`nginx -t`)
   - Service control (start/stop/reload)
   - Log retrieval

3. **BackendMock** (`utils/backend_mock.py`)
   - Flask-based HTTP mock service
   - Captures and stores incoming request headers
   - Provides endpoints for test verification
   - Supports both local and remote deployment

4. **HttpClient** (`utils/http_client.py`)
   - HTTP request wrapper with retry logic
   - Response validation helpers
   - Nginx-specific test client

5. **Validators** (`utils/validators.py`)
   - Header validation (exists, equals, contains)
   - Response status code validation
   - Config validation helpers

### Test Structure

Tests follow the pattern in `tests/conftest.py`:
- `NginxBaseTest` class provides autouse fixture for config backup/restore
- Each test method deploys config, makes requests, validates results
- Automatic teardown ensures clean state between tests

### Configuration Files

- `config/hosts.yml` - Machine configuration (IPs, credentials, ports)
- `config/nginx_templates/` - Nginx config templates by directive
- `config/test_data/` - Test data (headers, URLs, payloads)
- `pytest.ini` - pytest configuration and markers

## Key Implementation Patterns

### Test Method Pattern
```python
@pytest.mark.p0
def test_example(self):
    """Test description"""
    config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Test value;
    }}
}}'''
    self.deploy_and_reload(
        self.deploy_config_with_upstream(config, [self.backend_host])
    )

    response = requests.get(f'http://192.168.2.250/', timeout=5)
    assert response.status_code == 200

    backend_headers = self.backend.get_last_headers()
    assert 'X-Test' in backend_headers
```

### Priority Markers
- `@pytest.mark.p0` - Core functionality, must pass
- `@pytest.mark.p1` - Important functionality
- `@pytest.mark.p2` - General functionality
- `@pytest.mark.p3` - Low priority

### Module Markers
- `@pytest.mark.proxy_set_header`
- `@pytest.mark.grpc_set_header`
- `@pytest.mark.proxy_pass_header`
- `@pytest.mark.add_header`
- `@pytest.mark.server`
- `@pytest.mark.server_name`
- `@pytest.mark.location`
- `@pytest.mark.performance`

## Test Coverage

| Module | Cases | Key Scenarios |
|--------|-------|---------------|
| proxy_set_header | 39 | Custom headers, Host modification, header deletion, level priority, variable expansion |
| grpc_set_header | 22 | gRPC metadata, HTTP/2 requirement, token pass, level inheritance |
| proxy_pass_header | 30 | Response header pass/hide, batch operations, level scoping |
| add_header | 5 | Basic addition, always parameter, level priority |
| server | 14 | Port matching, default server, multi-server configs |
| server_name | 7 | Exact match, wildcard, regex, priority |
| location | 1+ | Exact (=), prefix (^~), regex (~, ~*), priority |
| performance | ~105 | Response time, throughput, concurrency, memory |

## Important Notes

1. **Config Deployment**: Always use `deploy_and_reload()` which validates syntax before deployment
2. **Backend Mock**: Tests rely on Flask mock service running on backend nodes (port 8080)
3. **SSH Connections**: Framework uses paramiko for SSH - ensure network connectivity
4. **State Cleanup**: `NginxBaseTest` automatically restores config after each test
5. **Parallel Execution**: Use `-n auto` for parallel test execution (requires pytest-xdist)

## Related Resources

- Original test plan: `/Users/user/Desktop/chenxin/nginx-automation-test-plan.md`
- Nginx configurations: `/Users/user/Desktop/chenxin/nginx/`
