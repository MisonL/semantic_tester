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

    def load_environment(self):
        """加载环境变量"""
        load_dotenv()  # 优先加载环境变量

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

    def get_channels_config(self) -> List[dict]:
        """
        获取多渠道配置 (参考七鱼项目)
        支持 AI_CHANNEL_1_NAME, AI_CHANNEL_1_API_KEY, AI_CHANNEL_1_BASE_URL, AI_CHANNEL_1_MODEL
        """
        channels = []
        i = 1
        while i <= 20:  # 限制最多20个渠道
            name_key = f"AI_CHANNEL_{i}_NAME"
            name = os.getenv(name_key) or self.env_loader.get_str(name_key)
            if not name:
                break

            api_key_key = f"AI_CHANNEL_{i}_API_KEY"
            api_key = os.getenv(api_key_key) or self.env_loader.get_str(api_key_key)

            base_url_key = f"AI_CHANNEL_{i}_BASE_URL"
            base_url = os.getenv(base_url_key) or self.env_loader.get_str(base_url_key)

            model_key = f"AI_CHANNEL_{i}_MODEL"
            model = os.getenv(model_key) or self.env_loader.get_str(model_key)

            app_id_key = f"AI_CHANNEL_{i}_APP_ID"
            app_id = os.getenv(app_id_key) or self.env_loader.get_str(app_id_key)

            # 并发数配置 (支持环境变量覆盖)
            concurrency_key = f"AI_CHANNEL_{i}_CONCURRENCY"
            concurrency_str = os.getenv(concurrency_key) or self.env_loader.get_str(
                concurrency_key
            )

            # 处理行内注释 (例如: 1 # 注释)
            if concurrency_str and "#" in str(concurrency_str):
                concurrency_str = str(concurrency_str).split("#")[0].strip()

            try:
                concurrency = int(concurrency_str) if concurrency_str else 1
            except (ValueError, TypeError):
                # 记录警告但继续执行，使用默认值 1
                logger.warning(
                    f"无效的并发配置 {concurrency_key}: {concurrency_str}, 默认为 1"
                )
                concurrency = 1

            channels.append(
                {
                    "id": f"channel_{i}",
                    "display_name": f"渠道 {i}: {name}",
                    "type": name.lower(),  # 对应供应商类型 (gemini, openai, dify, iflow, anthropic)
                    "api_keys": [api_key] if api_key else [],
                    "base_url": base_url,
                    "model": model,
                    "app_id": app_id,
                    "concurrency": concurrency,
                    "has_config": api_key and not self._is_template_value(api_key),
                }
            )
            i += 1

        # 尝试加载 ai_config.json 来覆盖/补充并发配置
        config_path = os.path.join(os.getcwd(), "ai_config.json")
        if os.path.exists(config_path):
            try:
                import json

                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    if isinstance(config_data, list):
                        for channel_cfg in config_data:
                            c_id_num = channel_cfg.get("channel_id")
                            if c_id_num:
                                target_id = f"channel_{c_id_num}"
                                # 如果渠道已通过环境变量定义，则更新并发数
                                for c in channels:
                                    if c["id"] == target_id:
                                        c["concurrency"] = channel_cfg.get(
                                            "concurrency", c["concurrency"]
                                        )
                                        break

                                # 如果环境变量中没有该渠道，但 JSON 中有，可以考虑是否要通过 JSON 完全定义
                                # 暂时只做覆盖
            except Exception as e:
                logger.warning(f"加载 ai_config.json 失败: {e}")

        return channels

    def get_batch_config(self) -> dict:
        """获取批量处理配置"""
        return {
            "save_interval": self.env_loader.get_int("BATCH_SAVE_INTERVAL", 10),
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

        # 显示多渠道配置概览
        channels = self.get_channels_config()
        configured_channels = [c for c in channels if c["has_config"]]
        print(f"已配置 AI 渠道: {len(configured_channels)} / {len(channels)}")
        for c in configured_channels:
            print(f"  - {c['display_name']} (并发: {c['concurrency']})")

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
