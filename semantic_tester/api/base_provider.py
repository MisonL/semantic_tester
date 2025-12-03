"""
AI供应商抽象基类

定义所有AI供应商必须实现的接口，确保统一的使用体验。
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """AI 供应商抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化AI供应商

        Args:
            config: 供应商配置字典
        """
        self.config = config
        self.name = config.get("name", "Unknown")
        self.id = config.get("id", "unknown")
        self.waiting_indicators = config.get("waiting_indicators", ["⣾", "⣽", "⣻", "⢿"])
        self.waiting_text = config.get("waiting_text", "正在处理")
        self.waiting_delay = config.get("waiting_delay", 0.1)
        self.auto_rotate = config.get("auto_rotate", False)

    @abstractmethod
    def get_models(self) -> List[str]:
        """
        获取可用的模型列表

        Returns:
            List[str]: 模型名称列表
        """
        pass

    @abstractmethod
    def validate_api_key(self, api_key: str) -> bool:
        """
        验证API密钥有效性

        Args:
            api_key: API密钥

        Returns:
            bool: 密钥是否有效
        """
        pass

    @abstractmethod
    def check_semantic_similarity(
        self,
        question: str,
        ai_answer: str,
        source_document: str,
        model: Optional[str] = None,
        stream: bool = False,
        show_thinking: bool = False,
    ) -> tuple[str, str]:
        """
        执行语义相似度检查

        Args:
            question: 问题内容
            ai_answer: AI回答内容
            source_document: 源文档内容
            model: 使用的模型（可选）
            stream: 是否使用流式输出（默认False保持向后兼容）
            show_thinking: 是否显示思维链过程（默认False）

        Returns:
            tuple[str, str]: (结果, 原因)，结果为"是"/"否"/"错误"
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        检查供应商是否已正确配置

        Returns:
            bool: 是否已配置
        """
        pass

    def get_default_model(self) -> str:
        """
        获取默认模型

        Returns:
            str: 默认模型名称
        """
        models = self.get_models()
        return models[0] if models else ""

    def show_waiting_indicator(self, stop_event: threading.Event):
        """显示等待状态指示器"""
        from rich.live import Live
        from rich.spinner import Spinner
        from rich.text import Text

        spinner = Spinner(
            "dots", text=Text(f" {self.name}: {self.waiting_text}...", style="cyan")
        )

        # 使用 Live 上下文管理器显示加载动画
        with Live(spinner, refresh_per_second=10, transient=True):
            while not stop_event.is_set():
                time.sleep(0.1)

    def get_provider_info(self) -> Dict[str, Any]:
        """
        获取供应商信息

        Returns:
            Dict[str, Any]: 供应商信息
        """
        return {
            "name": self.name,
            "id": self.id,
            "models": self.get_models(),
            "configured": self.is_configured(),
            "default_model": self.get_default_model(),
        }

    def __str__(self) -> str:
        """字符串表示"""
        status = "已配置" if self.is_configured() else "未配置"
        return f"{self.name} ({status})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"AIProvider(name='{self.name}', id='{self.id}', "
            f"configured={self.is_configured()})"
        )


class ProviderError(Exception):
    """供应商相关错误"""

    pass


class ConfigurationError(ProviderError):
    """配置错误"""

    pass


class APIError(ProviderError):
    """API调用错误"""

    pass


class AuthenticationError(ProviderError):
    """认证错误"""

    pass


class RateLimitError(ProviderError):
    """速率限制错误"""

    pass
