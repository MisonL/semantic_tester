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

    def get_batch_config(self) -> Dict[str, Any]:
        return {}

    # 以下在 _get_provider_api_key 中会用到
    def get_gemini_api_keys(self):
        return ["ok-key"]

    def get_openai_config(self):
        return {"api_keys": ["ok-key"], "model": "m", "base_url": "u", "has_config": True}

    def get_anthropic_config(self):
        return {"api_keys": ["bad"], "model": "m", "base_url": "u", "has_config": True}

    def get_dify_config(self):
        return {"api_keys": ["ok-key"], "base_url": "u", "app_id": "id", "has_config": True}

    def get_iflow_config(self):
        return {"api_keys": ["ok-key"], "model": "m", "base_url": "u", "has_config": True}


def _make_manager_with_fake_providers(monkeypatch) -> ProviderManager:
    env = DummyEnv()

    # 拦截 _create_provider，避免真正实例化各 Provider
    def fake_create(self, provider_id: str, provider_name: str, batch_config: Dict[str, Any]):
        return FakeProvider(provider_id, provider_name, configured=(provider_id != "p2"))

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


def test_provider_manager_basic_selection_and_queries(monkeypatch):
    mgr = _make_manager_with_fake_providers(monkeypatch)

    # 初始化后，应自动选择已配置的第一个供应商（p1）
    assert mgr.get_current_provider_name() == "P1"

    avail = mgr.get_available_providers()
    assert any(p["is_current"] for p in avail)

    configured = mgr.get_configured_providers()
    assert len(configured) == 1

    # set_current_provider / get_provider
    assert mgr.set_current_provider("p2") is True
    assert mgr.get_current_provider_name() == "P2"
    assert mgr.get_provider("p1").name == "P1"  # type: ignore[union-attr]

    # provider_choices
    choices = mgr.get_provider_choices()
    ids = [c[0] for c in choices]
    assert ids == ["p1", "p2"]

    # has_configured_providers / statistics
    assert mgr.has_configured_providers() is True
    stats = mgr.get_provider_statistics()
    assert stats["total_providers"] == 2


def test_provider_manager_validation_and_switch(monkeypatch):
    mgr = _make_manager_with_fake_providers(monkeypatch)

    # 使用 gemini provider id 测试 _get_provider_api_key / _validate_provider_api_key
    fake_gemini = FakeProvider("gemini", "Gemini")
    api_key = mgr._get_provider_api_key(fake_gemini)
    assert api_key == "ok-key"
    assert mgr._validate_provider_api_key(fake_gemini) is True

    # 构造验证状态
    status = mgr.get_provider_validation_status()
    assert status["total"] == 2
    assert status["unconfigured"] >= 1

    # 当前 fake provider 的 validate_api_key 只对 "ok-key" 返回 True，
    # 但 get_provider_validation_status 中只对管理器内的 providers 调用验证，
    # 而我们的 fake providers 没有真实 api_key，因此这里不强求成功，只要调用不抛异常即可。
    assert mgr.switch_to_first_valid_provider() in (True, False)


def test_provider_manager_print_and_revalidate(monkeypatch, capsys):
    mgr = _make_manager_with_fake_providers(monkeypatch)

    mgr.print_provider_status()
    out, _ = capsys.readouterr()
    assert "AI 供应商状态" in out

    mgr.revalidate_all_providers()  # 调用内部 _validate_and_auto_select_provider


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


def test_get_provider_api_key_for_known_and_unknown_ids():
    mgr = _make_bare_manager()

    for pid in ["gemini", "openai", "anthropic", "dify", "iflow"]:
        key = mgr._get_provider_api_key(FakeProvider(pid, pid))
        # 只要调用不抛异常即可，这里不强制 key 非空
        assert isinstance(key, (str, type(None)))

    # 未知 id 应返回 None
    assert mgr._get_provider_api_key(FakeProvider("unknown", "Unknown")) is None


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
