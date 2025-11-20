"""
API 模块 - 处理各种API接口调用
"""

from .gemini_handler import GeminiAPIHandler, check_semantic_similarity

__all__ = ["GeminiAPIHandler", "check_semantic_similarity"]
