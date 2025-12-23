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
    # 提供详细的错误信息以便诊断打包问题
    import sys
    error_details = f"原始错误: {type(e).__name__}: {e}"
    if hasattr(sys, '_MEIPASS'):
        # 在 PyInstaller 打包环境中
        error_details += f"\n[PyInstaller 环境] 基础路径: {sys._MEIPASS}"
    raise ImportError(
        f"请安装 Google Generative AI SDK: pip install google-genai\n{error_details}"
    ) from e

try:
    from colorama import Fore, Style  # type: ignore
except ImportError:
    # 如果 colorama 不可用，定义空的颜色和样式
    class Fore:  # type: ignore[no-redef]
        GREEN = ""
        RED = ""

    class Style:  # type: ignore[no-redef]
        BRIGHT = ""
        RESET_ALL = ""


from .base_provider import AIProvider


from .prompts import SEMANTIC_CHECK_PROMPT

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
        self.lock = threading.Lock()  # 用于多线程并发下的 Key 轮转同步

        # 初始化可用密钥和客户端
        self._initialize_api_keys()
        self._configure_client()

    def get_models(self) -> List[str]:
        """获取可用的模型列表"""
        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-thinking-exp-1219",  # 支持思维链的模型
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
            stream: 是否使用流式输出
            show_thinking: 是否显示思维链（仅思考模型有效）

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
            # 获取可用客户端
            if not self._get_available_client():
                if not self._handle_no_client(
                    attempt, max_retries, default_retry_delay
                ):
                    return "错误", "无可用 Gemini 模型"
                continue

            # 创建等待指示器
            stop_event = threading.Event()
            waiting_thread = threading.Thread(
                target=self.show_waiting_indicator, args=(stop_event,)
            )
            waiting_thread.daemon = True

            # 只有在非流式模式才显示等待指示器
            if not stream:
                waiting_thread.start()

            try:
                result, reason = self._call_gemini_api(
                    model_to_use,
                    prompt,
                    attempt,
                    max_retries,
                    stream,
                    show_thinking,
                    stop_event,
                )
                if result != "RETRY":
                    return result, reason

            except Exception as e:
                if not self._handle_general_error(
                    e, attempt, max_retries, default_retry_delay
                ):
                    return "错误", f"API 调用多次重试失败: {str(e)}"
                continue

            finally:
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

        return "错误", "API 调用多次重试失败"

    def _handle_no_client(
        self, attempt: int, max_retries: int, default_retry_delay: int
    ) -> bool:
        """
        处理无可用客户端的情况

        Returns:
            bool: True 表示需要重试，False 表示应该返回错误
        """
        logger.warning("无可用 Gemini 客户端，跳过 API 调用")
        if attempt < max_retries - 1:
            time.sleep(default_retry_delay)
            return True
        return False

    def _call_gemini_api(  # noqa: C901
        self,
        model_to_use: str,
        prompt: str,
        attempt: int,
        max_retries: int,
        stream: bool = False,
        show_thinking: bool = False,
        stop_event: Optional[threading.Event] = None,
    ) -> tuple[str, str]:
        """
        调用 Gemini API

        Returns:
            tuple[str, str]: (结果, 原因) 或 ("RETRY", "") 表示需要重试
        """
        import sys

        logger.info(
            f"正在调用 Gemini API 进行语义比对 (尝试 {attempt + 1}/{max_retries})..."
        )

        # 检查是否是思考模型
        is_thinking_model = "thinking" in model_to_use.lower()

        try:
            if stream:
                # 流式调用
                response = self.client.models.generate_content_stream(  # type: ignore
                    model=model_to_use,
                    contents=[prompt],
                    config=types.GenerateContentConfig(temperature=0),
                )

                # 停止等待指示器（如果有）
                if stop_event:
                    stop_event.set()

                full_response = ""
                thinking_content = ""
                first_char_printed = False

                logger.info("开始接收流式响应...")

                for chunk in response:
                    if chunk.text:
                        # 流式输出内容
                        if not first_char_printed:
                            # 如果是思考模型且需要显示思维链
                            if is_thinking_model and show_thinking:
                                # 尝试提取思维内容
                                if hasattr(chunk, "candidates") and chunk.candidates:
                                    candidate = chunk.candidates[0]
                                    if hasattr(candidate, "content") and hasattr(
                                        candidate.content, "parts"
                                    ):
                                        for part in candidate.content.parts:
                                            if (
                                                hasattr(part, "thought")
                                                and part.thought
                                            ):
                                                thinking_content += getattr(
                                                    part, "text", ""
                                                )

                            sys.stdout.write(f"\r{' ' * 50}\r")  # 清除等待指示器
                            sys.stdout.write("Gemini: ")
                            sys.stdout.flush()
                            first_char_printed = True

                        # 输出内容
                        print(chunk.text, end="", flush=True)
                        full_response += chunk.text

                # 换行
                if first_char_printed:
                    print()

                # 如果有思维内容且需要显示
                if thinking_content and show_thinking:
                    from rich.panel import Panel
                    from rich.markdown import Markdown
                    from rich import print as rprint

                    rprint(
                        Panel(
                            Markdown(thinking_content),
                            title="[bold blue]💭 思维过程[/bold blue]",
                            border_style="bright_cyan",
                            expand=False,
                        )
                    )

                response_text = full_response.strip()
            else:
                # 非流式调用
                response = self.client.models.generate_content(  # type: ignore
                    model=model_to_use,
                    contents=[prompt],
                    config=types.GenerateContentConfig(temperature=0),
                )

                if response is None or response.text is None:
                    logger.warning("Gemini API 返回空响应")
                    return "错误", "API 返回空响应"

                # 如果是思考模型，尝试提取思维内容
                if is_thinking_model and show_thinking:
                    try:
                        if hasattr(response, "candidates") and response.candidates:
                            candidate = response.candidates[0]
                            if hasattr(candidate, "content") and hasattr(
                                candidate.content, "parts"
                            ):
                                thinking_parts = []
                                for part in candidate.content.parts:
                                    if hasattr(part, "thought") and part.thought:
                                        thinking_parts.append(getattr(part, "text", ""))

                                if thinking_parts:
                                    thinking_content = "\n".join(thinking_parts)
                                    logger.info(f"\n💭 思维过程:\n{thinking_content}\n")
                    except Exception as e:
                        logger.debug(f"提取思维内容失败: {e}")

                response_text = response.text.strip()

            # 解析响应
            if response_text.startswith("```json") and response_text.endswith("```"):
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
                    colored_result = Style.BRIGHT + Fore.RED + result + Style.RESET_ALL

                logger.info(f"语义比对结果：{colored_result}")
                return result, reason

            except json.JSONDecodeError as e:
                logger.warning(f"解析 JSON 失败: {response_text}, 错误: {e}")
                return "错误", f"JSON 解析失败: {e}"

        except google.api_core.exceptions.ResourceExhausted as e:
            # 速率限制错误，需要重试
            error_msg = str(e)
            logger.warning(f"Gemini API 速率限制: {error_msg}")

            if attempt < max_retries - 1:
                retry_after = self._extract_retry_delay(error_msg) or 60
                logger.info("检测到 429 错误，立即强制轮转到下一个密钥")
                current_key = self.api_keys[self.current_key_index]
                self.key_cooldown_until[current_key] = time.time() + retry_after
                self._rotate_key(force_rotate=True)
                return "RETRY", ""

            return "错误", f"API 调用次数超限: {error_msg}"

    def _handle_general_error(
        self, e: Exception, attempt: int, max_retries: int, default_retry_delay: int
    ) -> bool:
        """
        处理一般错误

        Returns:
            bool: True 表示需要重试，False 表示应该返回错误
        """
        error_msg = str(e)

        if isinstance(e, json.JSONDecodeError):
            logger.warning(f"Gemini 返回的 JSON 格式不正确，错误：{error_msg}")
            return False  # JSON解析错误不重试
        elif isinstance(e, google.api_core.exceptions.ResourceExhausted):
            logger.warning(f"调用 Gemini API 时发生速率限制错误 (429)：{error_msg}")
            if attempt < max_retries - 1:
                retry_after = (
                    self._extract_retry_delay(error_msg) or default_retry_delay
                )
                logger.info("检测到 429 错误，立即强制轮转到下一个密钥")
                current_key = self.api_keys[self.current_key_index]
                self.key_cooldown_until[current_key] = time.time() + retry_after
                self._rotate_key(force_rotate=True)
                return True
            return False
        else:
            logger.error(f"调用 Gemini API 时发生错误：{error_msg}")
            if attempt < max_retries - 1:
                logger.warning(f"等待 {default_retry_delay} 秒后重试")
                time.sleep(default_retry_delay)
                self._rotate_key(force_rotate=True)
                return True
            return False

    def _get_prompt(
        self, question: str, ai_answer: str, source_document_content: str
    ) -> str:
        """生成语义比对提示词"""
        return SEMANTIC_CHECK_PROMPT.format(
            question=question,
            ai_answer=ai_answer,
            source_document=source_document_content,
        )

    def _initialize_api_keys(self):
        """初始化 API 密钥列表（启动时跳过验证）"""
        if not self.api_keys:
            logger.debug("Gemini API 密钥未配置")
            return

        current_time = time.time()
        for key in self.api_keys:
            self.key_last_used_time[key] = current_time
            self.key_cooldown_until[key] = 0.0

        logger.debug(f"已初始化 {len(self.api_keys)} 个 Gemini API 密钥")

    def _configure_client(self):
        """配置 Gemini 客户端"""
        if not self.api_keys:
            self.client = None
            return

        current_api_key = self.api_keys[self.current_key_index]
        try:
            self.client = genai.Client(api_key=current_api_key)
            logger.debug(
                f"Gemini API 客户端已配置，使用密钥索引: {self.current_key_index}"
            )
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
        """轮转到下一个 API 密钥（线程安全）"""
        if not self.api_keys:
            return

        # 用于记录需要在锁外执行的等待时间
        wait_time_outside_lock = 0.0

        with self.lock:  # 使用线程锁确保整个轮转过程的原子性
            # 如果未启用自动轮转且不是强制轮转，则不进行轮转
            if not self.auto_rotate and not force_rotate:
                return

            current_time = time.time()

            for _ in range(len(self.api_keys)):
                self.current_key_index = (self.current_key_index + 1) % len(
                    self.api_keys
                )
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
                        # 记录需要等待的时间，稍后在锁外执行
                        wait_time_outside_lock = 60 - time_since_last_use
                        logger.info(
                            f"密钥 {self.current_key_index} 需要等待: {wait_time_outside_lock:.1f}s"
                        )

                    logger.info(f"密钥 {self.current_key_index} 可用")
                    self.key_last_used_time[next_key] = current_time
                    self._configure_client()
                    break  # 退出循环，稍后在锁外等待
                else:
                    logger.info(
                        f"密钥 {self.current_key_index} 冷却中: 剩余 {cooldown_remaining:.1f}s"
                    )
            else:
                # 所有密钥都在冷却中
                max_cooldown = (
                    max(self.key_cooldown_until.values(), default=0) - current_time
                )
                if max_cooldown > 0:
                    wait_time_outside_lock = max_cooldown
                    logger.warning(
                        f"所有密钥不可用，等待最长冷却时间: {max_cooldown:.1f}s"
                    )

        # 在锁外执行等待，避免长时间持有锁阻塞其他线程
        if wait_time_outside_lock > 0:
            time.sleep(wait_time_outside_lock)
            # 等待后需要重新尝试轮转
            if (
                wait_time_outside_lock
                == max(self.key_cooldown_until.values(), default=0)
                - time.time()
                + wait_time_outside_lock
            ):
                self._rotate_key(force_rotate=True)
