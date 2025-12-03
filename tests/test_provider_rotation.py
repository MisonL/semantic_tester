import sys
import os
import logging
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path so `semantic_tester` can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from semantic_tester.api.provider_manager import ProviderManager
from semantic_tester.config.environment import EnvManager

# Configure logging for debug output during test runs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_rotation_configuration():
    """ProviderManager 应该为不同供应商设置正确的 auto_rotate 策略。

    这里只关心配置逻辑本身，不依赖真实的 SDK 安装状态，
    因此只验证 Gemini 和 OpenAI 两个核心供应商。
    """

    # Mock EnvManager
    mock_env = MagicMock(spec=EnvManager)
    mock_env.get_gemini_api_keys.return_value = ["key1", "key2"]
    mock_env.get_gemini_model.return_value = "gemini-pro"

    mock_env.get_openai_config.return_value = {
        "api_keys": ["key1", "key2"],
        "model": "gpt-4",
        "base_url": "url",
        "has_config": True,
    }

    # 其他供应商配置为默认空，避免依赖未安装的第三方 SDK
    mock_env.get_anthropic_config.return_value = {}
    mock_env.get_dify_config.return_value = {}
    mock_env.get_iflow_config.return_value = {}

    mock_env.get_batch_config.return_value = {}
    mock_env.get_api_config.return_value = {}

    # 只注册 Gemini 和 OpenAI，避免创建 Anthropic/Dify/iFlow 实例
    mock_env.get_ai_providers.return_value = [
        {"index": 1, "name": "Gemini", "id": "gemini"},
        {"index": 2, "name": "OpenAI", "id": "openai"},
    ]

    manager = ProviderManager(mock_env)

    gemini = manager.get_provider("gemini")
    assert gemini is not None
    assert gemini.auto_rotate is True

    openai = manager.get_provider("openai")
    assert openai is not None
    assert openai.auto_rotate is False


def test_rotation_logic():
    """验证不同 auto_rotate 配置下 _rotate_key 的行为。"""

    # Mock config for a provider with auto_rotate=False
    config_no_rotate = {
        "name": "TestNoRotate",
        "id": "test_no_rotate",
        "api_keys": ["key1", "key2"],
        "auto_rotate": False,
    }

    # Mock config for a provider with auto_rotate=True
    config_rotate = {
        "name": "TestRotate",
        "id": "test_rotate",
        "api_keys": ["key1", "key2"],
        "auto_rotate": True,
    }

    from semantic_tester.api.gemini_provider import GeminiProvider

    # Test Gemini (Auto Rotate = True)
    with patch.object(GeminiProvider, "validate_api_key", return_value=True):
        gemini = GeminiProvider(config_rotate)
        initial_key_index = gemini.current_key_index
        gemini._rotate_key()
        new_key_index = gemini.current_key_index

        assert new_key_index != initial_key_index, (
            "GeminiProvider 在 auto_rotate=True 时应当轮转 API Key"
        )

    # Test Gemini with Auto Rotate = False (Simulated)
    with patch.object(GeminiProvider, "validate_api_key", return_value=True):
        gemini_no_rotate = GeminiProvider(config_no_rotate)
        initial_key_index = gemini_no_rotate.current_key_index
        gemini_no_rotate._rotate_key()
        new_key_index = gemini_no_rotate.current_key_index

        assert new_key_index == initial_key_index, (
            "GeminiProvider 在 auto_rotate=False 时不应当轮转 API Key"
        )

    # Test OpenAI (Auto Rotate = False)
    from semantic_tester.api.openai_provider import OpenAIProvider

    with patch.object(OpenAIProvider, "validate_api_key", return_value=True):
        openai = OpenAIProvider(config_no_rotate)
        initial_key_index = openai.current_key_index
        openai._rotate_key()
        new_key_index = openai.current_key_index

        assert new_key_index == initial_key_index, (
            "OpenAIProvider 默认 auto_rotate=False，调用 _rotate_key 不应改变索引"
        )
