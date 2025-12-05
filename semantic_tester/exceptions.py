"""
统一异常处理模块

定义项目中使用的异常层次结构，提供清晰的错误分类和友好的错误信息。
"""


class SemanticTesterError(Exception):
    """基础异常类 - 所有项目异常的父类"""

    def __init__(self, message: str = "", details: str = ""):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class ProviderError(SemanticTesterError):
    """AI 供应商相关错误"""

    pass


class ConfigError(SemanticTesterError):
    """配置相关错误"""

    pass


class DocumentError(SemanticTesterError):
    """文档处理相关错误"""

    pass


class ExcelError(SemanticTesterError):
    """Excel 处理相关错误"""

    pass


class NetworkError(SemanticTesterError):
    """网络相关错误"""

    pass


class AuthenticationError(ProviderError):
    """认证/API密钥错误"""

    pass


class RateLimitError(ProviderError):
    """速率限制错误"""

    pass


def friendly_error_message(error_msg: str, status_code: int | None = None) -> str:
    """将底层错误信息转换为用户友好的中文提示

    Args:
        error_msg: 原始错误信息
        status_code: HTTP 状态码（可选）

    Returns:
        str: 用户友好的错误提示
    """
    # HTTP 状态码优先
    if status_code is not None:
        if status_code in (401, 403):
            return "认证失败：API 密钥无效或权限不足，请检查配置。"
        if status_code == 429:
            return "请求过于频繁，已触发频率限制，请稍后重试。"
        if 500 <= status_code <= 599:
            return f"服务端错误（HTTP {status_code}），请稍后重试。"

    # 常见网络错误关键字
    lowered = error_msg.lower()
    net_keywords = [
        "failed to establish a new connection",
        "name or service not known",
        "connection refused",
        "timeout",
        "timed out",
    ]
    if any(k in lowered for k in net_keywords):
        return "无法连接到 API 服务器，请检查网络连接和配置。"

    ssl_keywords = ["ssl", "certificate_verify_failed"]
    if any(k in lowered for k in ssl_keywords):
        return "SSL 证书错误，请检查 API 地址是否正确。"

    # 默认返回原始信息
    return error_msg
