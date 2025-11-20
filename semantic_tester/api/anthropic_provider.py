"""
Anthropic API 供应商实现

支持 Anthropic Claude API 及其兼容接口。
"""

import logging
import time
from typing import Any, Dict, List, Optional

try:
    from anthropic.types import TextBlock
except ImportError:
    TextBlock = None

from .base_provider import AIProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    """Anthropic AI 供应商实现"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Anthropic 供应商

        Args:
            config: 供应商配置字典
        """
        super().__init__(config)
        self.name = config.get("name", "Anthropic")
        self.id = config.get("id", "anthropic")
        self.api_keys = config.get("api_keys", [])
        self.base_url = config.get("base_url", "https://api.anthropic.com")
        self.has_config = config.get("has_config", len(self.api_keys) > 0)
        self.default_model = config.get("model", "claude-sonnet-4-20250514")
        self.timeout = config.get("timeout", 60)
        self.retry_count = config.get("retry_count", 3)
        self.retry_delay = config.get("retry_delay", 1)

        # 内部状态
        self.client = None
        self.current_key_index = 0
        self.key_last_used_time: Dict[str, float] = {}
        self.key_cooldown_until: Dict[str, float] = {}
        self.first_actual_call = True

        # 批量处理配置
        self.batch_config = config.get("batch", {})

        # 初始化可用密钥和客户端
        self._initialize_api_keys()
        self._configure_client()

    def get_models(self) -> List[str]:
        """
        获取可用的模型列表

        Returns:
            List[str]: 模型名称列表
        """
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]

    def validate_api_key(self, api_key: str) -> bool:
        """
        验证API密钥有效性

        Args:
            api_key: API密钥

        Returns:
            bool: 密钥是否有效
        """
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key, timeout=5)
            # 发送简单的测试请求
            if hasattr(client, 'messages') and hasattr(client.messages, 'create'):
                client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Hi"}],
                )
            return True
        except Exception:
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
            question: 问题内容
            ai_answer: AI回答内容
            source_document: 源文档内容
            model: 使用的模型（可选）

        Returns:
            tuple[str, str]: (结果, 原因)，结果为"是"/"否"/"错误"
        """
        result = self.analyze_semantic(question, ai_answer, source_document)
        if result["success"]:
            is_consistent = "是" if result["is_consistent"] else "否"
            return is_consistent, result["reason"]
        else:
            return "错误", result.get("error", "未知错误")

    def is_configured(self) -> bool:
        """
        检查供应商是否已配置

        Returns:
            bool: 是否已配置
        """
        return len(self.api_keys) > 0 and self.client is not None

    def get_provider_info(self) -> Dict[str, Any]:
        """
        获取供应商信息

        Returns:
            Dict[str, Any]: 供应商信息
        """
        return {
            "name": self.name,
            "id": self.id,
            "type": "anthropic",
            "configured": self.is_configured(),
            "model": self.default_model,
            "base_url": self.base_url,
            "features": ["语义分析", "文本生成"],
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接

        Returns:
            Dict[str, Any]: 测试结果
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "供应商未配置或API密钥无效",
                "error_type": "configuration_error",
            }

        try:
            import anthropic

            # 获取当前API密钥
            current_api_key = (
                self.api_keys[self.current_key_index] if self.api_keys else ""
            )

            client = anthropic.Anthropic(
                api_key=current_api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )

            # 发送简单的测试请求
            if hasattr(client, 'messages') and hasattr(client.messages, 'create'):
                client.messages.create(
                    model=self.default_model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}],
                )

            return {
                "success": True,
                "response_time": 0.5,  # 简化的响应时间
                "model": self.default_model,
            }

        except ImportError:
            return {
                "success": False,
                "error": "未安装 anthropic 库，请运行: uv add anthropic",
                "error_type": "missing_dependency",
            }
        except Exception as e:
            logger.error(f"Anthropic 连接测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "api_error",
            }

    def analyze_semantic(
        self, question: str, answer: str, knowledge: str
    ) -> Dict[str, Any]:
        """
        执行语义分析

        Args:
            question: 用户问题
            answer: AI回答
            knowledge: 知识库文档内容

        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Anthropic API 未配置",
                "is_consistent": False,
                "confidence": 0.0,
                "reason": "供应商未配置",
            }

        try:
            import anthropic

            # 获取当前API密钥
            current_api_key = (
                self.api_keys[self.current_key_index] if self.api_keys else ""
            )

            client = anthropic.Anthropic(
                api_key=current_api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )

            # 构建分析提示
            prompt = self._build_analysis_prompt(question, answer, knowledge)

            # 调用 API
            start_time = time.time()
            if hasattr(client, 'messages') and hasattr(client.messages, 'create'):
                response = client.messages.create(
                    model=self.default_model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )
            else:
                raise Exception("客户端未正确初始化")
            response_time = time.time() - start_time

            # 解析响应 - 提取文本内容块
            text_content = ""
            if hasattr(response, 'content'):
                for content_block in response.content:
                    # 使用类型检查而不是hasattr，避免Pylance类型错误
                    if TextBlock is not None and isinstance(content_block, TextBlock):
                        text_content += content_block.text

            if not text_content:
                return {
                    "success": False,
                    "error": "响应中未找到文本内容",
                    "is_consistent": False,
                    "confidence": 0.0,
                    "reason": "API返回响应不包含可解析的文本内容",
                }

            result = self._parse_response(text_content)
            result["response_time"] = response_time
            result["model"] = self.default_model

            return result

        except ImportError:
            logger.error("未安装 anthropic 库")
            return {
                "success": False,
                "error": "未安装 anthropic 库，请运行: uv add anthropic",
                "is_consistent": False,
                "confidence": 0.0,
                "reason": "缺少依赖",
            }
        except Exception as e:
            logger.error(f"Anthropic 语义分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "is_consistent": False,
                "confidence": 0.0,
                "reason": f"API调用失败: {str(e)}",
            }

    def _build_analysis_prompt(self, question: str, answer: str, knowledge: str) -> str:
        """
        构建分析提示

        Args:
            question: 用户问题
            answer: AI回答
            knowledge: 知识库文档内容

        Returns:
            str: 分析提示
        """
        return f"""请分析以下AI客服回答是否与源知识库文档内容语义相符。

**用户问题：**
{question}

**AI客服回答：**
{answer}

**源知识库文档内容：**
{knowledge}

**分析要求：**
1. 判断AI客服回答是否与源文档内容语义相符
2. 给出判断依据和置信度（0-100%）
3. 指出回答中与文档不符或缺失的关键信息

**输出格式：**
判断结果：【是/否】
置信度：【0-100%】
判断依据：【详细说明判断理由】
不符点：【如果有不符，列出具体问题；如果没有，写"无不符点"】"""

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析 API 响应

        Args:
            response_text: API 响应文本

        Returns:
            Dict[str, Any]: 解析结果
        """
        try:
            # 默认值
            is_consistent = False
            confidence = 0.0
            reason = "解析失败"

            # 解析判断结果
            if "判断结果：【是】" in response_text:
                is_consistent = True
            elif "判断结果：【否】" in response_text:
                is_consistent = False

            # 解析置信度
            import re

            confidence_match = re.search(r"置信度：【(\d+)%】", response_text)
            if confidence_match:
                confidence = float(confidence_match.group(1)) / 100

            # 提取判断依据
            reason_start = response_text.find("判断依据：")
            if reason_start != -1:
                reason_end = response_text.find("不符点：")
                if reason_end != -1:
                    reason = response_text[reason_start:reason_end].strip()
                else:
                    reason = response_text[reason_start:].strip()

            return {
                "success": True,
                "is_consistent": is_consistent,
                "confidence": confidence,
                "reason": reason,
                "raw_response": response_text,
            }

        except Exception as e:
            logger.error(f"解析 Anthropic 响应失败: {e}")
            return {
                "success": False,
                "error": f"响应解析失败: {str(e)}",
                "is_consistent": False,
                "confidence": 0.0,
                "reason": "响应解析失败",
                "raw_response": response_text,
            }

    def _initialize_api_keys(self):
        """测试并初始化可用的 API 密钥列表"""
        logger.info("开始测试 Anthropic API Key 的有效性...")
        valid_keys = []
        current_time = time.time()

        for key in self.api_keys:
            if self.validate_api_key(key):
                valid_keys.append(key)
                self.key_last_used_time[key] = current_time
                self.key_cooldown_until[key] = 0.0

        self.api_keys = valid_keys
        if not self.api_keys:
            logger.warning("所有提供的 Anthropic API Key 均无效或未设置")
        else:
            logger.info(f"成功识别 {len(self.api_keys)} 个有效 Anthropic API Key")

    def _configure_client(self):
        """配置 Anthropic 客户端"""
        if not self.api_keys:
            self.client = None
            return

        if self.api_keys:
            current_api_key = self.api_keys[self.current_key_index]
            try:
                import anthropic
                self.client = anthropic.Anthropic(
                    api_key=current_api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
                logger.info(f"Anthropic API 已配置，使用密钥索引: {self.current_key_index}")
                self.key_last_used_time[current_api_key] = time.time()
            except Exception as e:
                logger.error(f"Anthropic API 配置失败: {e}")
                self.client = None
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

    def batch_analyze(self, items: list, progress_callback=None) -> list:
        """
        批量语义分析

        Args:
            items: 待分析的项目列表
            progress_callback: 进度回调函数

        Returns:
            list: 分析结果列表
        """
        results = []
        total = len(items)

        for i, item in enumerate(items, 1):
            try:
                result = self.analyze_semantic(
                    item["question"], item["answer"], item["knowledge"]
                )
                result["row_number"] = item.get("row_number", i)
                results.append(result)

                # 调用进度回调
                if progress_callback:
                    progress_callback(i, total, result)

                # 批量处理间隔
                if i < total:
                    time.sleep(self.batch_config.get("request_interval", 1.0))

            except Exception as e:
                logger.error(f"批量分析第 {i} 项失败: {e}")
                error_result = {
                    "success": False,
                    "error": str(e),
                    "is_consistent": False,
                    "confidence": 0.0,
                    "reason": f"处理失败: {str(e)}",
                    "row_number": item.get("row_number", i),
                }
                results.append(error_result)

        return results
