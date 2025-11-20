"""
Gemini API 处理模块

包含 GeminiAPIHandler 类和语义比对函数，用于处理与 Google Gemini API 的交互。
"""

import json
import logging
import re
import time
import threading
from typing import List, Dict

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


logger = logging.getLogger(__name__)


def show_waiting_indicator(stop_event, service_name="服务"):
    """显示等待指示器"""
    indicators = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not stop_event.is_set():
        print(
            f"\r{service_name} 处理中... {indicators[i % len(indicators)]}",
            end="",
            flush=True,
        )
        time.sleep(0.1)
        i += 1
    print("\r" + " " * 50 + "\r", end="", flush=True)  # 清除等待指示器


class GeminiAPIHandler:
    """Gemini API 处理器，负责 API 密钥管理和请求处理"""

    def __init__(self, api_keys: List[str], model_name: str, prompt_template: str = ""):
        """
        初始化 Gemini API 处理器

        Args:
            api_keys: API 密钥列表
            model_name: 使用的模型名称
            prompt_template: 提示词模板（semantic_tester 中为空）
        """
        self.all_api_keys = api_keys  # 存储所有提供的API Key
        self.api_keys: List[str] = []  # 存储经过有效性测试后的可用API Key
        self.current_key_index = 0
        self.model_name = model_name
        self.prompt_template = prompt_template
        self.client = None  # 使用client替代model
        # 存储每个API Key上次使用的时间戳，用于轮转判断
        self.key_last_used_time: Dict[str, float] = {}
        # 存储每个API Key的冷却结束时间（429错误后）
        self.key_cooldown_until: Dict[str, float] = {}
        self.first_actual_call = True  # 新增标志，用于判断是否是首次实际API调用

        self._initialize_api_keys()  # 初始化时进行API Key有效性测试
        self._configure_gemini_api()  # 配置Gemini API

    def _initialize_api_keys(self):
        """测试并初始化可用的API Key列表。初始化时不触发等待。"""
        logger.info("开始测试Gemini API Key的有效性...")
        valid_keys = []
        current_time = time.time()
        for key in self.all_api_keys:
            # 初始化测试时不触发等待
            if self._test_api_key_validity(key, during_initialization=True):
                valid_keys.append(key)
                # 初始化时记录当前时间，避免首次使用时显示大数值
                self.key_last_used_time[key] = current_time
                self.key_cooldown_until[key] = 0.0

        self.api_keys = valid_keys
        if not self.api_keys:
            logger.critical(
                "所有提供的Gemini API Key均无效或未设置。语义比对功能将无法使用。"
            )
        else:
            logger.info(f"成功识别 {len(self.api_keys)} 个有效Gemini API Key。")

    def _test_api_key_validity(
        self, api_key: str, during_initialization: bool = False
    ) -> bool:
        """
        测试单个Gemini API Key的有效性。
        通过尝试获取模型信息来验证，不列出所有模型。

        Args:
            api_key: 要测试的API Key
            during_initialization: 是否在初始化阶段调用此方法

        Returns:
            bool: API Key 是否有效
        """
        if not re.match(r"^[a-zA-Z0-9_-]{20,}$", api_key):
            logger.warning(f"API Key格式无效: {api_key[:5]}...")
            return False

        try:
            # 使用新SDK创建客户端
            client = genai.Client(api_key=api_key)

            # 尝试获取特定模型信息（轻量级验证）
            # 使用一个已知模型名称，例如"gemini-2.5-flash"
            model_info = client.models.get(model="gemini-2.5-flash")  # type: ignore
            if model_info:
                # 初始化阶段只记录有效性，不触发等待日志
                if not during_initialization:
                    logger.info(f"API Key {api_key[:5]}... 有效。")
                return True
            return False
        except Exception:
            # 初始化阶段只记录警告，不触发等待日志
            if not during_initialization:
                logger.warning(f"API Key {api_key[:5]}... 为无效或已过期。请检查：")
                logger.info(
                    "1. API密钥是否正确（在 https://aistudio.google.com/app/apikey 查看）"
                )
                logger.info("2. 网络连接是否正常（特别是代理设置）")
                url = "https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/"
                logger.info(f"3. 是否启用了Gemini API（在 {url} 启用）")
            return False

    def _configure_gemini_api(self):
        """配置Gemini API，使用当前API Key。"""
        if not self.api_keys:
            logger.warning("没有可用的Gemini API密钥，无法配置模型。")
            self.client = None  # 确保客户端为None
            return

        current_api_key = self.api_keys[self.current_key_index]
        try:
            # 使用新SDK创建客户端
            self.client = genai.Client(api_key=current_api_key)
            logger.info(
                f"Gemini API 已配置，使用密钥索引: {self.current_key_index} (密钥: {current_api_key[:5]}...)，模型: {self.model_name}"
            )
            # 成功配置后，更新当前key的上次使用时间
            self.key_last_used_time[current_api_key] = time.time()
        except Exception as e:
            logger.error(f"Gemini API 配置失败，密钥索引 {self.current_key_index}: {e}")
            logger.info("请检查：")
            logger.info(
                "1. API密钥是否正确（在 https://aistudio.google.com/app/apikey 查看）"
            )
            logger.info("2. 网络连接是否正常（特别是代理设置）")
            logger.info(
                "3. 是否启用了Gemini API（在 https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/ 启用）"
            )
            self.client = None
            # 如果当前密钥配置失败，尝试轮转到下一个密钥
            if self.api_keys:  # 只有当还有其他密钥时才尝试轮转
                logger.info("当前密钥配置失败，尝试轮转到下一个可用密钥。")
                self.rotate_key(force_rotate=True)  # 强制轮转到下一个密钥

    def rotate_key(self, force_rotate: bool = False):
        """
        轮转到下一个API Key。

        Args:
            force_rotate: 如果为True，则强制轮转，跳过冷却时间检查。
        """
        if not self.api_keys:
            logger.warning("没有可用的API密钥进行轮转。")
            return

        current_time = time.time()

        # 调试日志：显示所有密钥状态
        logger.debug(
            f"开始密钥轮转，当前密钥索引: {self.current_key_index}, 强制轮转: {force_rotate}"
        )
        for index, key in enumerate(self.api_keys):
            cooldown_until = self.key_cooldown_until.get(key, 0.0)
            cooldown_remaining = max(0.0, cooldown_until - current_time)
            time_since_last_use = current_time - self.key_last_used_time.get(key, 0.0)
            logger.debug(
                f"密钥 {index}: 冷却剩余 {cooldown_remaining:.1f}s, 上次使用 {time_since_last_use:.1f}s前"
            )

        # 循环直到找到一个可用的密钥
        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            next_key = self.api_keys[self.current_key_index]

            cooldown_until = self.key_cooldown_until.get(next_key, 0.0)
            cooldown_remaining = max(0.0, cooldown_until - current_time)
            time_since_last_use = current_time - self.key_last_used_time.get(
                next_key, 0.0
            )

            # 强制轮转（因429错误）直接使用下一个密钥
            if force_rotate:
                logger.info(
                    f"强制轮转: 跳过等待, 新密钥索引: {self.current_key_index} (密钥: {next_key[:5]}...)"
                )
                self.key_last_used_time[next_key] = current_time
                self._configure_gemini_api()
                return

            # 检查密钥是否可用
            if cooldown_remaining <= 0:
                # 如果是首次实际调用，则跳过60秒等待
                if self.first_actual_call:
                    logger.info(
                        f"首次实际调用，密钥 {self.current_key_index} 可用 (密钥: {next_key[:5]}...)"
                    )
                    self.first_actual_call = False  # 标记首次调用已完成
                # 智能等待策略：距离上次使用不足60秒则等待
                elif time_since_last_use < 60:
                    wait_time = 60 - time_since_last_use
                    logger.info(
                        f"密钥 {self.current_key_index} 需要等待: {wait_time:.1f}s (上次使用: {time_since_last_use:.1f}s前)"
                    )
                    # 在这里添加等待提示
                    stop_event = threading.Event()
                    waiting_thread = threading.Thread(
                        target=show_waiting_indicator, args=(stop_event, "等待密钥冷却")
                    )
                    waiting_thread.daemon = True
                    waiting_thread.start()
                    time.sleep(wait_time)
                    stop_event.set()
                    if waiting_thread.is_alive():
                        waiting_thread.join(timeout=0.5)

                logger.info(
                    f"密钥 {self.current_key_index} 可用 (冷却已过, 密钥: {next_key[:5]}...)"
                )
                self.key_last_used_time[next_key] = time.time()  # 更新为当前时间
                self._configure_gemini_api()
                return
            else:
                logger.info(
                    f"密钥 {self.current_key_index} 冷却中: 剩余 {cooldown_remaining:.1f}s (密钥: {next_key[:5]}...)"
                )

        # 所有密钥都不可用时等待最长冷却时间
        max_cooldown = max(self.key_cooldown_until.values(), default=0) - current_time
        if max_cooldown > 0:
            logger.warning(f"所有密钥不可用，等待最长冷却时间: {max_cooldown:.1f}s")
            # 在这里添加等待提示
            stop_event = threading.Event()
            waiting_thread = threading.Thread(
                target=show_waiting_indicator, args=(stop_event, "等待所有密钥冷却")
            )
            waiting_thread.daemon = True
            waiting_thread.start()
            time.sleep(max_cooldown)
            stop_event.set()
            if waiting_thread.is_alive():
                waiting_thread.join(timeout=0.5)

            self.rotate_key(force_rotate)  # 递归尝试
        else:
            logger.error("所有密钥均不可用且无有效冷却时间")
            # 在所有密钥都不可用时，不退出程序，而是让调用者处理无可用模型的情况
            self.client = None  # 确保客户端为None

    def get_client(self):
        """获取当前配置的Gemini客户端实例。"""
        return self.client

    def get_prompt(
        self, question: str, ai_answer: str, source_document_content: str
    ) -> str:
        """
        生成带问答和源文档内容的提示词。

        Args:
            question: 问题内容
            ai_answer: AI回答内容
            source_document_content: 源文档内容

        Returns:
            str: 生成的提示词
        """
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


def check_semantic_similarity(
    gemini_api_handler: GeminiAPIHandler,
    question: str,
    ai_answer: str,
    source_document_content: str,
) -> tuple[str, str]:
    """
    使用Gemini API判断AI客服回答与源文档在语义上是否相符，并返回判断结果和原因。
    使用GeminiAPIHandler处理API调用和密钥轮转。

    Args:
        gemini_api_handler: Gemini API 处理器实例
        question: 问题内容
        ai_answer: AI回答内容
        source_document_content: 源文档内容

    Returns:
        tuple[str, str]: (结果, 原因)，结果为"是"/"否"/"错误"
    """
    max_retries = 5  # API调用重试次数
    default_retry_delay = 60  # 默认等待时间（秒）

    for attempt in range(max_retries):
        start_time = time.time()  # 记录API调用开始时间

        # 在每次API调用前尝试轮转密钥并获取客户端
        gemini_api_handler.rotate_key()
        client = gemini_api_handler.get_client()

        if not client:
            if not _handle_no_client(
                question, attempt, max_retries, default_retry_delay
            ):
                return "错误", "无可用Gemini模型"
            continue

        prompt = gemini_api_handler.get_prompt(
            question, ai_answer, source_document_content
        )

        # 创建停止事件和等待线程
        stop_event = threading.Event()
        waiting_thread = threading.Thread(
            target=show_waiting_indicator, args=(stop_event, "Gemini")
        )
        waiting_thread.daemon = True
        waiting_thread.start()

        try:
            result, reason = _call_gemini_api(
                client,
                gemini_api_handler,
                prompt,
                question,
                attempt,
                max_retries,
                start_time,
                default_retry_delay,
            )
            if result != "RETRY":
                return result, reason

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"调用Gemini API时发生错误 (问题: '{question[:50]}...', 尝试 {attempt + 1}/{max_retries})：{error_msg}，耗时: {time.time() - start_time:.2f} 秒"
            )
            logger.debug(
                f"完整错误信息: {str(e)}", exc_info=True
            )  # 添加详细错误日志

            # 非速率限制错误，也进行重试（可能是其他临时网络问题）
            if attempt < max_retries - 1:
                logger.warning(
                    f"非速率限制错误，等待 {default_retry_delay} 秒后重试 (问题: '{question[:50]}...)。"
                )
                time.sleep(default_retry_delay)
                # 强制轮转到下一个密钥并在下一次循环开始时使用
                gemini_api_handler.rotate_key(force_rotate=True)
                continue  # 重试当前记录
            else:
                logger.error(
                    f"语义比对多次重试后失败 (问题: '{question[:50]}...'): {error_msg}"
                )
                return "错误", f"API调用多次重试失败: {error_msg}"

        finally:
            # 确保停止等待指示器
            stop_event.set()
            if waiting_thread.is_alive():
                waiting_thread.join(timeout=0.5)

    # 如果所有重试都失败
    return "错误", "API调用多次重试失败"


def _handle_no_client(
    question: str, attempt: int, max_retries: int, default_retry_delay: int
) -> bool:
    """
    处理无可用客户端的情况

    Returns:
        bool: True 表示需要重试，False 表示应该返回错误
    """
    logger.warning(
        f"Gemini客户端未成功初始化或无可用密钥，跳过API调用 (问题: '{question[:50]}...', 尝试 {attempt + 1}/{max_retries})。"
    )
    if attempt < max_retries - 1:
        # 如果没有可用密钥，等待一段时间再重试
        logger.info(
            f"等待 {default_retry_delay} 秒后重试 (问题: '{question[:50]}...')。"
        )
        time.sleep(default_retry_delay)
        return True
    else:
        logger.error(
            f"多次尝试后仍无可用Gemini模型，语义比对失败 (问题: '{question[:50]}...')。"
        )
        return False


def _call_gemini_api(
    client,
    gemini_api_handler: GeminiAPIHandler,
    prompt: str,
    question: str,
    attempt: int,
    max_retries: int,
    start_time: float,
    default_retry_delay: int,
) -> tuple[str, str]:
    """
    调用 Gemini API 并处理响应

    Returns:
        tuple[str, str]: (结果, 原因) 或 ("RETRY", "") 表示需要重试
    """
    try:
        logger.info(
            f"正在调用Gemini API进行语义比对 (问题: '{question[:50]}...', 尝试 {attempt + 1}/{max_retries})..."
        )
        # 使用新SDK生成内容（使用正确的配置类型）
        response = client.models.generate_content(  # type: ignore
            model=gemini_api_handler.model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(temperature=0),
        )
        end_time = time.time()  # 记录API调用结束时间
        duration = end_time - start_time  # 计算耗时
        logger.info(
            f"Gemini API调用完成，耗时: {duration:.2f} 秒 (问题: '{question[:50]}...')。"
        )

        # 确保响应有效
        if response is None or response.text is None:
            logger.warning("Gemini API返回空响应")
            return "错误", "API返回空响应"

        # 尝试解析Gemini返回的JSON
        response_text = response.text.strip()
        # 移除可能存在的Markdown代码块标记
        if response_text.startswith("```json") and response_text.endswith(
            "```"
        ):
            response_text = response_text[7:-3].strip()

        try:
            parsed_response = json.loads(response_text)
            result = parsed_response.get("result", "无法判断").strip()
            reason = parsed_response.get("reason", "无").strip()

            # 根据结果设置颜色和加粗
            colored_result = result
            if result == "是":
                colored_result = (
                    Style.BRIGHT + Fore.GREEN + result + Style.RESET_ALL
                )
            elif result == "否":
                colored_result = (
                    Style.BRIGHT + Fore.RED + result + Style.RESET_ALL
                )

            logger.info(
                f"语义比对结果：{colored_result} (问题: '{question[:50]}...')"
            )
            return result, reason
        except json.JSONDecodeError as e:
            logger.warning(f"解析JSON失败: {response_text}, 错误: {e}")
            return "错误", f"JSON解析失败: {e}"

    except json.JSONDecodeError as e:
        end_time = time.time()  # 记录API调用结束时间
        duration = end_time - start_time  # 计算耗时
        logger.warning(
            f"Gemini返回的JSON格式不正确，错误：{e}，耗时: {duration:.2f} 秒 (问题: '{question[:50]}...)。"
        )
        # JSON解析错误通常不是临时错误，不进行重试
        return "错误", f"JSON解析错误: {e}"

    except google.api_core.exceptions.ResourceExhausted as e:
        return _handle_rate_limit_error(
            e,
            gemini_api_handler,
            question,
            attempt,
            max_retries,
            start_time,
            default_retry_delay,
        )


def _handle_rate_limit_error(
    e,
    gemini_api_handler: GeminiAPIHandler,
    question: str,
    attempt: int,
    max_retries: int,
    start_time: float,
    default_retry_delay: int,
) -> tuple[str, str]:
    """
    处理速率限制错误 (429)

    Returns:
        tuple[str, str]: (结果, 原因) 或 ("RETRY", "") 表示需要重试
    """
    end_time = time.time()  # 记录API调用结束时间
    duration = end_time - start_time  # 计算耗时
    error_msg = str(e)
    logger.warning(
        f"调用Gemini API时发生速率限制错误 (429) (问题: '{question[:50]}...', 尝试 {attempt + 1}/{max_retries})：{error_msg}，耗时: {duration:.2f} 秒"
    )

    retry_after = _extract_retry_delay_from_error(e, default_retry_delay, question)

    if attempt < max_retries - 1:
        logger.info(
            f"检测到429错误，立即强制轮转到下一个密钥 (问题: '{question[:50]}...)。"
        )
        # 更新当前密钥的冷却时间
        current_key = gemini_api_handler.api_keys[
            gemini_api_handler.current_key_index
        ]
        gemini_api_handler.key_cooldown_until[current_key] = (
            time.time() + retry_after
        )
        gemini_api_handler.rotate_key(
            force_rotate=True
        )  # 强制轮转到下一个密钥
        return "RETRY", ""  # 重试当前记录
    else:
        logger.error(
            f"语义比对多次重试后失败 (问题: '{question[:50]}...'): {error_msg}"
        )
        return "错误", f"API调用多次重试失败: {error_msg}"


def _extract_retry_delay_from_error(
    e, default_retry_delay: int, question: str
) -> int:
    """
    从错误中提取重试延迟时间

    Returns:
        int: 重试延迟时间（秒）
    """
    retry_after = default_retry_delay
    error_msg = str(e)

    # 尝试从异常对象本身或其details属性中提取retryDelay
    details = getattr(e, "details", [])  # 尝试获取details属性，如果不存在则为空列表
    if not details and hasattr(e, "message"):  # 如果details为空，尝试解析错误消息字符串
        # 尝试从错误消息字符串中解析retryDelay
        retry_delay_match = re.search(r"'retryDelay': '(\d+)s'", error_msg)
        if retry_delay_match:
            try:
                retry_after = (
                    int(retry_delay_match.group(1)) + 5
                )  # 增加5秒缓冲
                logger.info(
                    f"从错误消息中提取到建议的重试延迟: {retry_after} 秒 (问题: '{question[:50]}...)。"
                )
            except ValueError:
                logger.warning(
                    f"无法解析错误消息中的retryDelay。使用默认等待时间 {default_retry_delay} 秒 (问题: '{question[:50]}...)。"
                )
                retry_after = default_retry_delay
        else:
            logger.warning(
                f"未在错误详情或错误消息中找到retryDelay信息。使用默认等待时间 {default_retry_delay} 秒 (问题: '{question[:50]}...)。"
            )
            retry_after = default_retry_delay
    else:  # 如果details不为空，遍历details查找retryDelay
        found_retry_delay = False
        for detail in details:
            # 假设detail是ErrorInfo对象或类似结构
            if hasattr(detail, "retry_delay") and hasattr(
                detail.retry_delay, "seconds"
            ):
                retry_after = detail.retry_delay.seconds
                logger.info(
                    f"从API错误详情中提取到建议的重试延迟: {retry_after} 秒 (问题: '{question[:50]}...)。"
                )
                found_retry_delay = True
                break
        if not found_retry_delay:
            logger.warning(
                f"在错误详情中未找到retryDelay信息。使用默认等待时间 {default_retry_delay} 秒 (问题: '{question[:50]}...)。"
            )
            retry_after = default_retry_delay

    return retry_after
