import sys
import os
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from semantic_tester.api.provider_manager import ProviderManager
from semantic_tester.config.environment import EnvManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rotation_configuration():
    logger.info("Testing Provider Rotation Configuration...")
    
    # Mock EnvManager
    mock_env = MagicMock(spec=EnvManager)
    mock_env.get_gemini_api_keys.return_value = ["key1", "key2"]
    mock_env.get_gemini_model.return_value = "gemini-pro"
    
    mock_env.get_openai_config.return_value = {
        "api_keys": ["key1", "key2"],
        "model": "gpt-4",
        "base_url": "url",
        "has_config": True
    }
    
    mock_env.get_anthropic_config.return_value = {
        "api_keys": ["key1", "key2"],
        "model": "claude",
        "base_url": "url",
        "has_config": True
    }
    
    mock_env.get_dify_config.return_value = {
        "api_keys": ["key1", "key2"],
        "base_url": "url",
        "app_id": "id",
        "has_config": True
    }
    
    mock_env.get_iflow_config.return_value = {
        "api_keys": ["key1", "key2"],
        "model": "qwen",
        "base_url": "url",
        "has_config": True
    }
    
    mock_env.get_batch_config.return_value = {}
    mock_env.get_api_config.return_value = {}
    
    mock_env.get_ai_providers.return_value = [
        {"index": 1, "name": "Gemini", "id": "gemini"},
        {"index": 2, "name": "OpenAI", "id": "openai"},
        {"index": 3, "name": "Anthropic", "id": "anthropic"},
        {"index": 4, "name": "Dify", "id": "dify"},
        {"index": 5, "name": "iFlow", "id": "iflow"},
    ]

    # Initialize ProviderManager
    manager = ProviderManager(mock_env)
    
    # Check Gemini
    gemini = manager.get_provider("gemini")
    if gemini.auto_rotate:
        logger.info("✅ Gemini auto_rotate is True (Correct)")
    else:
        logger.error("❌ Gemini auto_rotate is False (Incorrect)")
        
    # Check OpenAI
    openai = manager.get_provider("openai")
    if not openai.auto_rotate:
        logger.info("✅ OpenAI auto_rotate is False (Correct)")
    else:
        logger.error("❌ OpenAI auto_rotate is True (Incorrect)")

    # Check Anthropic
    anthropic = manager.get_provider("anthropic")
    if not anthropic.auto_rotate:
        logger.info("✅ Anthropic auto_rotate is False (Correct)")
    else:
        logger.error("❌ Anthropic auto_rotate is True (Incorrect)")

    # Check Dify
    dify = manager.get_provider("dify")
    if not dify.auto_rotate:
        logger.info("✅ Dify auto_rotate is False (Correct)")
    else:
        logger.error("❌ Dify auto_rotate is True (Incorrect)")

    # Check iFlow
    iflow = manager.get_provider("iflow")
    if iflow is None:
        logger.error(f"❌ iFlow provider is None. Available providers: {list(manager.providers.keys())}")
    elif not iflow.auto_rotate:
        logger.info("✅ iFlow auto_rotate is False (Correct)")
    else:
        logger.error("❌ iFlow auto_rotate is True (Incorrect)")

def test_rotation_logic():
    logger.info("\nTesting Rotation Logic...")
    
    # Mock config for a provider with auto_rotate=False
    config_no_rotate = {
        "name": "TestNoRotate",
        "id": "test_no_rotate",
        "api_keys": ["key1", "key2"],
        "auto_rotate": False
    }
    
    # Mock config for a provider with auto_rotate=True
    config_rotate = {
        "name": "TestRotate",
        "id": "test_rotate",
        "api_keys": ["key1", "key2"],
        "auto_rotate": True
    }
    
    from semantic_tester.api.gemini_provider import GeminiProvider
    
    # Test Gemini (Auto Rotate = True)
    logger.info("Testing Gemini Provider (Auto Rotate = True)...")
    with patch.object(GeminiProvider, 'validate_api_key', return_value=True):
        gemini = GeminiProvider(config_rotate)
        # Manually set api_keys because __init__ filters them based on validation
        # But since we mocked validate_api_key, they should be there.
        # However, _initialize_api_keys calls validate_api_key.
        
        initial_key_index = gemini.current_key_index
        gemini._rotate_key()
        new_key_index = gemini.current_key_index
        
        if initial_key_index != new_key_index:
            logger.info(f"✅ Gemini rotated key: {initial_key_index} -> {new_key_index}")
        else:
            logger.error(f"❌ Gemini did not rotate key. Keys: {gemini.api_keys}")

    # Test Gemini with Auto Rotate = False (Simulated)
    logger.info("Testing Gemini Provider (Auto Rotate = False)...")
    with patch.object(GeminiProvider, 'validate_api_key', return_value=True):
        gemini_no_rotate = GeminiProvider(config_no_rotate)
        initial_key_index = gemini_no_rotate.current_key_index
        gemini_no_rotate._rotate_key()
        new_key_index = gemini_no_rotate.current_key_index
        
        if initial_key_index == new_key_index:
            logger.info(f"✅ Gemini did not rotate key: {initial_key_index} -> {new_key_index}")
        else:
            logger.error(f"❌ Gemini rotated key unexpectedly: {initial_key_index} -> {new_key_index}")

    # Test OpenAI (Auto Rotate = False)
    from semantic_tester.api.openai_provider import OpenAIProvider
    logger.info("Testing OpenAI Provider (Auto Rotate = False)...")
    with patch.object(OpenAIProvider, 'validate_api_key', return_value=True):
        openai = OpenAIProvider(config_no_rotate)
        initial_key_index = openai.current_key_index
        openai._rotate_key()
        new_key_index = openai.current_key_index
        
        if initial_key_index == new_key_index:
            logger.info(f"✅ OpenAI did not rotate key: {initial_key_index} -> {new_key_index}")
        else:
            logger.error(f"❌ OpenAI rotated key unexpectedly: {initial_key_index} -> {new_key_index}")

if __name__ == "__main__":
    test_rotation_configuration()
    test_rotation_logic()
