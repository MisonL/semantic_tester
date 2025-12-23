import os

import pytest

from semantic_tester.config import environment as env_mod


class DummyLoader:
    def __init__(self, cfg: dict):
        self._cfg = cfg

    def get_str(self, key: str, default: str = "") -> str:
        return self._cfg.get(key, default)

    def get_float(self, key: str, default: float = 0.0) -> float:
        return float(self._cfg.get(key, default))

    def get_int(self, key: str, default: int = 0) -> int:
        return int(self._cfg.get(key, default))

    def get_bool(self, key: str, default: bool = False) -> bool:
        return str(self._cfg.get(key, str(default))).lower() in (
            "true",
            "1",
            "yes",
            "on",
        )

    def get_list(self, key: str, default=None, separator=","):
        if default is None:
            default = []
        value = self._cfg.get(key, "")
        if not value:
            return default
        return [v.strip() for v in value.split(separator) if v.strip()]

    def get_ai_providers(self):  # pragma: no cover - simple passthrough
        return self._cfg.get("AI_PROVIDERS", [])

    def print_config_status(self):  # pragma: no cover
        print("CONFIG")


@pytest.fixture
def patched_env_loader(monkeypatch):
    cfg = {
        "GEMINI_MODEL": "models/test",
        "OPENAI_MODEL": "gpt-test",
        "OPENAI_BASE_URL": "https://test.openai",
        "DIFY_BASE_URL": "https://test.dify",
        "ANTHROPIC_MODEL": "claude-test",
        "ANTHROPIC_BASE_URL": "https://test.anthropic",
        "IFLOW_MODEL": "qwen-test",
        "IFLOW_BASE_URL": "https://test.iflow",
        "BATCH_REQUEST_INTERVAL": "2.0",
        "WAITING_INDICATORS": "-,*",
        "WAITING_TEXT": "处理中",
        "WAITING_DELAY": "0.2",
        "API_TIMEOUT": "30",
        "API_RETRY_COUNT": "2",
        "API_RETRY_DELAY": "10",
        "USE_FULL_DOC_MATCH": "true",
        "ENABLE_THINKING": "false",
        "SEMANTIC_CHECK_PROMPT": "PROMPT_FROM_FILE",
    }

    dummy = DummyLoader(cfg)
    monkeypatch.setattr(env_mod, "get_env_loader", lambda: dummy)
    # 清空相关环境变量，避免干扰
    for k in list(os.environ.keys()):
        if k.startswith("GEMINI_") or k.startswith("OPENAI_") or k.endswith("_API_KEY"):
            os.environ.pop(k, None)

    return dummy


def test_env_manager_flags_and_prompt(patched_env_loader, monkeypatch):
    """测试 EnvManager 的标志位获取和语义提示词方法"""
    mgr = env_mod.EnvManager()

    # use_full_doc_match / enable_thinking 从 env 覆盖 loader
    monkeypatch.setenv("USE_FULL_DOC_MATCH", "0")
    monkeypatch.setenv("ENABLE_THINKING", "1")
    assert mgr.get_use_full_doc_match() is False
    assert mgr.get_enable_thinking() is True

    # 语义提示词：环境变量优先
    monkeypatch.setenv("SEMANTIC_CHECK_PROMPT", "PROMPT_FROM_ENV")
    assert mgr.get_semantic_check_prompt() == "PROMPT_FROM_ENV"


def test_env_manager_batch_api_config_and_print(
    patched_env_loader, monkeypatch, capsys
):
    """测试批量配置和 API 配置获取"""
    mgr = env_mod.EnvManager()

    batch_cfg = mgr.get_batch_config()
    # 使用实际存在的 key
    assert "save_interval" in batch_cfg or "waiting_text" in batch_cfg

    api_cfg = mgr.get_api_config()
    assert "timeout" in api_cfg
    assert "retry_count" in api_cfg

    # print_env_status 主要验证输出包含关键字段
    mgr.print_env_status()
    out, _ = capsys.readouterr()
    assert "环境配置状态" in out


def test_env_manager_analyze_and_log_template_summary(patched_env_loader, monkeypatch):
    # 设置多个供应商 key，部分为模板值
    monkeypatch.setenv("GEMINI_API_KEY", "your-gemini-api-key, real1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-your-openai-api-key, sk-real2")
    monkeypatch.setenv("DIFY_API_KEY", "app-your-dify-api-key")

    mgr = env_mod.EnvManager()

    # _analyze_provider_keys 基本分支
    tpl_count, configured = mgr._analyze_provider_keys("GEMINI_API_KEY", "gemini")
    assert tpl_count == 1 and configured is True

    # 调用 _log_template_summary 只要不抛异常即可（构造时已调用）
    mgr._log_template_summary()
