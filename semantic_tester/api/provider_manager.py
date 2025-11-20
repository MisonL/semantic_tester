"""
AI 供应商管理器

负责管理多个 AI 供应商实例，提供统一的接口和供应商选择功能。
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from .base_provider import AIProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .dify_provider import DifyProvider
from .iflow_provider import IflowProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """AI 供应商管理器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化供应商管理器

        Args:
            config: 全局配置字典
        """
        self.config = config
        self.providers: Dict[str, AIProvider] = {}
        self.current_provider_id: Optional[str] = None

        # 初始化所有可用的供应商
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化所有可用的供应商"""
        logger.info("开始初始化 AI 供应商...")

        # 获取供应商配置
        ai_providers = self.config.get("ai_providers", [])
        if not ai_providers:
            # 如果没有配置供应商，使用默认的 Gemini
            ai_providers = [{"index": 1, "name": "Gemini", "id": "gemini"}]

        # 批量处理配置
        batch_config = self.config.get("batch", {})

        for provider_config in ai_providers:
            provider_id = provider_config["id"]
            provider_name = provider_config["name"]

            try:
                # 根据供应商 ID 创建相应的供应商实例
                provider = self._create_provider(
                    provider_id, provider_name, batch_config
                )
                if provider:
                    self.providers[provider_id] = provider
                    logger.info(f"成功初始化供应商: {provider_name} ({provider_id})")
            except Exception as e:
                logger.error(f"初始化供应商 {provider_name} ({provider_id}) 失败: {e}")

        # 验证所有供应商的API密钥并自动选择第一个有效的
        self._validate_and_auto_select_provider()

    def _validate_and_auto_select_provider(self):
        """验证所有供应商的API密钥并自动选择第一个有效的"""
        if not self.providers:
            logger.warning("没有可用的 AI 供应商")
            return

        logger.info("开始验证供应商API密钥...")
        valid_providers = []
        configured_providers = []
        unconfigured_providers = []

        for provider_id, provider in self.providers.items():
            if not provider.is_configured():
                logger.info(f"供应商 {provider.name} 未配置")
                unconfigured_providers.append((provider_id, provider))
                continue

            configured_providers.append((provider_id, provider))

            # 验证API密钥
            is_valid = self._validate_provider_api_key(provider)
            if is_valid:
                valid_providers.append((provider_id, provider))
                logger.info(f"✅ 供应商 {provider.name} API密钥验证通过")
            else:
                logger.warning(f"❌ 供应商 {provider.name} API密钥验证失败")

        # 优先选择策略：有效供应商 > 已配置供应商 > 未配置供应商
        if valid_providers:
            # 选择第一个API验证通过的供应商
            first_valid_id, first_valid_provider = valid_providers[0]
            self.current_provider_id = first_valid_id
            logger.info(f"自动选择第一个有效供应商: {first_valid_provider.name}")

            # 如果有多个有效供应商，提示用户可以在菜单中切换
            if len(valid_providers) > 1:
                logger.info(f"检测到 {len(valid_providers)} 个有效供应商")
                logger.info("可在主菜单选择'AI供应商管理'->'切换当前供应商'进行切换")
        elif configured_providers:
            # 如果没有有效供应商但有已配置的供应商，选择第一个已配置的
            first_configured_id, first_configured_provider = configured_providers[0]
            self.current_provider_id = first_configured_id
            logger.warning(f"没有API验证通过的供应商，选择第一个已配置供应商: {first_configured_provider.name}")
        elif unconfigured_providers:
            # 最后回退到未配置的供应商
            first_unconfigured_id, first_unconfigured_provider = unconfigured_providers[0]
            self.current_provider_id = first_unconfigured_id
            logger.warning("所有供应商都未配置，选择第一个未配置供应商")
            logger.info(f"选择供应商: {first_unconfigured_provider.name}")
        else:
            logger.error("无法选择供应商：没有任何可用供应商")

    def _validate_provider_api_key(self, provider: AIProvider) -> bool:
        """
        验证供应商的API密钥

        Args:
            provider: 供应商实例

        Returns:
            bool: API密钥是否有效
        """
        try:
            # 获取供应商的API密钥
            api_key = self._get_provider_api_key(provider)
            if not api_key:
                return False

            # 调用供应商的validate_api_key方法
            return provider.validate_api_key(api_key)
        except Exception as e:
            logger.error(f"验证供应商 {provider.name} API密钥时出错: {e}")
            return False

    def _get_provider_api_key(self, provider: AIProvider) -> Optional[str]:
        """
        获取供应商的API密钥

        Args:
            provider: 供应商实例

        Returns:
            Optional[str]: API密钥，如果未配置返回None
        """
        provider_id = provider.id

        if provider_id == "gemini":
            # Gemini支持多密钥，返回第一个
            gemini_keys = self.config.get("gemini_api_keys", [])
            return gemini_keys[0] if gemini_keys else None
        elif provider_id == "openai":
            openai_config = self.config.get("openai", {})
            return openai_config.get("api_key", "")
        elif provider_id == "anthropic":
            anthropic_config = self.config.get("anthropic", {})
            return anthropic_config.get("api_key", "")
        elif provider_id == "dify":
            dify_config = self.config.get("dify", {})
            return dify_config.get("api_key", "")
        elif provider_id == "iflow":
            iflow_config = self.config.get("iflow", {})
            return iflow_config.get("api_key", "")

        return None

    def _create_provider(
        self, provider_id: str, provider_name: str, batch_config: Dict[str, Any]
    ) -> Optional[AIProvider]:
        """
        创建供应商实例

        Args:
            provider_id: 供应商 ID
            provider_name: 供应商名称
            batch_config: 批量处理配置

        Returns:
            Optional[AIProvider]: 供应商实例，创建失败返回 None
        """
        if provider_id == "gemini":
            gemini_keys = self.config.get("gemini_api_keys", [])
            gemini_model = self.config.get("gemini_model", "gemini-2.0-flash-exp")

            if not gemini_keys:
                logger.warning("Gemini API 密钥未配置，将创建未配置的供应商实例")

            provider_config = {
                "name": provider_name,
                "id": provider_id,
                "api_keys": gemini_keys,
                "model": gemini_model,
                **batch_config,
            }
            return GeminiProvider(provider_config)

        elif provider_id == "openai":
            openai_config = self.config.get("openai", {})
            api_keys = openai_config.get("api_keys", [])
            model = openai_config.get("model", "gpt-4o")
            base_url = openai_config.get("base_url", "https://api.openai.com/v1")
            has_config = openai_config.get("has_config", False)

            if not has_config:
                logger.warning("OpenAI API 密钥未配置或为模板值，将创建未配置的供应商实例")

            provider_config = {
                "name": provider_name,
                "id": provider_id,
                "api_keys": api_keys,
                "model": model,
                "base_url": base_url,
                "has_config": has_config,
                **batch_config,
            }
            return OpenAIProvider(provider_config)

        elif provider_id == "anthropic":
            anthropic_config = self.config.get("anthropic", {})
            api_keys = anthropic_config.get("api_keys", [])
            model = anthropic_config.get("model", "claude-sonnet-4-20250514")
            base_url = anthropic_config.get("base_url", "https://api.anthropic.com")
            has_config = anthropic_config.get("has_config", False)

            if not has_config:
                logger.warning("Anthropic API 密钥未配置或为模板值，将创建未配置的供应商实例")

            provider_config = {
                "name": provider_name,
                "id": provider_id,
                "api_keys": api_keys,
                "model": model,
                "base_url": base_url,
                "has_config": has_config,
                **batch_config,
            }
            return AnthropicProvider(provider_config)

        elif provider_id == "dify":
            dify_config = self.config.get("dify", {})
            api_key = dify_config.get("api_key", "")
            base_url = dify_config.get("base_url", "https://api.dify.ai/v1")
            app_id = dify_config.get("app_id", "")
            has_config = dify_config.get("has_config", bool(api_key))

            if not has_config:
                logger.warning("Dify API 密钥未配置或为模板值，将创建未配置的供应商实例")

            provider_config = {
                "name": provider_name,
                "id": provider_id,
                "api_key": api_key,
                "base_url": base_url,
                "app_id": app_id,
                "has_config": has_config,
                **batch_config,
            }
            return DifyProvider(provider_config)

        elif provider_id == "iflow":
            iflow_config = self.config.get("iflow", {})
            api_key = iflow_config.get("api_key", "")
            model = iflow_config.get("model", "qwen3-max")
            base_url = iflow_config.get("base_url", "https://apis.iflow.cn/v1")
            has_config = iflow_config.get("has_config", False)

            if not has_config:
                logger.warning("iFlow API 密钥未配置或为模板值，将创建未配置的供应商实例")

            provider_config = {
                "name": provider_name,
                "id": provider_id,
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
                "has_config": has_config,
                **batch_config,
            }
            return IflowProvider(provider_config)

        else:
            logger.warning(f"未知的供应商 ID: {provider_id}")
            return None

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的供应商信息

        Returns:
            List[Dict[str, Any]]: 供应商信息列表
        """
        providers_info = []
        for provider_id, provider in self.providers.items():
            info = provider.get_provider_info()
            info["is_current"] = provider_id == self.current_provider_id
            providers_info.append(info)

        return providers_info

    def get_configured_providers(self) -> List[Dict[str, Any]]:
        """
        获取已正确配置的供应商

        Returns:
            List[Dict[str, Any]]: 已配置的供应商信息列表
        """
        return [
            provider.get_provider_info()
            for provider in self.providers.values()
            if provider.is_configured()
        ]

    def get_provider(self, provider_id: Optional[str] = None) -> Optional[AIProvider]:
        """
        获取指定的供应商实例

        Args:
            provider_id: 供应商 ID，如果为 None 则返回当前供应商

        Returns:
            Optional[AIProvider]: 供应商实例
        """
        if provider_id is None:
            provider_id = self.current_provider_id

        if provider_id and provider_id in self.providers:
            return self.providers[provider_id]

        return None

    def set_current_provider(self, provider_id: str) -> bool:
        """
        设置当前供应商

        Args:
            provider_id: 供应商 ID

        Returns:
            bool: 设置是否成功
        """
        if provider_id in self.providers:
            self.current_provider_id = provider_id
            provider = self.providers[provider_id]
            logger.info(f"已切换到供应商: {provider.name}")
            return True
        else:
            logger.error(f"供应商 {provider_id} 不存在")
            return False

    def get_current_provider(self) -> Optional[AIProvider]:
        """
        获取当前供应商实例

        Returns:
            Optional[AIProvider]: 当前供应商实例
        """
        return self.get_provider()

    def get_current_provider_name(self) -> str:
        """获取当前供应商名称"""
        provider = self.get_current_provider()
        return provider.name if provider else "无"

    def check_semantic_similarity(
        self,
        question: str,
        ai_answer: str,
        source_document: str,
        provider_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        使用指定供应商执行语义相似度检查

        Args:
            question: 问题内容
            ai_answer: AI回答内容
            source_document: 源文档内容
            provider_id: 供应商 ID（可选）
            model: 模型名称（可选）

        Returns:
            Tuple[str, str]: (结果, 原因)
        """
        provider = self.get_provider(provider_id)
        if not provider:
            return "错误", "指定的供应商不可用"

        if not provider.is_configured():
            return "错误", f"供应商 {provider.name} 未正确配置"

        return provider.check_semantic_similarity(
            question, ai_answer, source_document, model
        )

    def has_configured_providers(self) -> bool:
        """
        检查是否有已配置的供应商

        Returns:
            bool: 是否有已配置的供应商
        """
        return any(provider.is_configured() for provider in self.providers.values())

    def get_provider_choices(self) -> List[Tuple[str, str, bool]]:
        """
        获取供应商选择列表

        Returns:
            List[Tuple[str, str, bool]]: (ID, 显示名称, 是否已配置)
        """
        choices = []
        for provider_id, provider in self.providers.items():
            display_name = f"{provider.name} ({'已配置' if provider.is_configured() else '未配置'})"
            choices.append((provider_id, display_name, provider.is_configured()))

        return choices

    def print_provider_status(self):
        """打印供应商状态"""
        print(f"\n=== AI 供应商状态 ===")
        print(f"总供应商数: {len(self.providers)}")
        current_provider = self.get_current_provider()
        current_name = current_provider.name if current_provider else "无"
        print(f"当前供应商: {current_name}")
        print(f"已配置供应商数: {len(self.get_configured_providers())}")

        print(f"\n--- 供应商详情 ---")
        for i, (provider_id, provider) in enumerate(self.providers.items(), 1):
            status = "✅ 已配置" if provider.is_configured() else "❌ 未配置"
            current = " (当前)" if provider_id == self.current_provider_id else ""
            print(f"{i}. {provider.name}{current} - {status}")

            if provider.is_configured():
                models = provider.get_models()
                default_model = provider.get_default_model()
                print(f"   模型: {default_model} (共 {len(models)} 个可用)")

    def get_provider_statistics(self) -> Dict[str, Any]:
        """
        获取供应商统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_providers = len(self.providers)
        configured_providers = len(self.get_configured_providers())

        provider_stats = {}
        for provider_id, provider in self.providers.items():
            provider_stats[provider_id] = {
                "name": provider.name,
                "configured": provider.is_configured(),
                "models_count": len(provider.get_models()),
                "default_model": provider.get_default_model(),
            }

        return {
            "total_providers": total_providers,
            "configured_providers": configured_providers,
            "current_provider": self.current_provider_id,
            "providers": provider_stats,
        }

    def get_provider_validation_status(self) -> Dict[str, Any]:
        """
        获取所有供应商的验证状态

        Returns:
            Dict[str, Any]: 验证状态信息
        """
        validation_results = {}
        valid_count = 0
        invalid_count = 0
        unconfigured_count = 0

        for provider_id, provider in self.providers.items():
            if not provider.is_configured():
                validation_results[provider_id] = {
                    "name": provider.name,
                    "status": "未配置",
                    "valid": False,
                    "message": "供应商未配置API密钥"
                }
                unconfigured_count += 1
                continue

            # 验证API密钥
            is_valid = self._validate_provider_api_key(provider)
            if is_valid:
                validation_results[provider_id] = {
                    "name": provider.name,
                    "status": "验证通过",
                    "valid": True,
                    "message": "API密钥有效"
                }
                valid_count += 1
            else:
                validation_results[provider_id] = {
                    "name": provider.name,
                    "status": "验证失败",
                    "valid": False,
                    "message": "API密钥无效或无法连接"
                }
                invalid_count += 1

        return {
            "total": len(self.providers),
            "valid": valid_count,
            "invalid": invalid_count,
            "unconfigured": unconfigured_count,
            "results": validation_results
        }

    def revalidate_all_providers(self):
        """重新验证所有供应商的API密钥"""
        logger.info("重新验证所有供应商API密钥...")
        self._validate_and_auto_select_provider()

    def switch_to_first_valid_provider(self) -> bool:
        """
        切换到第一个有效的供应商

        Returns:
            bool: 是否成功切换到有效供应商
        """
        for provider_id, provider in self.providers.items():
            if not provider.is_configured():
                continue

            if self._validate_provider_api_key(provider):
                if self.set_current_provider(provider_id):
                    logger.info(f"已切换到第一个有效供应商: {provider.name}")
                    return True

        logger.warning("没有可用的有效供应商")
        return False
