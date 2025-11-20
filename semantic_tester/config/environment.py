"""
环境变量管理

处理环境变量的加载和验证，支持 .env 文件配置。
环境变量优先级高于 .env 文件配置。
"""

import logging
import os
import re
from typing import List

from dotenv import load_dotenv

from .env_loader import get_env_loader

logger = logging.getLogger(__name__)


class EnvManager:
    """环境变量管理器 - 支持环境变量和 .env 文件"""

    def __init__(self):
        """初始化环境变量管理器"""
        self.env_loader = get_env_loader()
        self.load_environment()
        self.gemini_api_keys = self.get_gemini_api_keys()
        self._log_template_summary()

    def load_environment(self):
        """加载环境变量"""
        load_dotenv()  # 优先加载环境变量

    def _load_gemini_keys(self) -> List[str]:
        """
        加载 Gemini API 密钥
        优先从环境变量获取，其次从 .env 文件获取

        Returns:
            List[str]: API 密钥列表
        """
        # 优先从环境变量获取
        gemini_api_keys_str = os.getenv("GEMINI_API_KEY")

        # 如果环境变量不存在，尝试从 .env 文件获取
        if not gemini_api_keys_str:
            gemini_api_keys_str = self.env_loader.get_str("GEMINI_API_KEY")
            if gemini_api_keys_str:
                logger.info("从 .env 文件加载 Gemini API 密钥")

        if not gemini_api_keys_str:
            logger.warning("未配置 GEMINI_API_KEY")
            return []

        # 使用正则表达式分割密钥，支持逗号和空格分隔
        all_keys = [
            key.strip()
            for key in re.split(r"[\s,]+", gemini_api_keys_str)
            if key.strip()
        ]

        if not all_keys:
            logger.warning("GEMINI_API_KEY 配置格式无效")
            return []

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        if len(valid_keys) < len(all_keys):
            template_count = len(all_keys) - len(valid_keys)
            logger.warning(f"已过滤 {template_count} 个模板API密钥")

        if not valid_keys:
            logger.warning("所有 Gemini API 密钥都是模板值，请配置真实的API密钥")
            return []

        logger.info(f"成功加载 {len(valid_keys)} 个有效的 Gemini API 密钥")
        return valid_keys

    def get_gemini_api_keys(self) -> List[str]:
        """
        获取过滤后的 Gemini API 密钥
        这个方法会过滤掉模板值

        Returns:
            List[str]: 有效的API密钥列表
        """
        return self._load_gemini_keys()

    def get_gemini_model(self) -> str:
        """
        获取 Gemini 模型名称
        优先从环境变量获取，其次从 .env 文件获取

        Returns:
            str: 模型名称
        """
        # 优先从环境变量获取
        model = os.getenv("GEMINI_MODEL")
        if not model:
            # 从 .env 文件获取
            model = self.env_loader.get_str("GEMINI_MODEL")
        return model or "gemini-2.0-flash-exp"

    def _is_template_value(self, value: str) -> bool:
        """
        检查值是否是模板值

        Args:
            value: 要检查的值

        Returns:
            bool: 是否是模板值
        """
        if not value:
            return True

        template_indicators = [
            "your-api-key",
            "your-gemini-api-key",
            "your-openai-api-key",
            "your-dify-api-key",
            "your-iflow-api-key",
            "sk-ant-your-anthropic-api-key",
            "sk-your-openai-api-key",
            "sk-your-iflow-api-key",
            "app-your-dify-api-key",
            "your-key-here",
            "replace-with-your-key",
            "your-actual-key",
            "your-real-key",
        ]

        value_lower = value.lower()
        return any(indicator in value_lower for indicator in template_indicators)

    def validate_required_env(self) -> bool:
        """
        验证必需的环境变量
        改为警告而非致命错误，支持无密钥启动

        Returns:
            bool: 是否有可用的API密钥
        """
        if not self.gemini_api_keys:
            logger.warning("未配置 Gemini API 密钥")
            logger.info("您可以通过以下方式配置：")
            logger.info(
                "1. 设置环境变量：export GEMINI_API_KEY='您的API密钥1,您的API密钥2'"
            )
            logger.info(
                "2. 在 .env 文件中配置：GEMINI_API_KEY=您的API密钥1,您的API密钥2"
            )
            logger.info("3. 程序运行时交互式输入")
            return False

        return True

    def get_ai_providers(self):
        """获取AI供应商配置"""
        return self.env_loader.get_ai_providers()

    def get_openai_config(self) -> dict:
        """获取 OpenAI 配置（支持多密钥）"""
        # 加载API密钥字符串（支持逗号分隔的多个密钥）
        api_keys_str = os.getenv("OPENAI_API_KEY") or self.env_loader.get_str(
            "OPENAI_API_KEY", ""
        )

        # 分割多个密钥
        all_keys = []
        if api_keys_str:
            all_keys = [key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 记录模板值过滤情况
        if len(valid_keys) < len(all_keys):
            template_count = len(all_keys) - len(valid_keys)
            logger.warning(f"OpenAI: 已过滤 {template_count} 个模板API密钥")

        model = os.getenv("OPENAI_MODEL") or self.env_loader.get_str(
            "OPENAI_MODEL", "gpt-4o"
        )
        base_url = os.getenv("OPENAI_BASE_URL") or self.env_loader.get_str(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )

        has_config = len(valid_keys) > 0

        return {
            "api_keys": valid_keys,  # 改为api_keys（复数）
            "model": model,
            "base_url": base_url,
            "has_config": has_config,
        }

    def get_dify_config(self) -> dict:
        """获取 Dify 配置（支持多密钥）"""
        # 加载API密钥字符串（支持逗号分隔的多个密钥）
        api_keys_str = os.getenv("DIFY_API_KEY") or self.env_loader.get_str(
            "DIFY_API_KEY", ""
        )

        # 分割多个密钥
        all_keys = []
        if api_keys_str:
            all_keys = [key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 记录模板值过滤情况
        if len(valid_keys) < len(all_keys):
            template_count = len(all_keys) - len(valid_keys)
            logger.warning(f"Dify: 已过滤 {template_count} 个模板API密钥")

        base_url = os.getenv("DIFY_BASE_URL") or self.env_loader.get_str(
            "DIFY_BASE_URL", "https://api.dify.ai/v1"
        )
        app_id = os.getenv("DIFY_APP_ID") or self.env_loader.get_str("DIFY_APP_ID", "")

        has_config = len(valid_keys) > 0

        return {
            "api_keys": valid_keys,  # 改为api_keys（复数）
            "base_url": base_url,
            "app_id": app_id,
            "has_config": has_config,
        }

    def get_anthropic_config(self) -> dict:
        """获取 Anthropic 配置（支持多密钥）"""
        # 加载API密钥字符串（支持逗号分隔的多个密钥）
        api_keys_str = os.getenv("ANTHROPIC_API_KEY") or self.env_loader.get_str(
            "ANTHROPIC_API_KEY", ""
        )

        # 分割多个密钥
        all_keys = []
        if api_keys_str:
            all_keys = [key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 记录模板值过滤情况
        if len(valid_keys) < len(all_keys):
            template_count = len(all_keys) - len(valid_keys)
            logger.warning(f"Anthropic: 已过滤 {template_count} 个模板API密钥")

        model = os.getenv("ANTHROPIC_MODEL") or self.env_loader.get_str(
            "ANTHROPIC_MODEL", "claude-sonnet-4-20250514"
        )
        base_url = os.getenv("ANTHROPIC_BASE_URL") or self.env_loader.get_str(
            "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
        )

        has_config = len(valid_keys) > 0

        return {
            "api_keys": valid_keys,  # 改为api_keys（复数）
            "model": model,
            "base_url": base_url,
            "has_config": has_config,
        }

    def get_iflow_config(self) -> dict:
        """获取 iFlow 配置（支持多密钥）"""
        # 加载API密钥字符串（支持逗号分隔的多个密钥）
        api_keys_str = os.getenv("IFLOW_API_KEY") or self.env_loader.get_str(
            "IFLOW_API_KEY", ""
        )

        # 分割多个密钥
        all_keys = []
        if api_keys_str:
            all_keys = [key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 记录模板值过滤情况
        if len(valid_keys) < len(all_keys):
            template_count = len(all_keys) - len(valid_keys)
            logger.warning(f"iFlow: 已过滤 {template_count} 个模板API密钥")

        model = os.getenv("IFLOW_MODEL") or self.env_loader.get_str(
            "IFLOW_MODEL", "qwen3-max"
        )
        base_url = os.getenv("IFLOW_BASE_URL") or self.env_loader.get_str(
            "IFLOW_BASE_URL", "https://apis.iflow.cn/v1"
        )

        has_config = len(valid_keys) > 0

        return {
            "api_keys": valid_keys,  # 改为api_keys（复数）
            "model": model,
            "base_url": base_url,
            "has_config": has_config,
        }

    def get_batch_config(self) -> dict:
        """获取批量处理配置"""
        return {
            "request_interval": self.env_loader.get_float(
                "BATCH_REQUEST_INTERVAL", 1.0
            ),
            "waiting_indicators": self.env_loader.get_list(
                "WAITING_INDICATORS", ["⣾", "⣽", "⣻", "⢿"]
            ),
            "waiting_text": self.env_loader.get_str("WAITING_TEXT", "正在处理"),
            "waiting_delay": self.env_loader.get_float("WAITING_DELAY", 0.1),
        }

    def get_api_config(self) -> dict:
        """获取API调用配置"""
        return {
            "timeout": self.env_loader.get_int("API_TIMEOUT", 60),
            "retry_count": self.env_loader.get_int("API_RETRY_COUNT", 5),
            "retry_delay": self.env_loader.get_int("API_RETRY_DELAY", 60),
        }

    def print_env_status(self):
        """打印环境变量状态"""
        print(f"\n=== 环境配置状态 ===")

        # 显示配置文件状态
        self.env_loader.print_config_status()

        print(f"\n--- 环境变量优先级配置 ---")
        print(
            f"Gemini API 密钥: {'已设置' if self.gemini_api_keys else '未设置'} ({len(self.gemini_api_keys)} 个)"
        )
        print(f"Gemini 模型: {self.get_gemini_model()}")

        # 显示其他供应商配置
        openai_config = self.get_openai_config()
        print(
            f"OpenAI API 密钥: {'已设置' if openai_config['has_config'] else '未设置'}"
        )
        if openai_config["has_config"]:
            print(f"OpenAI 模型: {openai_config['model']}")

        dify_config = self.get_dify_config()
        print(f"Dify API 密钥: {'已设置' if dify_config['has_config'] else '未设置'}")

        anthropic_config = self.get_anthropic_config()
        print(f"Anthropic API 密钥: {'已设置' if anthropic_config['has_config'] else '未设置'}")

        iflow_config = self.get_iflow_config()
        print(f"iFlow API 密钥: {'已设置' if iflow_config['has_config'] else '未设置'}")

        # 显示AI供应商配置
        ai_providers = self.get_ai_providers()
        print(f"已配置AI供应商: {', '.join([p['name'] for p in ai_providers])}")

    def get_api_keys_preview(self) -> str:
        """
        获取 API 密钥预览（隐藏敏感信息）

        Returns:
            str: API 密钥预览
        """
        if not self.gemini_api_keys:
            return "无"

        preview_list = []
        for key in self.gemini_api_keys:
            if len(key) >= 10:
                preview_list.append(f"{key[:5]}...{key[-4:]}")
            else:
                preview_list.append(f"{key[:3]}...")

        return ", ".join(preview_list)

    def _log_template_summary(self):
        """记录所有供应商的模板值统计摘要"""
        # 统计Gemini模板值
        gemini_template_count = 0
        if hasattr(self, 'gemini_api_keys'):
            all_gemini_keys = []
            gemini_api_keys_str = os.getenv("GEMINI_API_KEY") or self.env_loader.get_str("GEMINI_API_KEY", "")
            if gemini_api_keys_str:
                all_gemini_keys = [key.strip() for key in re.split(r"[\s,]+", gemini_api_keys_str) if key.strip()]
            valid_gemini_keys = [key for key in all_gemini_keys if not self._is_template_value(key)]
            gemini_template_count = len(all_gemini_keys) - len(valid_gemini_keys)

        # 统计其他供应商模板值
        template_counts = {"gemini": gemini_template_count}

        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY") or self.env_loader.get_str("OPENAI_API_KEY", "")
        if openai_key and self._is_template_value(openai_key):
            template_counts["openai"] = 1

        # Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY") or self.env_loader.get_str("ANTHROPIC_API_KEY", "")
        if anthropic_key and self._is_template_value(anthropic_key):
            template_counts["anthropic"] = 1

        # Dify
        dify_key = os.getenv("DIFY_API_KEY") or self.env_loader.get_str("DIFY_API_KEY", "")
        if dify_key and self._is_template_value(dify_key):
            template_counts["dify"] = 1

        # iFlow
        iflow_key = os.getenv("IFLOW_API_KEY") or self.env_loader.get_str("IFLOW_API_KEY", "")
        if iflow_key and self._is_template_value(iflow_key):
            template_counts["iflow"] = 1

        # 计算总数
        total_template_keys = sum(template_counts.values())
        total_suppliers = len(template_counts)

        # 记录摘要
        if total_template_keys > 0:
            logger.warning(f"检测到 {total_template_keys} 个模板API密钥（共 {total_suppliers} 个供应商）")

            # 详细列出每个供应商的情况
            for supplier, count in template_counts.items():
                if count > 0:
                    supplier_name = {
                        "gemini": "Gemini",
                        "openai": "OpenAI",
                        "anthropic": "Anthropic",
                        "dify": "Dify",
                        "iflow": "iFlow"
                    }.get(supplier, supplier)
                    logger.warning(f"  - {supplier_name}: {count} 个模板值")

            logger.info("提示: 配置真实的API密钥可提高程序可用性")
        else:
            logger.info("所有API密钥配置正常（未发现模板值）")
