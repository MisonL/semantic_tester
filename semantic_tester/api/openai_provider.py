"""
OpenAI AI 供应商实现

实现 OpenAI API 的语义相似度检查功能，继承自 AIProvider 抽象基类。
支持 OpenAI 官方 API 和兼容接口。
"""

import json
import logging
import threading
import time
from typing import List, Dict, Optional, Any

try:
    import openai
    from openai import OpenAI
except ImportError as e:
    raise ImportError("请安装 OpenAI SDK: pip install openai") from e

try:
    from colorama import Fore, Style  # type: ignore
except ImportError:
    # 如果 colorama 不可用，定义空的颜色和样式
    class Fore:
        GREEN = ""
        RED = ""

    class Style:
        BRIGHT = ""
        RESET_ALL = ""


from .base_provider import AIProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI AI 供应商"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 OpenAI 供应商

        Args:
            config: 配置字典，包含 api_keys, model, base_url 等信息
        """
        super().__init__(config)

        self.api_keys = config.get("api_keys", [])
        self.model_name = config.get("model", "gpt-4o")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.has_config = config.get("has_config", len(self.api_keys) > 0)

        # 内部状态
        self.client = None
        self.current_key_index = 0
        self.key_last_used_time: Dict[str, float] = {}
        self.key_cooldown_until: Dict[str, float] = {}
        self.first_actual_call = True

        # 初始化可用密钥和客户端
        self._initialize_api_keys()
        self._configure_client()

    def get_models(self) -> List[str]:
        """获取可用的模型列表"""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-4",
            # 可以添加更多模型
        ]

    def validate_api_key(self, api_key: str) -> bool:
        """
        验证 API 密钥有效性

        Args:
            api_key: API 密钥

        Returns:
            bool: 密钥是否有效
        """
        if not api_key.startswith("sk-"):
            logger.warning(f"OpenAI API Key 格式无效: {api_key[:10]}...")
            return False

        try:
            test_client = OpenAI(api_key=api_key, base_url=self.base_url)
            # 尝试获取模型列表来验证密钥
            test_client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI API Key 验证失败: {e}")
            return False

    def is_configured(self) -> bool:
        """检查供应商是否已正确配置"""
        return len(self.api_keys) > 0 and self.client is not None

    def check_semantic_similarity(
        self,
        question: str,
        ai_answer: str,
        source_document: str,
        model: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        执行语义相似度检查

        Args:
            question: 问题内容
            ai_answer: AI回答内容
            source_document: 源文档内容
            model: 使用的模型（可选）

        Returns:
            tuple[str, str]: (结果, 原因)，结果为"是"/"否"/"错误"
        """
        if not self.is_configured():
            return "错误", "OpenAI 供应商未正确配置"

        model_to_use = model or self.model_name
        prompt = self._get_prompt(question, ai_answer, source_document)

        max_retries = 3
        default_retry_delay = 30

        for attempt in range(max_retries):

            # 创建等待指示器
            stop_event = threading.Event()
            waiting_thread = threading.Thread(
                target=self.show_waiting_indicator, args=(stop_event,)
            )
            waiting_thread.daemon = True
            waiting_thread.start()

            try:
                result, reason = self._call_openai_api(
                    model_to_use, prompt, attempt, max_retries, default_retry_delay
                )
                if result != "RETRY":
                    return result, reason

            except Exception as e:
                logger.error(f"调用 OpenAI API 时发生错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(default_retry_delay)
                    continue
                else:
                    return "错误", f"API 调用多次重试失败: {e}"

            finally:
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

        return "错误", "API 调用多次重试失败"

    def _call_openai_api(
        self,
        model_to_use: str,
        prompt: str,
        attempt: int,
        max_retries: int,
        default_retry_delay: int,
    ) -> tuple[str, str]:
        """
        调用 OpenAI API 并处理响应

        Returns:
            tuple[str, str]: (结果, 原因) 或 ("RETRY", "") 表示需要重试
        """
        logger.info(
            f"正在调用 OpenAI API 进行语义比对 (尝试 {attempt + 1}/{max_retries})..."
        )

        # 获取可用客户端
        client = self._get_available_client()
        if not client:
            logger.warning("无可用 OpenAI 客户端，跳过 API 调用")
            if attempt < max_retries - 1:
                return "RETRY", ""
            else:
                return "错误", "无可用 OpenAI 模型"

        try:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "你是一个专业的语义分析助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=1000,
            )

            if not response.choices or not response.choices[0].message.content:
                logger.warning("OpenAI API 返回空响应")
                return "错误", "API 返回空响应"

            response_text = response.choices[0].message.content.strip()
            return self._parse_response(response_text)

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI API 认证失败: {e}")
            return "错误", f"API 认证失败: {e}"

        except openai.RateLimitError as e:
            logger.warning(f"OpenAI API 速率限制: {e}")
            if attempt < max_retries - 1:
                retry_after = (
                    self._extract_retry_delay(str(e)) or default_retry_delay
                )
                logger.info(f"等待 {retry_after} 秒后重试")
                time.sleep(retry_after)
                return "RETRY", ""
            else:
                return "错误", "API 调用次数超限"

        except openai.APIError as e:
            logger.error(f"OpenAI API 错误: {e}")
            if attempt < max_retries - 1:
                time.sleep(default_retry_delay)
                return "RETRY", ""
            else:
                return "错误", f"API 调用失败: {e}"

    def _parse_response(self, response_text: str) -> tuple[str, str]:
        """
        解析 API 响应

        Args:
            response_text: API 返回的响应文本

        Returns:
            tuple[str, str]: (结果, 原因)
        """
        # 尝试解析 JSON 响应
        try:
            # 如果响应包含代码块，提取其中的 JSON
            if response_text.startswith("```json") and response_text.endswith(
                "```"
            ):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```") and response_text.endswith(
                "```"
            ):
                response_text = response_text[3:-3].strip()

            parsed_response = json.loads(response_text)
            result = parsed_response.get("result", "无法判断").strip()
            reason = parsed_response.get("reason", "无").strip()

            self._log_result(result)
            return result, reason

        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试从文本中提取结果
            if "是" in response_text and "否" not in response_text:
                result = "是"
                reason = response_text
            elif "否" in response_text and "是" not in response_text:
                result = "否"
                reason = response_text
            else:
                result = "无法判断"
                reason = f"无法解析响应: {response_text[:200]}..."

            self._log_result(result, text_mode=True)
            return result, reason

    def _log_result(self, result: str, text_mode: bool = False) -> None:
        """
        记录语义比对结果

        Args:
            result: 语义比对结果
            text_mode: 是否为文本解析模式
        """
        colored_result = result
        if result == "是":
            colored_result = Style.BRIGHT + Fore.GREEN + result + Style.RESET_ALL
        elif result == "否":
            colored_result = Style.BRIGHT + Fore.RED + result + Style.RESET_ALL

        mode_text = "（文本解析）" if text_mode else ""
        logger.info(f"语义比对结果{mode_text}：{colored_result}")

    def _get_prompt(
        self, question: str, ai_answer: str, source_document_content: str
    ) -> str:
        """生成语义比对提示词"""
        return f"""请判断以下AI客服回答与源知识库文档内容在语义上是否相符。

判断标准：
- 如果AI客服回答的内容能够从源知识库文档中推断出来，或者与源文档的核心信息一致，则认为"相符"
- 如果AI客服回答的内容与源文档相悖，或者包含源文档中没有的信息且无法合理推断，则认为"不相符"

请严格按照以下JSON格式返回结果：
{{
    "result": "是" 或 "否",
    "reason": "详细的判断依据，说明为什么是相符或不相符"
}}

问题点：{question}

AI客服回答：{ai_answer}

源知识库文档内容：
---
{source_document_content}
---

请直接返回JSON格式结果，不要包含其他内容。"""

    def _initialize_api_keys(self):
        """测试并初始化可用的 API 密钥列表"""
        logger.info("开始测试 OpenAI API Key 的有效性...")
        valid_keys = []
        current_time = time.time()

        for key in self.api_keys:
            if self.validate_api_key(key):
                valid_keys.append(key)
                self.key_last_used_time[key] = current_time
                self.key_cooldown_until[key] = 0.0

        self.api_keys = valid_keys
        if not self.api_keys:
            logger.warning("所有提供的 OpenAI API Key 均无效或未设置")
        else:
            logger.info(f"成功识别 {len(self.api_keys)} 个有效 OpenAI API Key")

    def _configure_client(self):
        """配置 OpenAI 客户端"""
        if not self.api_keys:
            self.client = None
            return

        current_api_key = self.api_keys[self.current_key_index]
        try:
            self.client = OpenAI(
                api_key=current_api_key, base_url=self.base_url, timeout=60
            )
            logger.info(f"OpenAI API 已配置，使用密钥索引: {self.current_key_index}")
            self.key_last_used_time[current_api_key] = time.time()
        except Exception as e:
            logger.error(f"OpenAI API 配置失败: {e}")
            self.client = None
            if self.api_keys:
                self._rotate_key(force_rotate=True)

    def _get_available_client(self):
        """获取可用的客户端"""
        if not self.api_keys:
            return None

        self._rotate_key()
        return self.client

    def _rotate_key(self, force_rotate: bool = False):
        """轮转到下一个 API 密钥"""
        if not self.api_keys:
            return

        current_time = time.time()

        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            next_key = self.api_keys[self.current_key_index]

            cooldown_until = self.key_cooldown_until.get(next_key, 0.0)
            cooldown_remaining = max(0.0, cooldown_until - current_time)
            time_since_last_use = current_time - self.key_last_used_time.get(
                next_key, 0.0
            )

            if force_rotate:
                logger.info(f"强制轮转: 新密钥索引: {self.current_key_index}")
                self.key_last_used_time[next_key] = current_time
                self._configure_client()
                return

            if cooldown_remaining <= 0:
                if self.first_actual_call:
                    logger.info(f"首次实际调用，密钥 {self.current_key_index} 可用")
                    self.first_actual_call = False
                elif time_since_last_use < 60:
                    wait_time = 60 - time_since_last_use
                    logger.info(
                        f"密钥 {self.current_key_index} 需要等待: {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)

                logger.info(f"密钥 {self.current_key_index} 可用")
                self.key_last_used_time[next_key] = current_time
                self._configure_client()
                return
            else:
                logger.info(
                    f"密钥 {self.current_key_index} 冷却中: 剩余 {cooldown_remaining:.1f}s"
                )

        max_cooldown = max(self.key_cooldown_until.values(), default=0) - current_time
        if max_cooldown > 0:
            logger.warning(f"所有密钥不可用，等待最长冷却时间: {max_cooldown:.1f}s")
            time.sleep(max_cooldown)
            self._rotate_key(force_rotate=True)

    def _extract_retry_delay(self, error_msg: str) -> Optional[int]:
        """从错误消息中提取重试延迟时间"""
        import re

        # 尝试匹配 "Please try again in Xs" 格式
        retry_match = re.search(r"try again in (\d+)s", error_msg.lower())
        if retry_match:
            try:
                return int(retry_match.group(1))
            except ValueError:
                pass
        return None
