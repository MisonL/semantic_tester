"""
AI 供应商管理器

负责管理多个 AI 供应商实例，提供统一的接口和供应商选择功能。
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING

from .base_provider import AIProvider
from .gemini_provider import GeminiProvider

if TYPE_CHECKING:
    from ..config.environment import EnvManager
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .dify_provider import DifyProvider
from .iflow_provider import IflowProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """AI 供应商管理器"""

    def __init__(self, config: "EnvManager"):
        """
        初始化供应商管理器

        Args:
            config: 环境管理器实例
        """
        self.config = config
        self.providers: Dict[str, AIProvider] = {}
        self.current_provider_id: Optional[str] = None

        # 初始化所有可用的供应商
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化多渠道供应商 (唯一支持的配置方式)"""
        logger.debug("开始初始化 AI 供应商 (多渠道驱动)...")

        # 批量处理配置
        batch_config = self.config.get_batch_config()

        # 初始化多渠道配置
        channels_config = self.config.get_channels_config()
        self.channels_list: List[dict] = []  # 存储配置用于后续并发映射
        for ch_cfg in channels_config:
            try:
                channel_provider = self._create_channel_provider(ch_cfg, batch_config)
                if channel_provider:
                    # 将渠道作为唯一的供应商存入
                    ch_id = ch_cfg["id"]
                    self.providers[ch_id] = channel_provider
                    self.channels_list.append(ch_cfg)
                    logger.debug(f"成功初始化渠道: {ch_cfg['display_name']} ({ch_id})")
            except Exception as e:
                logger.error(f"初始化渠道 {ch_cfg['display_name']} 失败: {e}")

        # 验证所有供应商的API密钥并自动选择第一个有效的
        self._validate_and_auto_select_provider()

    def _create_channel_provider(
        self, ch_cfg: dict, batch_config: dict
    ) -> Optional[AIProvider]:
        """从渠道配置创建 Provider 实例"""
        ch_type = ch_cfg["type"]

        # 基础配置项
        provider_config = {
            "name": ch_cfg["display_name"],
            "id": ch_cfg["id"],
            "api_keys": ch_cfg["api_keys"],
            "model": ch_cfg["model"],
            "base_url": ch_cfg["base_url"],
            "app_id": ch_cfg.get("app_id"),
            "has_config": ch_cfg["has_config"],
            "auto_rotate": True if "gemini" in ch_type else False,
            **batch_config,
        }

        # 根据类型实例化
        if "gemini" in ch_type:
            return GeminiProvider(provider_config)
        elif "openai" in ch_type:
            return OpenAIProvider(provider_config)
        elif "anthropic" in ch_type:
            return AnthropicProvider(provider_config)
        elif "dify" in ch_type:
            return DifyProvider(provider_config)
        elif "iflow" in ch_type:
            return IflowProvider(provider_config)

        return None

    def get_configured_providers_list(self) -> List[AIProvider]:
        """获取已配置的渠道供应商列表"""
        return [p for p in self.providers.values() if p.is_configured()]

    def get_channel_providers(self) -> List[dict]:
        """获取多渠道(新)供应商列表"""
        return self.channels_list

    def validate_all_configured_channels(self) -> List[Dict[str, Any]]:
        """
        实时并发验证所有已配置渠道的 API 密钥有效性

        Returns:
            List[Dict[str, Any]]: 验证结果列表，包含 {id, name, type, valid, message}
        """
        import threading

        results = []
        lock = threading.Lock()

        def _validate_worker(ch_cfg):
            ch_id = ch_cfg["id"]
            provider = self.providers.get(ch_id)
            if not provider:
                with lock:
                    results.append(
                        {
                            "id": ch_id,
                            "name": ch_cfg["display_name"],
                            "valid": False,
                            "message": "Provider 未初始化",
                        }
                    )
                return

            api_key = (
                provider.config.get("api_keys", [])[0]
                if provider.config.get("api_keys")
                else None
            )
            is_valid = False
            msg = ""
            try:
                if not api_key:
                    msg = "未配置 API 密钥"
                else:
                    is_valid = provider.validate_api_key(api_key)
                    msg = "验证通过" if is_valid else "API 密钥无效"
            except Exception as e:
                msg = f"验证异常: {str(e)}"

            with lock:
                results.append(
                    {
                        "id": ch_id,
                        "name": provider.name,
                        "type": ch_cfg["type"],
                        "valid": is_valid,
                        "message": msg,
                    }
                )

        # 获取总并发限制（各渠道并发数之和）作为线程池上限
        max_workers = sum(ch.get("concurrency", 1) for ch in self.channels_list)
        if max_workers <= 0:
            max_workers = 1

        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交验证任务
            for ch in self.channels_list:
                executor.submit(_validate_worker, ch)

        # 记录验证通过的 ID 列表以便过滤
        self.valid_channel_ids = [r["id"] for r in results if r["valid"]]
        return sorted(results, key=lambda x: x["id"])

    def _validate_and_auto_select_provider(self):
        """快速选择供应商（启动时跳过API验证，仅检查配置）"""
        if not self.providers:
            logger.warning("没有可用的 AI 供应商")
            return

        logger.info("检查供应商配置状态...")
        configured_providers = []
        unconfigured_providers = []

        for provider_id, provider in self.providers.items():
            if not provider.is_configured():
                logger.debug(f"供应商 {provider.name} 未配置")
                unconfigured_providers.append((provider_id, provider))
                continue

            configured_providers.append((provider_id, provider))
            logger.debug(f"✅ 供应商 {provider.name} 已配置")

        # 优先选择策略：已配置供应商 > 未配置供应商
        # 注意：启动时不再进行API验证，验证推迟到实际使用或用户手动触发
        if configured_providers:
            # 选择第一个已配置的供应商
            first_configured_id, first_configured_provider = configured_providers[0]
            self.current_provider_id = first_configured_id
            logger.info(f"自动选择供应商: {first_configured_provider.name}")

            # 如果有多个已配置供应商，提示用户可以在菜单中切换
            if len(configured_providers) > 1:
                logger.debug(f"检测到 {len(configured_providers)} 个已配置供应商")
                logger.debug("可在主菜单选择'AI供应商管理'->'切换当前供应商'进行切换")
        elif unconfigured_providers:
            # 回退到未配置的供应商
            first_unconfigured_id, first_unconfigured_provider = unconfigured_providers[
                0
            ]
            self.current_provider_id = first_unconfigured_id
            logger.info(f"选择供应商: {first_unconfigured_provider.name}（未配置）")
        else:
            logger.error("无法选择供应商：没有任何可用供应商")

    def get_provider(self, provider_id: Optional[str] = None) -> Optional[AIProvider]:
        """
        获取指定的供应商实例

        Args:
            provider_id: 供应商 ID, 如果为 None 则返回当前供应商

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
        stream: bool = False,
        show_thinking: bool = True,
        stream_callback: Optional[callable] = None,  # 新增回调参数
    ) -> Tuple[str, str]:
        """使用指定供应商执行语义相似度检查

        Args:
            question: 问题内容
            ai_answer: AI回答内容
            source_document: 源文档内容
            provider_id: 供应商 ID (可选)
            model: 模型名称 (可选)
            stream: 是否启用流式输出 (可选)
            stream: 是否启用流式输出 (可选)
            show_thinking: 是否显示思维链/推理过程 (仅在模型支持时生效)
            stream_callback: 流式输出回调函数 (可选)

        Returns:
            Tuple[str, str]: (结果, 原因)
        """
        provider = self.get_provider(provider_id)
        if not provider:
            return "错误", "指定的供应商不可用"

        if not provider.is_configured():
            return "错误", f"供应商 {provider.name} 未正确配置"

        # 注意：在并发模式下 (stream_callback 存在时)，不要执行 console.print
        # 否则会干扰 WorkerTableUI 的全屏 Live 渲染
        # 仅在非并发模式（stream_callback 为 None）且启用流式时显示预览面板

        return provider.check_semantic_similarity(
            question,
            ai_answer,
            source_document,
            model,
            stream=stream,
            show_thinking=show_thinking,
            stream_callback=stream_callback,  # 传递给 provider
        )

    def get_preset_channel_configs(
        self, verified_only: bool = True
    ) -> List[Tuple[AIProvider, int]]:
        """
        获取环境预设的渠道配置

        Args:
            verified_only: 是否仅返回通过验证的渠道 (需先调用 validate_all_configured_channels)
        """
        configs = []
        valid_ids = getattr(self, "valid_channel_ids", None) if verified_only else None

        for ch_cfg in self.channels_list:
            ch_id = ch_cfg["id"]
            # 如果要求验证且有验证记录，则进行过滤
            if verified_only and valid_ids is not None:
                if ch_id not in valid_ids:
                    continue

            provider = self.get_provider(ch_id)
            if provider:
                configs.append((provider, ch_cfg["concurrency"]))
        return configs
