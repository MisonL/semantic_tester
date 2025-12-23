from typing import Any, Dict, List

from semantic_tester.api.base_provider import AIProvider
from semantic_tester.api.provider_manager import ProviderManager


class FakeProvider(AIProvider):
    def __init__(self, pid: str, name: str, configured: bool = True):
        super().__init__({"id": pid, "name": name})
        self._configured = configured
        self.validate_called_with: List[str] = []

    def get_models(self):
        return ["m1"]

    def validate_api_key(self, api_key: str) -> bool:
        self.validate_called_with.append(api_key)
        return api_key == "ok-key"

    def check_semantic_similarity(self, *args, **kwargs):  # pragma: no cover - not used
        return ("是", "ok")

    def is_configured(self) -> bool:
        return self._configured


class DummyEnv:
    def __init__(self):
        self._providers = [
            {"index": 1, "name": "P1", "id": "p1"},
            {"index": 2, "name": "P2", "id": "p2"},
        ]

    def get_ai_providers(self):
        return self._providers

    def get_channels_config(self):
        """返回模拟的多渠道配置"""
        return [
            {
                "id": "channel_1",
                "display_name": "P1",
                "type": "iflow-1",
                "concurrency": 1,
                "api_keys": ["ok-key"],
                "model": "test-model",
                "base_url": "https://test.url",
                "has_config": True,
            },
            {
                "id": "channel_2",
                "display_name": "P2",
                "type": "iflow-2",
                "concurrency": 1,
                "api_keys": ["ok-key"],
                "model": "test-model",
                "base_url": "https://test.url",
                "has_config": True,
            },
        ]

    def get_batch_config(self) -> Dict[str, Any]:
        return {}


def _make_manager_with_fake_providers(monkeypatch) -> ProviderManager:
    env = DummyEnv()

    # 拦截 _create_provider，避免真正实例化各 Provider
    def fake_create(
        self, provider_id: str, provider_name: str, batch_config: Dict[str, Any]
    ):
        return FakeProvider(
            provider_id, provider_name, configured=(provider_id != "p2")
        )

    monkeypatch.setattr(ProviderManager, "_create_provider", fake_create, raising=False)

    mgr = ProviderManager(env)
    return mgr


def _make_bare_manager() -> ProviderManager:
    """构造一个不运行 __init__ 的 ProviderManager，用于测试内部方法。"""
    mgr = ProviderManager.__new__(ProviderManager)  # type: ignore[call-arg]
    mgr.config = DummyEnv()
    mgr.providers = {}
    mgr.current_provider_id = None
    return mgr


def test_provider_manager_basic_selection(monkeypatch):
    """测试 ProviderManager 基础初始化和供应商选择"""
    mgr = _make_manager_with_fake_providers(monkeypatch)

    # 初始化后，应有供应商可用
    providers = mgr.get_channel_providers()
    assert len(providers) == 2

    # 可以通过 ID 获取供应商
    p1 = mgr.get_provider("channel_1")
    assert p1 is not None

    # set_current_provider / get_provider
    assert mgr.set_current_provider("channel_2") is True
    assert mgr.get_current_provider() is not None


def test_provider_manager_configured_list(monkeypatch):
    """测试已配置供应商列表获取"""
    mgr = _make_manager_with_fake_providers(monkeypatch)
    configured = mgr.get_configured_providers_list()
    # 应当有一个已配置的供应商 (channel_1配置为True)
    assert len(configured) >= 1


def test_validate_and_auto_select_provider_prefers_configured():
    mgr = _make_bare_manager()

    # 一个已配置、一个未配置
    p1 = FakeProvider("p1", "P1", configured=True)
    p2 = FakeProvider("p2", "P2", configured=False)
    mgr.providers = {"p1": p1, "p2": p2}

    mgr._validate_and_auto_select_provider()
    assert mgr.current_provider_id == "p1"


def test_validate_and_auto_select_provider_falls_back_to_unconfigured():
    mgr = _make_bare_manager()

    p1 = FakeProvider("p1", "P1", configured=False)
    p2 = FakeProvider("p2", "P2", configured=False)
    mgr.providers = {"p1": p1, "p2": p2}

    mgr._validate_and_auto_select_provider()
    # 没有已配置供应商时，应选择第一个未配置供应商
    assert mgr.current_provider_id in {"p1", "p2"}


def test_check_semantic_similarity_error_when_provider_missing():
    mgr = _make_bare_manager()
    # providers 为空时应返回错误
    result, reason = mgr.check_semantic_similarity("q", "a", "doc", provider_id="nope")
    assert result == "错误"
    assert "不可用" in reason


def test_check_semantic_similarity_streams_and_delegates(monkeypatch):
    # 使用 fake providers，避免真实网络调用
    mgr = _make_bare_manager()
    provider = FakeProvider("p1", "P1", configured=True)
    mgr.providers = {"p1": provider}
    mgr.current_provider_id = "p1"

    # verify that method returns provider's result, stream=True 触发富文本分支
    result, reason = mgr.check_semantic_similarity(
        "question",
        "answer",
        "doc",
        provider_id="p1",
        stream=True,
        show_thinking=False,
    )
    assert result == "是"
    assert reason == "ok"
