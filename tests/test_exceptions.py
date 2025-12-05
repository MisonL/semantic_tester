"""异常模块的单元测试"""

import pytest

from semantic_tester.exceptions import (
    AuthenticationError,
    ConfigError,
    DocumentError,
    ExcelError,
    NetworkError,
    ProviderError,
    RateLimitError,
    SemanticTesterError,
    friendly_error_message,
)


class TestExceptions:
    """测试异常类"""

    def test_base_exception(self):
        """测试基础异常"""
        exc = SemanticTesterError("测试错误")
        assert str(exc) == "测试错误"
        assert exc.message == "测试错误"

    def test_exception_with_details(self):
        """测试带详情的异常"""
        exc = SemanticTesterError("错误消息", details="详细信息")
        assert str(exc) == "错误消息 - 详细信息"

    def test_provider_error(self):
        """测试供应商异常"""
        exc = ProviderError("供应商错误")
        assert isinstance(exc, SemanticTesterError)

    def test_config_error(self):
        """测试配置异常"""
        exc = ConfigError("配置错误")
        assert isinstance(exc, SemanticTesterError)

    def test_document_error(self):
        """测试文档处理异常"""
        exc = DocumentError("文档错误")
        assert isinstance(exc, SemanticTesterError)

    def test_excel_error(self):
        """测试 Excel 异常"""
        exc = ExcelError("Excel 错误")
        assert isinstance(exc, SemanticTesterError)

    def test_authentication_error(self):
        """测试认证异常"""
        exc = AuthenticationError("认证失败")
        assert isinstance(exc, ProviderError)

    def test_rate_limit_error(self):
        """测试速率限制异常"""
        exc = RateLimitError("速率限制")
        assert isinstance(exc, ProviderError)


class TestFriendlyErrorMessage:
    """测试友好错误消息转换"""

    def test_auth_error_401(self):
        """测试 401 认证错误"""
        msg = friendly_error_message("Error", status_code=401)
        assert "认证失败" in msg

    def test_rate_limit_error_429(self):
        """测试 429 速率限制"""
        msg = friendly_error_message("Error", status_code=429)
        assert "频率限制" in msg

    def test_server_error_500(self):
        """测试服务端错误"""
        msg = friendly_error_message("Error", status_code=500)
        assert "服务端错误" in msg

    def test_network_error_timeout(self):
        """测试超时错误"""
        msg = friendly_error_message("read timed out")
        assert "无法连接" in msg

    def test_ssl_error(self):
        """测试 SSL 错误"""
        msg = friendly_error_message("ssl certificate_verify_failed")
        assert "SSL" in msg

    def test_unknown_error_passthrough(self):
        """测试未知错误原样返回"""
        msg = friendly_error_message("未知错误消息")
        assert msg == "未知错误消息"
