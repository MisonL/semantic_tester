import unittest
import time
from unittest.mock import MagicMock, patch
import logging

from semantic_tester.api.dify_provider import DifyProvider, RateLimitError
from semantic_tester.api.openai_provider import OpenAIProvider

# Configure logging to see output
logging.basicConfig(level=logging.INFO)


class TestRobustRotation(unittest.TestCase):
    def setUp(self):
        self.dify_config = {
            "name": "Dify",
            "id": "dify",
            "api_keys": ["dify-key-1", "dify-key-2", "dify-key-3"],
            "base_url": "https://api.dify.ai/v1",
            "auto_rotate": True,  # Enable for Dify to test rotation logic
        }
        self.openai_config = {
            "name": "OpenAI",
            "id": "openai",
            "api_keys": ["sk-key-1", "sk-key-2", "sk-key-3"],
            "auto_rotate": False,  # Default is False for OpenAI
        }

    def test_dify_rotation_logic(self):
        """Test DifyProvider's advanced rotation logic"""
        provider = DifyProvider(self.dify_config)

        # Initial state
        self.assertEqual(provider.current_key_index, 0)

        # 1. Normal Rotation
        provider._rotate_key(force_rotate=True)
        self.assertEqual(provider.current_key_index, 1)

        # 2. Cooldown Logic
        # Mark key 2 (index 1) as cooldown for 10 seconds
        current_key = provider.api_keys[1]
        provider.key_cooldown_until[current_key] = time.time() + 10

        # Mark key 3 (index 2) as available
        # Rotating should skip key 2 and go to key 3
        provider._rotate_key(force_rotate=True)
        self.assertEqual(provider.current_key_index, 2)

        # 3. All keys cooldown
        # Mark key 3 as cooldown too
        key3 = provider.api_keys[2]
        provider.key_cooldown_until[key3] = time.time() + 10
        # Mark key 1 as cooldown
        key1 = provider.api_keys[0]
        provider.key_cooldown_until[key1] = time.time() + 10

        # Rotating with sleep (mock time.sleep to avoid waiting)
        with patch("time.sleep") as mock_sleep:
            provider._rotate_key(force_rotate=True)
            # It should have slept because all keys are cooldown
            mock_sleep.assert_called()
            # After sleep, it should pick one (logic recursively calls rotate,
            # but since we mocked sleep, it effectively just picks one or loop logic handles it?
            # Creating a situation where all keys are cooldown makes it wait inside lock?
            # No, wait_time_outside_lock logic.

    def test_openai_force_rotation(self):
        """Test OpenAIProvider's force rotation even when auto_rotate is False"""
        # Patch validate_api_key to avoid real API calls
        with (
            patch.object(OpenAIProvider, "validate_api_key", return_value=True),
            patch.object(OpenAIProvider, "_configure_client"),
        ):

            provider = OpenAIProvider(self.openai_config)
            self.assertEqual(provider.current_key_index, 0)

            # Normal rotate should do nothing because auto_rotate is False
            provider._rotate_key()
            self.assertEqual(provider.current_key_index, 0)

            # Force rotate should work
            provider._rotate_key(force_rotate=True)
            self.assertEqual(provider.current_key_index, 1)

    def test_dify_error_handling_trigger(self):
        """Test DifyProvider triggers rotation on RateLimitError"""
        provider = DifyProvider(self.dify_config)

        # Mock _send_dify_request to raise RateLimitError
        provider._send_dify_request = MagicMock(
            side_effect=RateLimitError("Rate limit exceeded, retry in 5s")
        )
        provider.show_waiting_indicator = MagicMock()  # Mock UI

        # Mock _rotate_key to verify call
        original_rotate = provider._rotate_key
        provider._rotate_key = MagicMock(wraps=original_rotate)

        # Mock time.sleep to avoid actual waiting
        with patch("time.sleep"):
            result = provider.check_semantic_similarity("q", "a", "d")

        # It should have called _rotate_key multiple times
        self.assertTrue(provider._rotate_key.call_count >= 1)
        self.assertEqual(result, ("错误", "Dify API 调用多次重试失败"))

        # Check if force_rotate=True was passed
        provider._rotate_key.assert_called_with(force_rotate=True)

    def test_anthropic_rotation(self):
        """Test AnthropicProvider's rotation and cooldown"""
        # Mock the anthropic module since it might not be installed
        mock_anthropic_mod = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}):
            from semantic_tester.api.anthropic_provider import AnthropicProvider

            config = {
                "name": "Anthropic",
                "id": "anthropic",
                "api_keys": ["key-1", "key-2"],
                "auto_rotate": True,
            }
            with patch.object(AnthropicProvider, "_configure_client"):
                provider = AnthropicProvider(config)
                provider.client = MagicMock()
                self.assertEqual(provider.current_key_index, 0)

                # 模拟 429 错误触发
                provider._extract_retry_delay = MagicMock(return_value=5)
                provider.show_waiting_indicator = MagicMock()

                # 模拟消息创建抛出异常
                # 注意：这里我们重新 mock Anthropic 类，因为它在 analyze_semantic 内部被导入
                with patch("anthropic.Anthropic") as mock_anthropic_class:
                    mock_client = mock_anthropic_class.return_value
                    # 某些实现中可能是 client.messages.create
                    mock_client.messages.create.side_effect = Exception(
                        "rate_limit: retry in 5s"
                    )

                    with patch("time.sleep"):
                        result = provider.analyze_semantic("q", "a", "k")

                self.assertEqual(result["success"], False)
                self.assertTrue(provider.key_cooldown_until["key-1"] > time.time())
                self.assertEqual(provider.current_key_index, 1)

    def test_iflow_rotation(self):
        """Test IflowProvider's rotation and cooldown"""
        from semantic_tester.api.iflow_provider import IflowProvider

        config = {
            "name": "iFlow",
            "id": "iflow",
            "api_keys": ["ik1", "ik2"],
            "auto_rotate": True,
        }
        provider = IflowProvider(config)
        self.assertEqual(provider.current_key_index, 0)

        # 模拟 429
        with patch.object(provider.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            # requests raises_for_status doesn't raise if we don't call it,
            # but our code calls it or checks status
            # In iFlowProvider, it raises Exception if status is not 200 or similar
            # Wait, let's check iFlow logic again.

            # The code does: response = self.client.post(...) then response.raise_for_status()
            from requests.exceptions import HTTPError

            mock_response.raise_for_status.side_effect = HTTPError(
                "429 Client Error", response=mock_response
            )
            mock_post.return_value = mock_response

            with patch("time.sleep"):
                result, reason = provider.check_semantic_similarity("q", "a", "k")

        self.assertEqual(result, "错误")
        self.assertTrue(provider.key_cooldown_until["ik1"] > time.time())
        self.assertEqual(provider.current_key_index, 1)


if __name__ == "__main__":
    unittest.main()
