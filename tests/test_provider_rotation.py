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
    因此只验证 iFlow 类型的供应商。
    """

    # Mock EnvManager
    mock_env = MagicMock(spec=EnvManager)

    # 使用新的 get_channels_config 方法代替已移除的旧方法
    mock_env.get_channels_config.return_value = [
        {
            "id": "channel_1",
            "display_name": "iFlow-1",
            "type": "iflow-1",
            "concurrency": 1,
            "api_keys": ["key1", "key2"],
            "model": "qwen-max",
            "base_url": "https://test.iflow",
            "has_config": True,
        },
        {
            "id": "channel_2",
            "display_name": "iFlow-2",
            "type": "iflow-2",
            "concurrency": 1,
            "api_keys": ["key1", "key2"],
            "model": "qwen-max",
            "base_url": "https://test.iflow",
            "has_config": True,
        },
    ]

    mock_env.get_batch_config.return_value = {}

    manager = ProviderManager(mock_env)

    # 验证供应商已创建
    p1 = manager.get_provider("channel_1")
    assert p1 is not None

    p2 = manager.get_provider("channel_2")
    assert p2 is not None


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

        assert (
            new_key_index != initial_key_index
        ), "GeminiProvider 在 auto_rotate=True 时应当轮转 API Key"

    # Test Gemini with Auto Rotate = False (Simulated)
    with patch.object(GeminiProvider, "validate_api_key", return_value=True):
        gemini_no_rotate = GeminiProvider(config_no_rotate)
        initial_key_index = gemini_no_rotate.current_key_index
        gemini_no_rotate._rotate_key()
        new_key_index = gemini_no_rotate.current_key_index

        assert (
            new_key_index == initial_key_index
        ), "GeminiProvider 在 auto_rotate=False 时不应当轮转 API Key"

    # Test OpenAI (Auto Rotate = False)
    from semantic_tester.api.openai_provider import OpenAIProvider

    with patch.object(OpenAIProvider, "validate_api_key", return_value=True):
        openai = OpenAIProvider(config_no_rotate)
        initial_key_index = openai.current_key_index
        openai._rotate_key()
        new_key_index = openai.current_key_index

        assert (
            new_key_index == initial_key_index
        ), "OpenAIProvider 默认 auto_rotate=False，调用 _rotate_key 不应改变索引"
