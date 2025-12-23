"""
iFlow AI 供应商实现

基于 dify_chat_tester 项目的 iFlow 渠道实现
适配 semantic_tester 的语义分析接口

作者：Mison
邮箱：1360962086@qq.com
"""

import logging
import threading
import time
import requests
from typing import Dict, List, Optional, Any

from semantic_tester.api.base_provider import AIProvider
from semantic_tester.api.prompts import SEMANTIC_CHECK_PROMPT

logger = logging.getLogger(__name__)


class IflowProvider(AIProvider):
    """iFlow AI 供应商实现"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 iFlow 供应商

        Args:
            config: 配置字典，包含 api_keys, base_url 等信息
        """
        super().__init__(config)

        self.name = config.get("name", "iFlow")
        self.id = config.get("id", "iflow")
        self.api_keys = config.get("api_keys", [])
        self.base_url = config.get("base_url", "https://apis.iflow.cn/v1")
        self.has_config = config.get("has_config", len(self.api_keys) > 0)
        self.default_model = config.get("model", "qwen3-max")
        # 添加 model 属性以便统一访问
        self.model = self.default_model

        # iFlow 支持的模型列表
        self.available_models = config.get(
            "models", ["qwen3-max", "kimi-k2-0905", "glm-4.6", "deepseek-v3.2"]
        )

        # 内部状态
        self.client = None
        self.current_key_index = 0
        self.key_last_used_time: Dict[str, float] = {}
        self.key_cooldown_until: Dict[str, float] = {}
        self.lock = threading.Lock()  # 用于多线程并发下的同步

        # 初始化可用密钥和客户端
        self._initialize_api_keys()
        self._initialize_client()

    def _initialize_api_keys(self):
        """初始化 API 密钥列表"""
        if not self.api_keys:
            logger.warning("iFlow API 密钥未配置")
            return

        current_time = time.time()
        for key in self.api_keys:
            self.key_last_used_time[key] = current_time
            self.key_cooldown_until[key] = 0.0

        logger.debug(f"已初始化 {len(self.api_keys)} 个 iFlow API 密钥")

    def _initialize_client(self):
        """初始化客户端"""
        # iFlow 使用 requests 直接调用，不需要特殊客户端，但我们设置 session
        if self.has_config and self.api_keys:
            self.client = requests.Session()
            self._update_client_headers()
            logger.debug("iFlow 客户端初始化成功")
        else:
            logger.warning("iFlow API 密钥未配置，跳过客户端初始化")

    def _update_client_headers(self):
        """更新客户端头信息（切换密钥时调用）"""
        if self.client and self.api_keys:
            current_key = self.api_keys[self.current_key_index]
            self.client.headers.update(
                {
                    "Authorization": f"Bearer {current_key}",
                    "Content-Type": "application/json",
                }
            )

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

                if cooldown_remaining <= 0:
                    logger.info(f"iFlow 密钥 {self.current_key_index} 可用")
                    self.key_last_used_time[next_key] = current_time
                    self._update_client_headers()
                    return
                else:
                    logger.info(
                        f"iFlow 密钥 {self.current_key_index} 冷却中: 剩余 {cooldown_remaining:.1f}s"
                    )
            else:
                max_cooldown = (
                    max(self.key_cooldown_until.values(), default=0) - current_time
                )
                if max_cooldown > 0:
                    wait_time_outside_lock = max_cooldown
                    logger.warning(
                        f"iFlow 所有密钥不可用，等待最长冷却时间: {max_cooldown:.1f}s"
                    )

        # 在锁外执行等待
        if wait_time_outside_lock > 0:
            time.sleep(wait_time_outside_lock)

    def get_models(self) -> List[str]:
        """
        获取可用的模型列表

        Returns:
            List[str]: 模型列表
        """
        return self.available_models.copy()

    def get_default_model(self) -> str:
        """
        获取默认模型

        Returns:
            str: 默认模型名称
        """
        return self.default_model

    def is_configured(self) -> bool:
        """
        检查是否已正确配置

        Returns:
            bool: 是否已配置
        """
        return self.has_config and self.client is not None

    def validate_api_key(self, api_key: str) -> bool:
        """验证 API 密钥有效性 (使用最小化对话请求)"""
        if not api_key:
            return False

        try:
            # 发送一个极其微小的测试请求
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.default_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            }

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10,
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    # 检查业务状态码 (iFlow 有时在 200 响应里返回业务错误)
                    if (
                        isinstance(data, dict)
                        and data.get("status")
                        and str(data.get("status")) != "200"
                    ):
                        logger.warning(
                            f"iFlow API 业务验证失败: {data.get('msg') or data}"
                        )
                        return False
                    return True
                except Exception:
                    # 如果不是 JSON 或者格式不对，只要是 200 就暂且认为 OK (因为这是最小测试)
                    return True
            else:
                logger.warning(
                    f"iFlow API Key 验证失败, 状态码: {response.status_code}, 响应: {response.text[:100]}"
                )
                return False
        except Exception as e:
            logger.warning(f"iFlow API Key 验证异常: {e}")
            return False

    def check_semantic_similarity(
        self,
        question: str,
        ai_answer: str,
        source_document: str,
        model: Optional[str] = None,
        stream: bool = False,
        show_thinking: bool = False,
        stream_callback: Optional[callable] = None,  # 新增回调参数
    ) -> tuple[str, str]:
        """
        检查语义相似性 (使用 Prompt 模式，不再使用 Tools)

        Args:
            question: 用户问题
            ai_answer: AI回答
            source_document: 源文档内容
            model: 可选的模型名称
            stream: 是否使用流式输出
            show_thinking: 不支持

        Returns:
            tuple[str, str]: (判断结果, 判断依据)
        """
        import json

        if not self.is_configured():
            return "错误", "iFlow API 密钥未配置或无效"

        # 使用指定模型或默认模型
        target_model = model or self.default_model

        # 构建提示词
        prompt = self._build_semantic_prompt(
            question, ai_answer, source_document[:12000]
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
                # 构建请求
                messages = [
                    {
                        "role": "system",
                        "content": "你是一个专业的语义分析专家。请根据提供的源文档内容，判断AI客服的回答在语义上是否与源文档相符，并严格按照 JSON 格式返回结果。",
                    },
                    {"role": "user", "content": prompt},
                ]

                payload = {
                    "model": target_model,
                    "messages": messages,
                    "stream": stream,
                    "temperature": 0.1,
                    "max_tokens": 1000,
                }

                logger.info(f"调用 iFlow API 进行语义分析，模型: {target_model}")

                # 检查客户端是否可用
                if self.client is None:
                    return "错误", "iFlow 客户端未正确初始化"

                # 发送请求
                response = self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=60,
                    stream=stream,
                )

                if stream:
                    # 流式处理（兼容多种 SSE 格式：data:{...} / data: {...} / 纯 JSON 行）
                    # 注意：在并发 Worker UI 模式下，StreamDisplay 可能会干扰 rich.Live 表格
                    # 因此我们优先使用 callback，如果没有 callback 且不在静默模式，才使用 StreamDisplay

                    stream_display = None
                    if not stream_callback:
                        from semantic_tester.ui.terminal_ui import StreamDisplay

                        stream_display = StreamDisplay(
                            title=f"{self.name} ({self.model})"
                        )
                        stream_display.start()

                    full_response = ""
                    try:
                        for line in response.iter_lines():
                            if stop_event.is_set():
                                break

                            if not line:
                                continue

                            raw = line.decode("utf-8").strip()
                            if not raw:
                                continue

                            # 兼容 "data:{...}", "data: {...}" 以及纯 JSON 行
                            if raw.startswith("data:"):
                                data_str = raw[len("data:") :].strip()
                            else:
                                data_str = raw

                            if not data_str or data_str == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                # 可能是心跳包或注释行，直接跳过
                                continue

                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                                    # 如果有回调，优先调用回调更新 UI 表格
                                    if stream_callback:
                                        stream_callback(full_response)
                                    # 否则更新独立的流式显示
                                    elif stream_display:
                                        stream_display.update(content)
                    finally:
                        if stream_display:
                            stream_display.stop()

                    return self._parse_response(full_response)

                else:
                    # 非流式处理
                    stop_event.set()
                    if waiting_thread.is_alive():
                        waiting_thread.join(timeout=0.5)

                    response.raise_for_status()
                    data = response.json()

                    # 检查 iFlow 业务错误 (即使 HTTP 200)
                    if (
                        isinstance(data, dict)
                        and data.get("status")
                        and str(data.get("status")) != "200"
                    ):
                        error_msg = data.get("msg") or f"业务错误: {data.get('status')}"
                        return "错误", f"iFlow 供应商返回错误: {error_msg}"

                    if "choices" in data and len(data["choices"]) > 0:
                        message = data["choices"][0].get("message", {})
                        content = message.get("content", "")
                        if content:
                            return self._parse_response(content)

                        return "错误", "iFlow API 返回空响应"
                    else:
                        return "错误", f"iFlow API 响应格式异常: {data}"

            except Exception as e:
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

                error_msg = str(e)
                # 检测速率限制 (429)
                is_rate_limit = False
                if hasattr(e, "response") and getattr(e, "response", None) is not None:
                    if e.response.status_code == 429:
                        is_rate_limit = True
                elif "429" in error_msg or "rate limit" in error_msg.lower():
                    is_rate_limit = True

                if is_rate_limit:
                    current_key = self.api_keys[self.current_key_index]
                    delay = self._extract_retry_delay(error_msg) or 60
                    self.key_cooldown_until[current_key] = time.time() + delay
                    logger.warning(
                        f"iFlow 达到速率限制，密钥 {self.current_key_index} 进入冷却 ({delay}s)，准备轮转..."
                    )
                    self._rotate_key(force_rotate=True)
                else:
                    logger.error(
                        f"iFlow API 调用异常 (尝试 {attempt + 1}/{max_retries}): {error_msg}"
                    )
                    # 非速率限制错误也尝试轮转密钥以增加成功率
                    self._rotate_key(force_rotate=True)
            finally:
                stop_event.set()
                if waiting_thread.is_alive():
                    waiting_thread.join(timeout=0.5)

            if attempt == max_retries - 1:
                return "错误", f"iFlow API 调用多次重试失败: {error_msg}"

            # 这里的 _rotate_key已经在 except 块中调用了，此处可以根据需要添加额外等待
            time.sleep(1)

        return "错误", "iFlow API 调用多次重试失败"

    def _build_semantic_prompt(
        self, question: str, ai_answer: str, source_document: str
    ) -> str:
        """
        构建语义分析提示词

        Args:
            question: 用户问题
            ai_answer: AI回答
            source_document: 源文档内容

        Returns:
            str: 构建的提示词
        """
        return SEMANTIC_CHECK_PROMPT.format(
            question=question,
            ai_answer=ai_answer,
            source_document=source_document,
        )

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        解析 AI 响应内容 (优先尝试 JSON 解析)

        Args:
            content: AI 响应内容

        Returns:
            tuple[str, str]: (判断结果, 判断依据)
        """
        import json

        content = content.strip()

        # 尝试清理 Markdown 代码块
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content.strip("`")
        content = content.strip()

        # 1. 尝试 JSON 解析
        try:
            data = json.loads(content)
            result = data.get("result", "不确定")
            reason = data.get("reason", "未提供原因")

            # 规范化结果
            if result not in ["是", "否"]:
                if "是" in result:
                    result = "是"
                elif "否" in result:
                    result = "否"
                else:
                    result = "不确定"

            logger.info(f"iFlow JSON 解析成功: {result}")
            return result, reason
        except json.JSONDecodeError:
            pass

        # 2. 回退到文本提取 (兼容旧格式或非 JSON 输出)
        # 尝试提取判断结果
        result, reason = self._extract_result_from_format(content)

        # 备用解析：如果没有找到明确格式，尝试关键词匹配
        if result == "不确定":
            result = self._extract_result_by_keywords(content)

        # 清理判断依据
        reason = self._clean_reason(reason)

        return result, reason

    def _extract_result_from_format(self, content: str) -> tuple[str, str]:
        """
        从格式化内容中提取结果和原因

        Returns:
            tuple[str, str]: (结果, 原因)
        """
        result = "不确定"
        reason = content

        if "判断结果：" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "判断结果：" in line:
                    result_part = line.split("判断结果：")[-1].strip()
                    if result_part in ["是", "否", "不确定"]:
                        result = result_part

                    # 提取判断依据
                    reason = self._extract_reason_from_lines(lines, i, line)
                    break

        return result, reason

    def _extract_reason_from_lines(
        self, lines: list, current_index: int, current_line: str
    ) -> str:
        """
        从行中提取判断依据

        Returns:
            str: 判断依据
        """
        if current_index + 1 < len(lines):
            reason_lines = []
            # 从下一行开始收集判断依据
            for j in range(current_index + 1, len(lines)):
                if lines[j].strip():
                    reason_lines.append(lines[j].strip())

            if reason_lines:
                return "\n".join(reason_lines)

        # 如果没有后续行，使用当前行的剩余部分
        if "判断依据：" in current_line:
            return current_line.split("判断依据：")[-1].strip()

        return ""

    def _extract_result_by_keywords(self, content: str) -> str:
        """
        通过关键词匹配提取结果

        Returns:
            str: 提取的结果
        """
        content_lower = content.lower()

        positive_keywords = ["是", "符合", "一致", "正确", "能够推断"]
        negative_keywords = ["不是", "不符合", "不一致", "错误", "无法推断"]

        has_positive = any(kw in content_lower for kw in positive_keywords)
        has_negative = any(kw in content_lower for kw in negative_keywords)

        if has_positive and not has_negative:
            return "是"
        elif has_negative:
            return "否"

        return "不确定"

    def _clean_reason(self, reason: str) -> str:
        """
        清理判断依据

        Returns:
            str: 清理后的判断依据
        """
        if len(reason) > 500:
            reason = reason[:500] + "..."
        return reason
