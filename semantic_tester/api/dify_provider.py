"""
Dify AI 供应商实现

参考 dify_chat_tester 项目设计，适配 semantic_tester 语义分析需求
"""

import logging
import threading
import time
from typing import List, Optional, Dict, Any

import requests

from .base_provider import AIProvider, APIError, AuthenticationError, RateLimitError
from .prompts import SEMANTIC_CHECK_PROMPT

logger = logging.getLogger(__name__)

try:
    import colorama

    colorama.init(autoreset=True)
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    RESET = colorama.Fore.RESET
except ImportError:

    class Style:
        GREEN = ""
        RED = ""
        YELLOW = ""
        RESET = ""


class DifyProvider(AIProvider):
    """Dify AI 供应商实现"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Dify 供应商

        Args:
            config: Dify 配置字典，包含 api_keys, base_url 等
        """
        super().__init__(config)
        self.name = config.get("name", "Dify")
        self.id = config.get("id", "dify")
        self.api_keys = config.get("api_keys", [])
        self.base_url = config.get("base_url", "https://api.dify.ai/v1")
        self.app_id = config.get("app_id", "")
        self.has_config = config.get("has_config", len(self.api_keys) > 0)

        # 内部状态
        self.current_key_index = 0
        self.key_last_used_time: Dict[str, float] = {}
        self.key_cooldown_until: Dict[str, float] = {}
        self.first_actual_call = True
        self.lock = threading.Lock()  # 用于多线程并发下的同步

        # 确保 base_url 以 /v1 结尾
        self.base_url = self.base_url.rstrip("/")
        if not self.base_url.endswith("/v1"):
            self.base_url += "/v1"

        # 初始化可用密钥
        self._initialize_api_keys()

        logger.debug(f"Dify 供应商初始化完成: {self.base_url}")

    def _initialize_api_keys(self):
        """初始化 API 密钥列表"""
        if not self.api_keys:
            logger.warning("Dify API 密钥未配置")
            return

        current_time = time.time()
        for key in self.api_keys:
            self.key_last_used_time[key] = current_time
            self.key_cooldown_until[key] = 0.0

        logger.debug(f"已初始化 {len(self.api_keys)} 个 Dify API 密钥")

    def get_models(self) -> List[str]:
        """获取可用的模型列表"""
        # Dify 使用应用 ID，不支持传统意义上的模型列表
        return ["Dify App"]

    def get_default_model(self) -> str:
        """获取默认模型"""
        return "Dify App"

    def is_configured(self) -> bool:
        """检查是否已正确配置"""
        return len(self.api_keys) > 0

    def validate_api_key(self, api_key: str) -> bool:
        """验证 API 密钥有效性"""
        if not api_key:
            return False

        try:
            # 发送一个简单的测试请求
            # 使用 chat-messages 端点
            url = f"{self.base_url}/chat-messages"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "inputs": {},
                "query": "test",
                "response_mode": "blocking",
                "user": "validator",
            }

            # 如果有 app_id，添加到 payload
            if self.app_id:
                payload["app_id"] = self.app_id

            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Dify API 密钥验证成功")
                return True
            elif response.status_code == 401:
                logger.warning("Dify API 密钥无效")
                return False
            else:
                logger.warning(
                    f"Dify API 密钥验证失败，状态码: {response.status_code}, URL: {url}"
                )
                return False

        except Exception as e:
            logger.error(f"Dify API 密钥验证异常: {e}")
            return False

    def check_semantic_similarity(  # noqa: C901
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
            question: 用户问题
            ai_answer: AI回答
            source_document: 源文档内容
            model: 模型名称（Dify不使用此参数）
            stream: 是否使用流式输出
            show_thinking: 不支持（Dify不支持思维链）

        Returns:
            tuple[str, str]: (结果, 判断依据)
        """
        if not self.is_configured():
            error_msg = "Dify API 密钥未配置"
            logger.error(error_msg)
            return "错误", error_msg

        # 构造语义分析提示词
        prompt = self._build_semantic_analysis_prompt(
            question, ai_answer, source_document
        )

        max_retries = 3

        for attempt in range(max_retries):
            # 创建等待指示器
            stop_event = threading.Event()
            waiting_thread = threading.Thread(
                target=self.show_waiting_indicator, args=(stop_event,)
            )
            waiting_thread.daemon = True

            # 只在非流式模式显示等待指示器
            if not stream:
                waiting_thread.start()

            try:
                # 发送请求到 Dify API
                response_data = self._send_dify_request(prompt, stream, stop_event)

                # 停止等待指示器以便显示结果或日志
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

                # 处理响应
                return self._process_dify_response(response_data)

            except (
                AuthenticationError,
                RateLimitError,
                requests.exceptions.RequestException,
                APIError,
            ) as e:
                # 停止等待指示器
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

                logger.warning(
                    f"Dify API 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                )

                # 如果是最后一次尝试，或者未启用自动轮转且不是网络/API错误，则抛出异常或返回错误
                # 注意：对于网络错误，即使不轮转也应该重试（可能是临时网络波动）
                is_network_error = isinstance(
                    e, (requests.exceptions.RequestException, APIError)
                )

                if attempt == max_retries - 1:
                    if is_network_error:
                        return "错误", f"Dify API 调用多次重试失败: {str(e)}"
                    if not self.auto_rotate:
                        raise e

                # 对于认证和速率限制错误，尝试轮转密钥
                if isinstance(e, (AuthenticationError, RateLimitError)):
                    if self.auto_rotate:
                        logger.info("尝试轮转 Dify API 密钥...")

                        # 标记当前密钥冷却 (默认60秒)
                        current_key = self.api_keys[self.current_key_index]
                        retry_after = self._extract_retry_delay(str(e)) or 60
                        self.key_cooldown_until[current_key] = time.time() + retry_after

                        self._rotate_key(force_rotate=True)

                # 对于网络错误，等待一段时间后重试
                time.sleep(2)  # 稍作等待

            except Exception as e:
                # 停止等待指示器
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

                error_msg = f"Dify API 调用异常: {str(e)}"
                logger.error(error_msg)
                return "错误", error_msg
            finally:
                # 确保指示器停止
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

        return "错误", "Dify API 调用多次重试失败"

    def _rotate_key(self, force_rotate: bool = False):
        """轮转到下一个 API 密钥（线程安全）"""
        if not self.api_keys or len(self.api_keys) <= 1:
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

                if cooldown_remaining <= 0:
                    if self.first_actual_call:
                        logger.info(f"首次实际调用，密钥 {self.current_key_index} 可用")
                        self.first_actual_call = False

                    logger.info(f"密钥 {self.current_key_index} 可用")
                    self.key_last_used_time[next_key] = current_time
                    break
                else:
                    logger.info(
                        f"密钥 {self.current_key_index} 冷却中: 剩余 {cooldown_remaining:.1f}s"
                    )
            else:
                max_cooldown = (
                    max(self.key_cooldown_until.values(), default=0) - current_time
                )
                if max_cooldown > 0:
                    wait_time_outside_lock = max_cooldown
                    logger.warning(
                        f"所有密钥不可用，等待最长冷却时间: {max_cooldown:.1f}s"
                    )

        # 在锁外执行等待
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

    def _send_dify_request(  # noqa: C901
        self,
        prompt: str,
        stream: bool = False,
        stop_event: Optional[threading.Event] = None,
    ) -> Any:
        """
        发送请求到Dify API

        Args:
            prompt: 提示词
            stream: 是否使用流式输出
            stop_event: 停止事件（用于停止等待指示器）

        Returns:
            str or requests.Response: 流式返回字符串，非流式返回Response对象

        Raises:
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            APIError: API错误
            requests.exceptions.Timeout: 请求超时
            requests.exceptions.ConnectionError: 连接失败
        """
        import sys
        import json

        # 构建请求 - 使用 chat-messages 端点
        url = f"{self.base_url}/chat-messages"
        # 获取当前API密钥
        current_key = self.api_keys[self.current_key_index] if self.api_keys else ""

        headers = {
            "Authorization": f"Bearer {current_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": {},
            "query": prompt,
            "response_mode": "streaming" if stream else "blocking",
            "user": "semantic_tester",
        }

        if self.app_id:
            payload["app_id"] = self.app_id

        logger.debug(f"发送 Dify API 请求: {url}")
        logger.debug(f"流式模式: {stream}")

        start_time = time.time()

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60,
                stream=stream,
                allow_redirects=True,
            )

            # 处理状态码错误
            if response.status_code != 200:
                if (
                    response.status_code == 405
                    and response.history
                    and url.startswith("http://")
                ):
                    logger.warning(
                        "检测到 HTTP 重定向导致 405 错误，尝试自动切换到 HTTPS..."
                    )
                    https_url = url.replace("http://", "https://", 1)
                    response = requests.post(
                        https_url,
                        headers=headers,
                        json=payload,
                        timeout=60,
                        stream=stream,
                    )
                    if response.status_code == 200:
                        self.base_url = self.base_url.replace("http://", "https://", 1)
                else:
                    response.raise_for_status()

            if stream:
                # 流式处理
                if stop_event:
                    stop_event.set()

                full_response = ""
                first_char_printed = False

                logger.info("开始接收Dify流式响应...")

                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8")

                        if decoded_line.startswith("data:"):
                            try:
                                data = json.loads(decoded_line[5:])
                                event = data.get("event")

                                # 处理错误事件
                                if event == "error":
                                    error_msg = data.get("message", "未知错误")
                                    logger.error(f"Dify API 返回错误: {error_msg}")
                                    raise APIError(error_msg)

                                # 处理消息事件
                                elif event == "message":
                                    if "answer" in data:
                                        answer_chunk = data["answer"]

                                        if not first_char_printed:
                                            sys.stdout.write(f"\r{' ' * 50}\r")
                                            sys.stdout.write("Dify: ")
                                            sys.stdout.flush()
                                            first_char_printed = True

                                        print(answer_chunk, end="", flush=True)
                                        full_response += answer_chunk

                                # 消息结束
                                elif event == "message_end":
                                    break

                            except json.JSONDecodeError:
                                continue

                if first_char_printed:
                    print()

                end_time = time.time()
                logger.debug(
                    f"Dify API 流式响应完成，耗时: {end_time - start_time:.2f} 秒"
                )

                return full_response
            else:
                # 非流式处理，直接返回response对象
                end_time = time.time()
                logger.debug(f"Dify API 响应时间: {end_time - start_time:.2f} 秒")
                return response

        except requests.exceptions.RequestException as e:
            # 如果是连接错误，且是 http，尝试 https
            if url.startswith("http://") and not isinstance(
                e, requests.exceptions.SSLError
            ):
                logger.warning(f"请求失败: {e}，尝试切换到 HTTPS 重试...")
                https_url = url.replace("http://", "https://", 1)
                response = requests.post(
                    https_url, headers=headers, json=payload, timeout=60, stream=stream
                )
                if response.status_code == 200:
                    self.base_url = self.base_url.replace("http://", "https://", 1)

                    if stream:
                        # 重新处理流式
                        full_response = ""
                        for line in response.iter_lines():
                            if line:
                                decoded_line = line.decode("utf-8")
                                if decoded_line.startswith("data:"):
                                    try:
                                        data = json.loads(decoded_line[5:])
                                        if (
                                            data.get("event") == "message"
                                            and "answer" in data
                                        ):
                                            full_response += data["answer"]
                                        elif data.get("event") == "message_end":
                                            break
                                    except json.JSONDecodeError:
                                        continue
                        return full_response
                    else:
                        return response
            else:
                raise e

    def _process_dify_response(self, response_data: Any) -> tuple[str, str]:
        """
        处理Dify API响应

        Args:
            response_data: 流式模式下是字符串，非流式模式下是Response对象

        Returns:
            tuple[str, str]: (结果, 判断依据)

        Raises:
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            APIError: API错误
        """
        # 如果是字符串，说明是流式返回的完整响应
        if isinstance(response_data, str):
            answer = response_data
            if not answer:
                error_msg = "Dify API 流式返回空回答"
                logger.warning(error_msg)
                return "错误", error_msg

            # 解析语义分析结果
            result, reason = self._parse_semantic_result(answer)
            logger.info(f"Dify 语义分析完成: {result}")
            return result, reason

        # 否则是Response对象，按原来的方式处理
        response = response_data
        status_code = response.status_code

        if status_code == 200:
            return self._handle_success_response(response)
        elif status_code == 401:
            error_msg = "Dify API 认证失败，请检查 API 密钥"
            logger.error(error_msg)
            raise AuthenticationError(error_msg)
        elif status_code == 429:
            error_msg = "Dify API 速率限制，请稍后重试"
            logger.warning(error_msg)
            raise RateLimitError(error_msg)
        else:
            # 记录更多调试信息
            logger.error(f"请求 URL: {response.url}")
            if response.history:
                logger.error(f"重定向历史: {response.history}")

            error_msg = (
                f"Dify API 请求失败，状态码: {status_code}, 响应: {response.text}"
            )
            logger.error(error_msg)
            raise APIError(error_msg)

    def _handle_success_response(self, response: requests.Response) -> tuple[str, str]:
        """
        处理成功响应

        Args:
            response: API响应

        Returns:
            tuple[str, str]: (结果, 判断依据)
        """
        result_data = response.json()
        logger.debug(f"Dify API 响应数据: {result_data}")

        # 提取回答内容
        answer = result_data.get("answer", "")
        if not answer:
            # 尝试从其他常见字段获取回答，以防 API 版本差异
            if "message" in result_data:
                answer = result_data["message"]
            elif "data" in result_data and isinstance(result_data["data"], dict):
                answer = result_data["data"].get("answer", "")

        if not answer:
            error_msg = f"Dify API 返回空回答。完整响应: {result_data}"
            logger.warning(error_msg)
            return "错误", error_msg

        # 解析语义分析结果
        result, reason = self._parse_semantic_result(answer)
        logger.info(f"Dify 语义分析完成: {result}")
        return result, reason

    def _build_semantic_analysis_prompt(
        self, question: str, ai_answer: str, source_document: str
    ) -> str:
        """
        构建语义分析提示词

        Args:
            question: 用户问题
            ai_answer: AI回答
            source_document: 源文档内容

        Returns:
            str: 构造的提示词
        """
        # 限制文档长度以避免超出 token 限制
        max_doc_length = 8000
        if len(source_document) > max_doc_length:
            source_document = source_document[:max_doc_length] + "..."

        return SEMANTIC_CHECK_PROMPT.format(
            question=question,
            ai_answer=ai_answer,
            source_document=source_document,
        )

    def _parse_semantic_result(self, response: str) -> tuple[str, str]:
        """
        解析语义分析结果

        Args:
            response: Dify API 返回的回答

        Returns:
            tuple[str, str]: (结果, 判断依据)
        """
        try:
            import json

            # 尝试解析 JSON
            clean_text = response.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text.strip("`")
            clean_text = clean_text.strip()

            try:
                data = json.loads(clean_text)
                result = data.get("result", "无法确定")
                reason = data.get("reason", "无")
                return result, reason
            except json.JSONDecodeError:
                pass

            # 尝试提取判断结果和判断依据 (旧格式兼容)
            result, reason = self._extract_result_and_reason(response)

            # 如果没有找到标准格式，尝试其他解析方式
            if not result:
                result = self._fallback_result_extraction(response)

            if not reason:
                # 如果没有找到判断依据，使用整个回答作为依据
                reason = response

            # 清理结果
            result = result.strip()
            reason = reason.strip()

            # 验证结果有效性
            result = self._validate_result(result, reason)

            logger.debug(f"Dify 结果解析: 结果={result}, 依据长度={len(reason)}")
            return result, reason

        except Exception as e:
            logger.error(f"解析 Dify 回答时出错: {e}")
            return "错误", f"解析回答失败: {str(e)}"

    def _extract_result_and_reason(self, response: str) -> tuple[str, str]:
        """
        从响应中提取结果和原因

        Returns:
            tuple[str, str]: (结果, 原因)
        """
        lines = response.strip().split("\n")
        result = ""
        reason = ""

        for line in lines:
            line = line.strip()
            if line.startswith("判断结果："):
                result_part = line.replace("判断结果：", "").strip()
                if "是" in result_part:
                    result = "是"
                elif "否" in result_part:
                    result = "否"
                else:
                    result = result_part
            elif line.startswith("判断依据："):
                reason = line.replace("判断依据：", "").strip()
            elif reason and line:  # 如果已经找到判断依据，继续收集后续内容
                reason += " " + line

        return result, reason

    def _fallback_result_extraction(self, response: str) -> str:
        """
        备用结果提取方法

        Returns:
            str: 提取的结果
        """
        if "判断结果：是" in response.lower() or "结果：是" in response.lower():
            return "是"
        elif "判断结果：否" in response or "结果：否" in response:
            return "否"
        else:
            # 尝试从第一行提取结果
            lines = response.strip().split("\n")
            first_line = lines[0].strip() if lines else ""
            if "是" in first_line and "否" not in first_line:
                return "是"
            elif "否" in first_line:
                return "否"
            else:
                return "无法确定"

    def _validate_result(self, result: str, reason: str) -> str:
        """
        验证结果的有效性

        Returns:
            str: 验证后的结果
        """
        if result not in ["是", "否"]:
            logger.warning(f"Dify 返回的判断结果无效: {result}")
            if "是" in reason and "否" not in reason:
                result = "是"
            elif "否" in reason:
                result = "否"
            else:
                result = "无法确定"

        return result

    def get_provider_info(self) -> Dict[str, Any]:
        """获取供应商信息"""
        return {
            "name": self.name,
            "id": self.id,
            "models": self.get_models(),
            "configured": self.is_configured(),
            "default_model": self.get_default_model(),
            "base_url": self.base_url,
            "app_id": self.app_id if self.app_id else "未设置",
        }
