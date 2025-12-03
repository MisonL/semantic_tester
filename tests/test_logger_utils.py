import logging
import os
import tempfile

from semantic_tester.utils.logger_utils import (
    LoggerUtils,
    ProgressLogger,
    ColoredFormatter,
)


def test_get_log_directory_and_setup_logging_and_get_logger(tmp_path, monkeypatch):
    # 强制在当前工作目录下创建日志目录
    monkeypatch.chdir(tmp_path)

    log_dir = LoggerUtils._get_log_directory("logs")
    assert os.path.isdir(log_dir)

    LoggerUtils.setup_logging(log_level="DEBUG", log_dir="logs", log_file="test.log")
    logger = LoggerUtils.get_logger("test")
    logger.debug("debug message")

    # set_log_level 只需确保不会抛异常
    LoggerUtils.set_log_level("INFO")


def test_console_and_temp_levels_and_silence_restore(capsys):
    LoggerUtils.console_print("hello", level="SUCCESS")
    out, _ = capsys.readouterr()
    assert "hello" in out

    root = logging.getLogger()
    LoggerUtils.set_temp_log_level("WARNING")
    assert root.level == logging.WARNING

    LoggerUtils.set_temp_log_level("ERROR", target_handlers=list(root.handlers))
    # handler level 调整由实现负责，这里只需不抛错

    LoggerUtils.silence_console_temporarily()
    LoggerUtils.restore_console_level()


def test_startup_banner_and_provider_summary_and_simple_menu(capsys, monkeypatch):
    # 避免 rich 真正输出复杂格式，只验证不会抛异常
    LoggerUtils.print_startup_banner()

    LoggerUtils.print_provider_summary({"total": 2, "configured": 1, "current": "gemini"})
    LoggerUtils.print_simple_menu()
    out, _ = capsys.readouterr()
    assert "AI供应商状态" in out
    assert "请选择操作" in out


def test_log_system_and_package_info():
    LoggerUtils.log_system_info()
    LoggerUtils.log_package_info()  # 即使部分包缺失也应该不会抛出异常


def test_progress_logger_and_colored_formatter(capsys):
    pl = ProgressLogger(total_items=3, description="测试进度")
    pl.update(increment=1, message="step1")
    pl.finish("done")

    # ColoredFormatter 应该为 levelname 添加颜色码
    fmt = ColoredFormatter("%(levelname)s: %(message)s")
    record = logging.LogRecord(
        name="x",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="msg",
        args=(),
        exc_info=None,
    )
    formatted = fmt.format(record)
    assert "msg" in formatted
