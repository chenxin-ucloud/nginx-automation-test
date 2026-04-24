"""
性能测试

测试内容:
- 并发性能测试
- 响应时间测试
- 吞吐量测试
- 内存使用测试
"""

import pytest
import requests
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from tests.conftest import NginxBaseTest


@pytest.mark.performance
class TestPerformance(NginxBaseTest):
    """性能测试类"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, backend_1_mock, backend_1_config):
        """设置后端Mock"""
        self.backend = backend_1_mock
        self.backend_host = f"{backend_1_config['host']}:{backend_1_config['mock_port']}"
        self.nginx_url = 'http://192.168.2.250'

    @pytest.mark.p1
    def test_single_request_response_time(self):
        """PERF-001: 单请求响应时间测试"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 预热
        for _ in range(10):
            requests.get(f'{self.nginx_url}/', timeout=5)

        # 测试100次请求
        response_times = []
        for _ in range(100):
            start = time.time()
            response = requests.get(f'{self.nginx_url}/', timeout=5)
            elapsed = time.time() - start
            response_times.append(elapsed)
            assert response.status_code == 200

        # 计算统计值
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        p95 = sorted(response_times)[int(len(response_times) * 0.95)]

        print(f"\n单请求性能统计:")
        print(f"  平均响应时间: {avg_time*1000:.2f}ms")
        print(f"  最小响应时间: {min_time*1000:.2f}ms")
        print(f"  最大响应时间: {max_time*1000:.2f}ms")
        print(f"  P95响应时间: {p95*1000:.2f}ms")

        # 断言性能指标
        assert avg_time < 0.1, f"平均响应时间应小于100ms，实际{avg_time*1000:.2f}ms"
        assert p95 < 0.2, f"P95响应时间应小于200ms，实际{p95*1000:.2f}ms"

    @pytest.mark.p1
    def test_concurrent_requests(self):
        """PERF-002: 并发请求测试"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        concurrency = 50
        total_requests = 500

        def make_request():
            try:
                start = time.time()
                response = requests.get(f'{self.nginx_url}/', timeout=10)
                elapsed = time.time() - start
                return response.status_code == 200, elapsed
            except Exception as e:
                return False, 0

        start_time = time.time()

        results = []
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]
            for future in as_completed(futures):
                results.append(future.result())

        total_time = time.time() - start_time

        success_count = sum(1 for success, _ in results if success)
        response_times = [rt for success, rt in results if success]

        throughput = total_requests / total_time
        success_rate = success_count / total_requests * 100

        print(f"\n并发性能测试 ({concurrency}并发, {total_requests}请求):")
        print(f"  总耗时: {total_time:.2f}s")
        print(f"  吞吐量: {throughput:.2f} req/s")
        print(f"  成功率: {success_rate:.2f}%")
        if response_times:
            print(f"  平均响应时间: {statistics.mean(response_times)*1000:.2f}ms")

        assert success_rate > 95, f"成功率应大于95%，实际{success_rate:.2f}%"
        assert throughput > 10, f"吞吐量应大于10 req/s，实际{throughput:.2f} req/s"

    @pytest.mark.p2
    def test_keepalive_performance(self):
        """PERF-003: 长连接性能测试"""
        config = f'''
upstream backend {{
    server {self.backend_host};
    keepalive 64;
}}

server {{
    listen 80;
    location / {{
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }}
}}'''
        self.deploy_and_reload(config)

        session = requests.Session()

        # 使用长连接发送100个请求
        start = time.time()
        for _ in range(100):
            response = session.get(f'{self.nginx_url}/', timeout=5)
            assert response.status_code == 200
        elapsed = time.time() - start

        avg_time = elapsed / 100
        print(f"\n长连接性能:")
        print(f"  平均响应时间: {avg_time*1000:.2f}ms")

        session.close()

    @pytest.mark.p2
    def test_proxy_set_header_performance_impact(self):
        """PERF-004: proxy_set_header对性能的影响"""
        # 测试无header的情况
        config_no_header = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config_no_header, [self.backend_host]))

        start = time.time()
        for _ in range(100):
            requests.get(f'{self.nginx_url}/', timeout=5)
        time_no_header = time.time() - start

        # 测试有多个header的情况
        config_with_headers = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Custom-1 "value1";
        proxy_set_header X-Custom-2 "value2";
        proxy_set_header X-Custom-3 "value3";
        proxy_set_header X-Custom-4 "value4";
        proxy_set_header X-Custom-5 "value5";
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config_with_headers, [self.backend_host]))

        start = time.time()
        for _ in range(100):
            requests.get(f'{self.nginx_url}/', timeout=5)
        time_with_headers = time.time() - start

        print(f"\nproxy_set_header性能影响:")
        print(f"  无header: {time_no_header*1000:.2f}ms")
        print(f"  有headers: {time_with_headers*1000:.2f}ms")
        print(f"  性能差异: {((time_with_headers - time_no_header) / time_no_header * 100):.2f}%")

        # 性能下降应小于50%
        assert time_with_headers < time_no_header * 1.5, "添加header不应导致性能下降超过50%"

    @pytest.mark.p2
    def test_memory_usage_under_load(self):
        """PERF-005: 负载下的内存使用"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 获取测试前的内存使用
        before_result = self.ssh.exec("ps aux | grep 'nginx' | grep -v grep | awk '{print $6}'")
        print(f"\nNginx内存使用测试:")
        print(f"  测试前: {before_result['stdout'].strip()}")

        # 发送大量请求
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(requests.get, f'{self.nginx_url}/', timeout=5)
                      for _ in range(1000)]
            for future in as_completed(futures):
                try:
                    future.result()
                except:
                    pass

        # 获取测试后的内存使用
        after_result = self.ssh.exec("ps aux | grep 'nginx' | grep -v grep | awk '{print $6}'")
        print(f"  测试后: {after_result['stdout'].strip()}")

    @pytest.mark.p2
    def test_header_size_impact(self):
        """PERF-006: 请求头大小对性能的影响"""
        config = f'''
server {{
    listen 80;
    location / {{
        proxy_pass http://{self.backend_host};
        proxy_set_header X-Custom $http_x_custom;
    }}
}}'''
        self.deploy_and_reload(self.deploy_config_with_upstream(config, [self.backend_host]))

        # 测试不同大小的header
        for size in [100, 1000, 5000]:
            header_value = "x" * size

            start = time.time()
            for _ in range(50):
                try:
                    requests.get(
                        f'{self.nginx_url}/',
                        headers={'X-Custom': header_value},
                        timeout=10
                    )
                except:
                    pass
            elapsed = time.time() - start

            print(f"  Header大小 {size}: {elapsed*1000/50:.2f}ms/请求")

    @pytest.mark.p1
    def test_upstream_failover_performance(self):
        """PERF-007: 上游故障转移性能"""
        # 配置一个无效的后端和一个有效的后端
        config = f'''
upstream backend {{
    server 192.168.255.255:8080 fail_timeout=1s;  # 无效后端
    server {self.backend_host} backup;
}}

server {{
    listen 80;
    location / {{
        proxy_pass http://backend;
        proxy_connect_timeout 2s;
    }}
}}'''
        self.deploy_and_reload(config)

        # 测试故障转移时间
        start = time.time()
        response = requests.get(f'{self.nginx_url}/', timeout=10)
        elapsed = time.time() - start

        assert response.status_code == 200
        print(f"\n故障转移时间: {elapsed*1000:.2f}ms")

        # 故障转移应在合理时间内完成（小于5秒）
        assert elapsed < 5, f"故障转移时间过长: {elapsed}s"
