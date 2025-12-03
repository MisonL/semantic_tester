"""
环境变量管理

处理环境变量的加载和验证，支持 .env.config 文件配置。
环境变量优先级高于 .env.config 文件配置。
"""

import logging
import os
import re
from typing import List

from dotenv import load_dotenv

from .env_loader import get_env_loader

logger = logging.getLogger(__name__)


class EnvManager:
    """环境变量管理器 - 支持环境变量和 .env.config 文件"""

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
        优先从环境变量获取，其次从 .env.config 文件获取

        Returns:
            List[str]: API 密钥列表
        """
        # 优先从环境变量获取（支持 GEMINI_API_KEY / GEMINI_API_KEYS 两种命名）
        gemini_api_keys_str = os.getenv("GEMINI_API_KEY") or os.getenv(
            "GEMINI_API_KEYS"
        )

        # 如果环境变量不存在，尝试从 .env.config 文件获取
        if not gemini_api_keys_str:
            gemini_api_keys_str = self.env_loader.get_str(
                "GEMINI_API_KEY"
            ) or self.env_loader.get_str("GEMINI_API_KEYS")
            if gemini_api_keys_str:
                logger.info("从 .env.config 文件加载 Gemini API 密钥")

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

        if not valid_keys:
            # 具体统计在 _log_template_summary 中统一处理
            return []

        logger.info(f"成功加载 {len(valid_keys)} 个有效的 Gemini API 密钥")
        return valid_keys

    def get_gemini_api_keys(self) -> List[str]:
        """获取过滤后的 Gemini API 密钥

        支持以下环境变量/配置键（按优先级排列）:
        1. 环境变量 `GEMINI_API_KEY`
        2. 环境变量 `GEMINI_API_KEYS`（向后兼容别名）
        3. `.env.config` 中的 `GEMINI_API_KEY` 或 `GEMINI_API_KEYS`
        """
        return self._load_gemini_keys()

    def get_gemini_model(self) -> str:
        """
        获取 Gemini 模型名称
        优先从环境变量获取，其次从 .env.config 文件获取

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
                "2. 在 .env.config 文件中配置：GEMINI_API_KEY=您的API密钥1,您的API密钥2"
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
            all_keys = [
                key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()
            ]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 模板值过滤情况在 _log_template_summary 中统一处理

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
            all_keys = [
                key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()
            ]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 模板值过滤情况在 _log_template_summary 中统一处理

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
            all_keys = [
                key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()
            ]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 模板值过滤情况在 _log_template_summary 中统一处理

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
            all_keys = [
                key.strip() for key in re.split(r"[\s,]+", api_keys_str) if key.strip()
            ]

        # 过滤模板值
        valid_keys = [key for key in all_keys if not self._is_template_value(key)]

        # 模板值过滤情况在 _log_template_summary 中统一处理

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

    def get_use_full_doc_match(self) -> bool:
        """获取是否使用全量文档匹配"""
        # 优先从环境变量获取
        use_full_doc_match = os.getenv("USE_FULL_DOC_MATCH")
        if use_full_doc_match is not None:
            return use_full_doc_match.lower() in ("true", "1", "yes", "on")

        # 从 .env.config 文件获取
        return self.env_loader.get_bool("USE_FULL_DOC_MATCH", False)

    def get_enable_thinking(self) -> bool:
        """获取是否默认启用思维链/推理过程显示.

        优先从环境变量 `ENABLE_THINKING` 读取，其次从 `.env.config` 中读取，默认开启。
        """
        value = os.getenv("ENABLE_THINKING")
        if value is not None:
            return value.lower() in ("true", "1", "yes", "on")

        return self.env_loader.get_bool("ENABLE_THINKING", True)

    def print_env_status(self):
        """打印环境变量状态"""
        print("\n=== 环境配置状态 ===")

        # 显示配置文件状态
        self.env_loader.print_config_status()

        print("\n--- 环境变量优先级配置 ---")
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
        print(
            f"Anthropic API 密钥: {'已设置' if anthropic_config['has_config'] else '未设置'}"
        )

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

    def _analyze_provider_keys(self, env_var: str, provider_name: str) -> tuple:
        """分析供应商密钥配置"""
        key_value = os.getenv(env_var) or self.env_loader.get_str(env_var, "")
        if not key_value:
            return 0, False

        keys = [key.strip() for key in re.split(r"[\s,]+", key_value) if key.strip()]
        template_count = sum(1 for key in keys if self._is_template_value(key))
        is_configured = any(not self._is_template_value(key) for key in keys)

        return template_count, is_configured

    def _log_template_summary(self):
        """记录所有供应商的模板值统计摘要"""
        template_counts = {}
        configured_suppliers = []

        # 供应商配置映射
        providers = [
            ("GEMINI_API_KEY", "gemini", "Gemini"),
            ("OPENAI_API_KEY", "openai", "OpenAI"),
            ("ANTHROPIC_API_KEY", "anthropic", "Anthropic"),
            ("DIFY_API_KEY", "dify", "Dify"),
            ("IFLOW_API_KEY", "iflow", "iFlow"),
        ]

        # 统计各供应商配置
        for env_var, key, name in providers:
            template_count, is_configured = self._analyze_provider_keys(env_var, key)
            if template_count > 0:
                template_counts[key] = template_count
            elif is_configured:
                configured_suppliers.append(name)

        # 计算总数
        total_template_keys = sum(template_counts.values())
        total_suppliers = len(template_counts) if template_counts else 0

        # 记录摘要
        if configured_suppliers:
            logger.info(f"✅ 已配置供应商: {', '.join(configured_suppliers)}")

        if total_template_keys > 0:
            # 改为 debug 级别，避免启动时刷屏干扰美观
            logger.debug(
                f"待配置: {total_template_keys} 个模板密钥（{total_suppliers} 个供应商）"
            )
            for supplier, count in template_counts.items():
                if count > 0:
                    supplier_name = {
                        "gemini": "Gemini",
                        "openai": "OpenAI",
                        "anthropic": "Anthropic",
                        "dify": "Dify",
                        "iflow": "iFlow",
                    }.get(supplier, supplier)
                    logger.debug(f"    - {supplier_name}: {count} 个模板值")
        elif not configured_suppliers:
            # 如果完全没有配置，还是需要提示一下，但用 info 级别
            logger.info("尚未配置任何AI供应商,请后续在菜单中配置")

    def get_semantic_check_prompt(self) -> str:
        """
        获取语义检查提示词
        优先从环境变量获取，其次从 .env.config 文件获取

        Returns:
            str: 语义检查提示词
        """
        # 默认提示词
        default_prompt = """请判断以下AI客服回答与源知识库文档内容在语义上是否相符。

判断标准：
1. 如果AI客服回答的内容能够从源知识库文档中推断出来，或者与源文档的核心信息一致，则认为"相符"。
2. 如果AI客服回答的内容与源文档相悖，或者包含源文档中没有的信息且无法合理推断，则认为"不相符"。
3. 如果无法获取源文档内容或遇到技术性错误，则标记为"错误"。
4. 如果信息不足以做出明确判断，则标记为"不确定"。

**重要：result 字段必须严格使用以下四种值之一，不得使用其他任何值：**
- "是" - 表示AI回答与源文档语义相符
- "否" - 表示AI回答与源文档语义不符
- "错误" - 表示遇到技术性错误（如获取文档失败）
- "不确定" - 表示信息不足，无法明确判断

请严格按照以下JSON格式返回结果：
{{
    "result": "是" 或 "否" 或 "错误" 或 "不确定",
    "reason": "详细的判断依据，说明为什么是相符或不相符，请引用源文档内容作为佐证"
}}

问题点：
{question}

AI客服回答：
{ai_answer}

源知识库文档内容：
---
{source_document}
---

请直接返回JSON格式结果，不要包含其他内容。记住：result 字段只能是这四个值之一："是"、"否"、"错误"、"不确定"。"""

        # 优先从环境变量获取
        prompt = os.getenv("SEMANTIC_CHECK_PROMPT")
        if not prompt:
            # 从 .env.config 文件获取
            prompt = self.env_loader.get_str("SEMANTIC_CHECK_PROMPT")

        return prompt or default_prompt
