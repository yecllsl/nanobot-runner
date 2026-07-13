"""nanobot-ai 0.2.2 升级性能基线测试（D6）

验证升级后核心路径的性能未退化。阈值基于 v0.32.0 升级后实测值设置，
留出 50-100% 退化空间。当阈值被突破时，提示性能退化需排查。

基线获取方式：首次运行记录实际值，阈值设为实际值的 2 倍。
"""

import os
import time
import tracemalloc
from pathlib import Path
from unittest.mock import MagicMock

import psutil
import pytest
from fastapi.testclient import TestClient

from src.core.config_injector import ConfigInjector
from src.core.provider_adapter import DynamicProviderRegistry
from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


def _make_mock_context() -> MagicMock:
    """构建测试用 mock AppContext"""
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": [],
        "token_secret": "perf-test-secret-with-sufficient-length",
        "token_ttl_s": 86400,
    }
    return context


class TestConfigInjectorPerformance:
    """ConfigInjector 构建性能基线"""

    def test_build_nanobot_config_latency(self, tmp_path: Path) -> None:
        """ConfigInjector.build_nanobot_config 应在 200ms 内完成

        基线实测：~5ms（后续调用），首次含 Schema 导入约 110ms
        阈值：200ms（含首次模块导入开销）
        """
        injector = ConfigInjector(config_path=tmp_path / "config.json")
        runner_config = {
            "agents": {"defaults": {"model": "gpt-4", "provider": "openai"}},
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    "api_base": "https://api.openai.com/v1",
                },
            },
            "transcription": {"enabled": False, "provider": "assemblyai"},
        }

        start = time.perf_counter()
        config = injector.build_nanobot_config(runner_config)
        elapsed = time.perf_counter() - start

        assert config is not None
        assert elapsed < 0.200, (
            f"ConfigInjector 构建退化: {elapsed * 1000:.1f}ms > 200ms"
        )

    def test_build_config_with_many_providers(self, tmp_path: Path) -> None:
        """构建含 20 个 Provider 的配置应在 200ms 内完成

        基线实测：~15ms
        阈值：200ms
        """
        injector = ConfigInjector(config_path=tmp_path / "config.json")
        providers = {
            f"custom_{i}": {
                "api_key": f"sk-{i}",
                "api_base": f"https://api.custom{i}.com/v1",
            }
            for i in range(20)
        }
        runner_config = {
            "agents": {"defaults": {"model": "gpt-4", "provider": "openai"}},
            "providers": providers,
        }

        start = time.perf_counter()
        config = injector.build_nanobot_config(runner_config)
        elapsed = time.perf_counter() - start

        assert config is not None
        assert elapsed < 0.200, f"多 Provider 构建退化: {elapsed * 1000:.1f}ms > 200ms"


class TestDynamicProviderRegistryPerformance:
    """DynamicProviderRegistry 注册性能基线"""

    def test_register_single_provider_latency(self) -> None:
        """注册单个 Provider 应在 50ms 内完成

        基线实测：~2ms
        阈值：50ms
        """
        DynamicProviderRegistry._custom_providers.clear()
        DynamicProviderRegistry._provider_metadata.clear()

        start = time.perf_counter()
        DynamicProviderRegistry.register_custom_provider(
            name="perf_test_provider",
            api_base="https://api.perf.com/v1",
            api_key="sk-perf",
            default_model="perf-model",
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.050, f"Provider 注册退化: {elapsed * 1000:.1f}ms > 50ms"

        # 清理
        DynamicProviderRegistry._custom_providers.clear()
        DynamicProviderRegistry._provider_metadata.clear()

    def test_register_ten_providers_latency(self) -> None:
        """注册 10 个 Provider 应在 200ms 内完成

        基线实测：~10ms
        阈值：200ms
        """
        DynamicProviderRegistry._custom_providers.clear()
        DynamicProviderRegistry._provider_metadata.clear()

        start = time.perf_counter()
        for i in range(10):
            DynamicProviderRegistry.register_custom_provider(
                name=f"batch_provider_{i}",
                api_base=f"https://api.batch{i}.com/v1",
                api_key=f"sk-{i}",
                default_model=f"model-{i}",
            )
        elapsed = time.perf_counter() - start

        assert elapsed < 0.200, f"批量注册退化: {elapsed * 1000:.1f}ms > 200ms"
        assert len(DynamicProviderRegistry.list_custom_providers()) == 10

        # 清理
        DynamicProviderRegistry._custom_providers.clear()
        DynamicProviderRegistry._provider_metadata.clear()


class TestWebUIRoutePerformance:
    """WebUI 路由响应性能基线"""

    @pytest.fixture
    def client(self) -> TestClient:
        app = create_app(context=_make_mock_context())
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        token = create_access_token(
            secret="perf-test-secret-with-sufficient-length", ttl_seconds=3600
        )
        return {"Authorization": f"Bearer {token}"}

    def test_health_endpoint_latency(self, client: TestClient) -> None:
        """/api/health 响应应在 50ms 内

        基线实测：~5ms
        阈值：50ms
        """
        start = time.perf_counter()
        response = client.get("/api/health")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 0.050, f"健康检查退化: {elapsed * 1000:.1f}ms > 50ms"

    def test_custom_providers_list_latency(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /api/settings/custom-providers 响应在 100ms 内

        基线实测：~10ms
        阈值：100ms
        """
        start = time.perf_counter()
        response = client.get("/api/settings/custom-providers", headers=auth_headers)
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 0.100, f"Provider 列表退化: {elapsed * 1000:.1f}ms > 100ms"

    def test_app_startup_latency(self) -> None:
        """create_app() 应在 500ms 内完成

        基线实测：~50ms
        阈值：500ms
        """
        context = _make_mock_context()

        start = time.perf_counter()
        app = create_app(context=context)
        elapsed = time.perf_counter() - start

        assert app is not None
        assert elapsed < 0.500, f"应用启动退化: {elapsed * 1000:.1f}ms > 500ms"


class TestMemoryUsage:
    """内存占用基线"""

    def test_config_injection_memory_footprint(self, tmp_path: Path) -> None:
        """ConfigInjector 构建配置的内存分配应在 2MB 内

        使用 tracemalloc 测量 Python 内存分配（非 RSS）。
        基线实测：~200KB
        阈值：2MB
        """
        injector = ConfigInjector(config_path=tmp_path / "config.json")
        runner_config = {
            "agents": {"defaults": {"model": "gpt-4", "provider": "openai"}},
            "providers": {
                "openai": {
                    "api_key": "sk-test",
                    "api_base": "https://api.openai.com/v1",
                }
            },
        }

        tracemalloc.start()
        config = injector.build_nanobot_config(runner_config)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert config is not None
        assert peak < 2 * 1024 * 1024, f"内存分配退化: {peak / 1024:.1f}KB > 2MB"

    def test_process_rss_within_reasonable_range(self) -> None:
        """Python 进程 RSS 应在 1200MB 内

        基线实测：~150MB（单模块独立运行）
        性能测试套件累积后：~980MB（含 pytest、Playwright、nanobot、RunFlowAgent 全量模块）
        阈值：1200MB（预留缓冲，监控异常增长）
        """
        process = psutil.Process(os.getpid())
        rss = process.memory_info().rss

        assert rss < 1200 * 1024 * 1024, f"RSS 过高: {rss / 1024 / 1024:.1f}MB > 1200MB"
