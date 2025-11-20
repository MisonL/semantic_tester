"""
iFlow AI 供应商实现

基于 dify_chat_tester 项目的 iFlow 渠道实现
适配 semantic_tester 的语义分析接口

作者：Mison
邮箱：1360962086@qq.com
"""

import logging
import requests
from typing import Dict, List, Optional, Any

from semantic_tester.api.base_provider import AIProvider

logger = logging.getLogger(__name__)


class IflowProvider(AIProvider):
    """iFlow AI 供应商实现"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 iFlow 供应商

        Args:
            config: 配置字典，包含 api_key, base_url 等信息
        """
        super().__init__(config)

        self.name = config.get("name", "iFlow")
        self.id = config.get("id", "iflow")
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://apis.iflow.cn/v1")
        self.has_config = config.get("has_config", bool(self.api_key))
        self.default_model = config.get("model", "qwen3-max")

        # iFlow 支持的模型列表
        self.available_models = config.get(
            "models", ["qwen3-max", "kimi-k2-0905", "glm-4.6", "deepseek-v3.2"]
        )

        # 内部状态
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化客户端"""
        # iFlow 使用 requests 直接调用，不需要特殊客户端
        if self.has_config and self.api_key:
            self.client = requests.Session()
            self.client.headers.update(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
            logger.info("iFlow 客户端初始化成功")
        else:
            logger.warning("iFlow API 密钥未配置，跳过客户端初始化")

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
        """验证 API 密钥有效性"""
        if not api_key:
            return False

        try:
            # 发送一个简单的测试请求
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"iFlow API Key 验证失败: {e}")
            return False

    def check_semantic_similarity(
        self,
        question: str,
        ai_answer: str,
        source_document: str,
        model: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        检查语义相似性

        Args:
            question: 用户问题
            ai_answer: AI回答
            source_document: 源文档内容
            model: 可选的模型名称

        Returns:
            tuple[str, str]: (判断结果, 判断依据)
        """
        if not self.is_configured():
            return "错误", "iFlow API 密钥未配置或无效"

        # 使用指定模型或默认模型
        target_model = model or self.default_model

        # 构建提示词
        prompt = self._build_semantic_prompt(question, ai_answer, source_document)

        try:
            # 构建请求
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的语义分析专家。请根据提供的源文档内容，判断AI客服的回答在语义上是否与源文档相符。",
                },
                {"role": "user", "content": prompt},
            ]

            payload = {
                "model": target_model,
                "messages": messages,
                "stream": False,
                "temperature": 0.3,  # 较低温度确保一致性
                "max_tokens": 1000,
            }

            logger.info(f"调用 iFlow API 进行语义分析，模型: {target_model}")

            # 检查客户端是否可用
            if self.client is None:
                return "错误", "iFlow 客户端未正确初始化"

            # 发送请求
            response = self.client.post(
                f"{self.base_url}/chat/completions", json=payload, timeout=60
            )
            response.raise_for_status()

            # 解析响应
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
                if content:
                    # 解析响应内容
                    result, reason = self._parse_response(content)
                    logger.info(f"iFlow 语义分析完成: {result}")
                    return result, reason
                else:
                    return "错误", "iFlow API 返回空响应"
            else:
                return "错误", f"iFlow API 响应格式异常: {data}"

        except requests.exceptions.Timeout:
            error_msg = "iFlow API 请求超时"
            logger.error(error_msg)
            return "错误", error_msg
        except requests.exceptions.HTTPError as e:
            error_msg = (
                f"iFlow API HTTP错误: {e.response.status_code} - {e.response.text}"
            )
            logger.error(error_msg)
            return "错误", error_msg
        except Exception as e:
            error_msg = f"iFlow API 调用异常: {str(e)}"
            logger.error(error_msg)
            return "错误", error_msg

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
        return f"""请根据以下源文档内容，评估AI客服回答的语义相符性：

**源文档内容：**
{source_document[:3000]}  # 限制长度避免超出token限制

**用户问题：**
{question}

**AI客服回答：**
{ai_answer}

**评估要求：**
1. 判断AI回答是否能够从源文档中合理推断
2. 检查AI回答是否与源文档的核心信息一致
3. 考虑回答的准确性和完整性

**请按以下格式回复：**
判断结果：是/否/不确定
判断依据：[详细说明判断理由，引用具体的文档内容]"""

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        解析 AI 响应内容

        Args:
            content: AI 响应内容

        Returns:
            tuple[str, str]: (判断结果, 判断依据)
        """
        content = content.strip()

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
    
    def _extract_reason_from_lines(self, lines: list, current_index: int, current_line: str) -> str:
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
