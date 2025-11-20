"""
Gemini AI 供应商实现

实现 Gemini API 的语义相似度检查功能，继承自 AIProvider 抽象基类。
"""

import json
import logging
import re
import time
import threading
from typing import List, Dict, Optional, Any

try:
    import google.api_core.exceptions
    from google import genai
    from google.genai import types
except ImportError as e:
    raise ImportError(
        "请安装 Google Generative AI SDK: pip install google-genai"
    ) from e

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


class GeminiProvider(AIProvider):
    """Gemini AI 供应商"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Gemini 供应商

        Args:
            config: 配置字典，包含 api_keys, model 等信息
        """
        super().__init__(config)

        self.api_keys = config.get("api_keys", [])
        self.model_name = config.get("model", "gemini-2.5-flash")

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
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]

    def validate_api_key(self, api_key: str) -> bool:
        """
        验证 API 密钥有效性

        Args:
            api_key: API 密钥

        Returns:
            bool: 密钥是否有效
        """
        if not re.match(r"^[a-zA-Z0-9_-]{20,}$", api_key):
            logger.warning(f"API Key格式无效: {api_key[:5]}...")
            return False

        try:
            client = genai.Client(api_key=api_key)
            model_info = client.models.get(model="gemini-2.5-flash")  # type: ignore
            return model_info is not None
        except Exception:
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
            return "错误", "Gemini 供应商未正确配置"

        model_to_use = model or self.model_name
        prompt = self._get_prompt(question, ai_answer, source_document)

        max_retries = 5
        default_retry_delay = 60

        for attempt in range(max_retries):
            start_time = time.time()

            # 获取可用客户端
            if not self._get_available_client():
                logger.warning("无可用 Gemini 客户端，跳过 API 调用")
                if attempt < max_retries - 1:
                    time.sleep(default_retry_delay)
                    continue
                else:
                    return "错误", "无可用 Gemini 模型"

            # 创建等待指示器
            stop_event = threading.Event()
            waiting_thread = threading.Thread(
                target=self.show_waiting_indicator, args=(stop_event,)
            )
            waiting_thread.daemon = True
            waiting_thread.start()

            try:
                logger.info(
                    f"正在调用 Gemini API 进行语义比对 (尝试 {attempt + 1}/{max_retries})..."
                )

                response = self.client.models.generate_content(  # type: ignore
                    model=model_to_use,
                    contents=[prompt],
                    config=types.GenerateContentConfig(temperature=0),
                )

                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Gemini API 调用完成，耗时: {duration:.2f} 秒")

                if response is None or response.text is None:
                    logger.warning("Gemini API 返回空响应")
                    return "错误", "API 返回空响应"

                response_text = response.text.strip()
                if response_text.startswith("```json") and response_text.endswith(
                    "```"
                ):
                    response_text = response_text[7:-3].strip()

                try:
                    parsed_response = json.loads(response_text)
                    result = parsed_response.get("result", "无法判断").strip()
                    reason = parsed_response.get("reason", "无").strip()

                    colored_result = result
                    if result == "是":
                        colored_result = (
                            Style.BRIGHT + Fore.GREEN + result + Style.RESET_ALL
                        )
                    elif result == "否":
                        colored_result = (
                            Style.BRIGHT + Fore.RED + result + Style.RESET_ALL
                        )

                    logger.info(f"语义比对结果：{colored_result}")
                    return result, reason

                except json.JSONDecodeError as e:
                    logger.warning(f"解析 JSON 失败: {response_text}, 错误: {e}")
                    return "错误", f"JSON 解析失败: {e}"

            except json.JSONDecodeError as e:
                end_time = time.time()
                duration = end_time - start_time
                # 在这个异常块中，response_text 可能未定义，使用通用消息
                logger.warning(
                    f"Gemini 返回的 JSON 格式不正确，错误：{e}，耗时: {duration:.2f} 秒"
                )
                return "错误", f"JSON 解析错误: {e}"

            except google.api_core.exceptions.ResourceExhausted as e:
                end_time = time.time()
                duration = end_time - start_time
                error_msg = str(e)
                logger.warning(
                    f"调用 Gemini API 时发生速率限制错误 (429)：{error_msg}，耗时: {duration:.2f} 秒"
                )

                retry_after = (
                    self._extract_retry_delay(error_msg) or default_retry_delay
                )

                if attempt < max_retries - 1:
                    logger.info("检测到 429 错误，立即强制轮转到下一个密钥")
                    current_key = self.api_keys[self.current_key_index]
                    self.key_cooldown_until[current_key] = time.time() + retry_after
                    self._rotate_key(force_rotate=True)
                    continue
                else:
                    logger.error(f"语义比对多次重试后失败: {error_msg}")
                    return "错误", f"API 调用多次重试失败: {error_msg}"

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                error_msg = str(e)
                logger.error(
                    f"调用 Gemini API 时发生错误：{error_msg}，耗时: {duration:.2f} 秒"
                )

                if attempt < max_retries - 1:
                    logger.warning(f"等待 {default_retry_delay} 秒后重试")
                    time.sleep(default_retry_delay)
                    self._rotate_key(force_rotate=True)
                    continue
                else:
                    logger.error(f"语义比对多次重试后失败: {error_msg}")
                    return "错误", f"API 调用多次重试失败: {error_msg}"

            finally:
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

        return "错误", "API 调用多次重试失败"

    def _get_prompt(
        self, question: str, ai_answer: str, source_document_content: str
    ) -> str:
        """生成语义比对提示词"""
        return f"""
请判断以下AI客服回答与源知识库文档内容在语义上是否相符。
如果AI客服回答的内容能够从源知识库文档中推断出来，或者与源文档的核心信息一致，则认为相符。
如果AI客服回答的内容与源文档相悖，或者包含源文档中没有的信息且无法合理推断，则认为不相符。

请以JSON格式返回结果，包含两个字段：
- "result": "是" 或 "否"
- "reason": 详细的判断依据

问题点: {question}
AI客服回答: {ai_answer}
源知识库文档内容:
---
{source_document_content}
---

请直接回答JSON。
"""

    def _initialize_api_keys(self):
        """测试并初始化可用的 API 密钥列表"""
        logger.info("开始测试 Gemini API Key 的有效性...")
        valid_keys = []
        current_time = time.time()

        for key in self.api_keys:
            if self.validate_api_key(key):
                valid_keys.append(key)
                self.key_last_used_time[key] = current_time
                self.key_cooldown_until[key] = 0.0

        self.api_keys = valid_keys
        if not self.api_keys:
            logger.warning("所有提供的 Gemini API Key 均无效或未设置")
        else:
            logger.info(f"成功识别 {len(self.api_keys)} 个有效 Gemini API Key")

    def _configure_client(self):
        """配置 Gemini 客户端"""
        if not self.api_keys:
            self.client = None
            return

        current_api_key = self.api_keys[self.current_key_index]
        try:
            self.client = genai.Client(api_key=current_api_key)
            logger.info(f"Gemini API 已配置，使用密钥索引: {self.current_key_index}")
            self.key_last_used_time[current_api_key] = time.time()
        except Exception as e:
            logger.error(f"Gemini API 配置失败: {e}")
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
        retry_delay_match = re.search(r"'retryDelay': '(\d+)s'", error_msg)
        if retry_delay_match:
            try:
                return int(retry_delay_match.group(1)) + 5  # 增加5秒缓冲
            except ValueError:
                pass
        return None
