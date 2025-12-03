import threading

from semantic_tester.api.base_provider import AIProvider


class DummyProvider(AIProvider):
    def __init__(self):
        super().__init__({"name": "Dummy", "id": "dummy"})

    def get_models(self):
        return ["m1", "m2"]

    def validate_api_key(self, api_key: str) -> bool:
        return api_key == "ok"

    def check_semantic_similarity(self, *args, **kwargs):  # pragma: no cover - not used
        return ("是", "ok")

    def is_configured(self) -> bool:
        return True


def test_base_provider_helpers_and_waiting_indicator():
    provider = DummyProvider()

    # default model & info
    assert provider.get_default_model() == "m1"
    info = provider.get_provider_info()
    assert info["name"] == "Dummy"
    assert info["configured"] is True

    s = str(provider)
    r = repr(provider)
    assert "Dummy" in s
    assert "AIProvider(" in r

    # show_waiting_indicator: 预先设置 stop_event，避免循环
    stop = threading.Event()
    stop.set()
    provider.show_waiting_indicator(stop)
