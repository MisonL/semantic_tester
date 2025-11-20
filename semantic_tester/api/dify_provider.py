"""
Dify AI 供应商实现

参考 dify_chat_tester 项目设计，适配 semantic_tester 语义分析需求
"""

import logging
import time
from typing import List, Optional, Dict, Any

import requests

from .base_provider import AIProvider, APIError, AuthenticationError, RateLimitError

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

        # 确保 base_url 以 /v1 结尾
        if not self.base_url.endswith("/v1"):
            if self.base_url.endswith("/"):
                self.base_url = self.base_url.rstrip("/") + "/v1"
            else:
                self.base_url += "/v1"

        # 初始化可用密钥
        self._initialize_api_keys()

        logger.info(f"Dify 供应商初始化完成: {self.base_url}")

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

            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Dify API 密钥验证成功")
                return True
            elif response.status_code == 401:
                logger.warning("Dify API 密钥无效")
                return False
            else:
                logger.warning(f"Dify API 密钥验证失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Dify API 密钥验证异常: {e}")
            return False

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
            question: 用户问题
            ai_answer: AI回答
            source_document: 源文档内容
            model: 模型名称（Dify不使用此参数）

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

        try:
            # 发送请求到 Dify API
            response = self._send_dify_request(prompt)

            # 处理响应
            return self._process_dify_response(response)

        except (AuthenticationError, RateLimitError, APIError) as e:
            raise e
        except Exception as e:
            error_msg = f"Dify API 调用异常: {str(e)}"
            logger.error(error_msg)
            return "错误", error_msg

    def _send_dify_request(self, prompt: str) -> requests.Response:
        """
        发送请求到Dify API

        Args:
            prompt: 提示词

        Returns:
            requests.Response: API响应

        Raises:
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            APIError: API错误
            requests.exceptions.Timeout: 请求超时
            requests.exceptions.ConnectionError: 连接失败
        """
        # 构建请求
        url = f"{self.base_url}/chat-messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": {},
            "query": prompt,
            "response_mode": "blocking",
            "user": "semantic_tester",
        }

        if self.app_id:
            payload["app_id"] = self.app_id

        logger.debug(f"发送 Dify API 请求，提示词长度: {len(prompt)} 字符")

        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        end_time = time.time()

        logger.debug(f"Dify API 响应时间: {end_time - start_time:.2f} 秒")

        return response

    def _process_dify_response(self, response: requests.Response) -> tuple[str, str]:
        """
        处理Dify API响应

        Args:
            response: API响应

        Returns:
            tuple[str, str]: (结果, 判断依据)

        Raises:
            AuthenticationError: 认证失败
            RateLimitError: 速率限制
            APIError: API错误
        """
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
            error_msg = f"Dify API 请求失败，状态码: {status_code}, 响应: {response.text}"
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
            error_msg = "Dify API 返回空回答"
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

        prompt = f"""请判断以下AI客服回答与源知识库文档内容在语义上是否相符。

用户问题：
{question}

AI客服回答：
{ai_answer}

源知识库文档：
{source_document}

请按照以下格式回答：
判断结果：是/否
判断依据：[详细说明判断理由，重点分析AI回答是否准确反映了源文档的内容，是否存在信息偏差或错误]

要求：
1. 严格基于源文档内容进行判断
2. 如果AI回答与源文档内容一致或基本一致，回答"是"
3. 如果AI回答与源文档内容有明显矛盾、偏差或错误信息，回答"否"
4. 判断依据要具体、准确，引用源文档中的相关内容
5. 重点考察语义的准确性，而不是文字的完全匹配"""

        return prompt

    def _parse_semantic_result(self, response: str) -> tuple[str, str]:
        """
        解析语义分析结果

        Args:
            response: Dify API 返回的回答

        Returns:
            tuple[str, str]: (结果, 判断依据)
        """
        try:
            # 尝试提取判断结果和判断依据
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
