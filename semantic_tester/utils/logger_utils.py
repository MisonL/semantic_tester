"""
日志工具

提供日志配置和管理的工具函数。
"""

import logging
import os
import sys
from typing import List, Optional


class LoggerUtils:
    """日志工具类"""

    @staticmethod
    def _get_log_directory(log_dir: str) -> str:
        """
        获取日志目录路径，优先使用程序所在目录，否则使用用户主目录

        Args:
            log_dir: 日志目录名称

        Returns:
            str: 日志目录的绝对路径
        """
        # 尝试获取程序所在目录
        if getattr(sys, "frozen", False):
            # 打包后的程序
            app_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            app_dir = os.getcwd()

        # 首选：程序所在目录的logs文件夹
        preferred_log_dir = os.path.join(app_dir, log_dir)

        # 测试是否有写入权限
        try:
            os.makedirs(preferred_log_dir, exist_ok=True)
            # 尝试写入测试文件
            test_file = os.path.join(preferred_log_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return preferred_log_dir
        except (OSError, PermissionError):
            # 如果没有写入权限，使用用户主目录
            home_dir = os.path.expanduser("~")
            fallback_log_dir = os.path.join(home_dir, ".semantic_tester", log_dir)
            os.makedirs(fallback_log_dir, exist_ok=True)
            return fallback_log_dir

    @staticmethod
    def setup_logging(
        log_level: str = "INFO",
        log_dir: str = "logs",
        log_file: str = "semantic_test.log",
        quiet_console: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,  # 保留5个备份文件
    ):
        """
        设置日志配置

        Args:
            log_level: 日志级别
            log_dir: 日志目录名称（相对路径）
            log_file: 日志文件名
            quiet_console: 是否静默控制台输出（只显示重要信息）
            max_bytes: 单个日志文件最大字节数（默认10MB）
            backup_count: 保留的备份文件数量（默认5个）
        """
        # 获取日志目录（智能选择）
        actual_log_dir = LoggerUtils._get_log_directory(log_dir)

        # 配置日志格式
        # 文件使用详细格式，控制台使用简洁格式
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")

        # 清除现有的处理器
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 设置日志级别
        level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(level)

        # 文件处理器 - 使用RotatingFileHandler实现日志轮转
        from logging.handlers import RotatingFileHandler

        log_file_path = os.path.join(actual_log_dir, log_file)
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)

        # 控制台处理器 - 简洁输出
        if quiet_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            # 控制台只显示WARNING及以上级别的信息，避免冗余输出
            console_handler.setLevel(logging.WARNING)
            root_logger.addHandler(console_handler)
        else:
            # 详细控制台输出（调试模式）
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(file_formatter)
            console_handler.setLevel(level)
            root_logger.addHandler(console_handler)

        # 记录日志系统初始化信息
        logging.info(
            f"日志系统已初始化：目录={actual_log_dir}, 级别={log_level}, 最大={max_bytes/1024/1024:.1f}MB, 备份={backup_count}"
        )

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        获取指定名称的日志器

        Args:
            name: 日志器名称

        Returns:
            logging.Logger: 日志器实例
        """
        return logging.getLogger(name)

    @staticmethod
    def set_log_level(level: str):
        """
        设置日志级别

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)
        # 只在文件中记录，不在控制台显示
        file_logger = logging.FileHandler("logs/semantic_test.log", encoding="utf-8")
        file_logger.emit(
            logging.LogRecord(
                name="root",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"日志级别已设置为: {level}",
                args=(),
                exc_info=None,
            )
        )

    @staticmethod
    def console_print(message: str, level: str = "INFO"):
        """
        在控制台打印重要信息，绕过日志系统

        Args:
            message: 要显示的消息
            level: 消息级别 (INFO, SUCCESS, WARNING, ERROR)
        """
        colors = {
            "INFO": "\033[37m",  # 白色
            "SUCCESS": "\033[92m",  # 绿色
            "WARNING": "\033[93m",  # 黄色
            "ERROR": "\033[91m",  # 红色
            "RESET": "\033[0m",  # 重置
        }

        color = colors.get(level, colors["INFO"])
        reset = colors["RESET"]
        print(f"{color}{message}{reset}")

    @staticmethod
    def set_temp_log_level(
        level: str, target_handlers: Optional[List[logging.Handler]] = None
    ):
        """
        临时设置日志级别，用于静默某些操作

        Args:
            level: 日志级别
            target_handlers: 目标处理器列表，None表示所有处理器
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        root_logger = logging.getLogger()

        if target_handlers is None:
            # 设置根日志器级别
            root_logger.setLevel(log_level)
        else:
            # 设置特定处理器的级别
            for handler in root_logger.handlers:
                if handler in target_handlers:
                    handler.setLevel(log_level)

    @staticmethod
    def silence_console_temporarily():
        """临时静默控制台输出"""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                # 临时将控制台处理器级别设为CRITICAL+1，完全静默
                handler.setLevel(logging.CRITICAL + 10)

    @staticmethod
    def restore_console_level():
        """恢复控制台输出级别"""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                # 恢复控制台处理器为WARNING级别
                handler.setLevel(logging.WARNING)

    @staticmethod
    def print_startup_banner():
        """打印启动信息（标题和应用信息合并显示）"""
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box
        from semantic_tester import __version__, __author__, __email__, __license__

        console = Console()

        # 创建信息文本
        info_text = Text()
        # info_text.append("\n")  # 移除空行分隔
        info_text.append("版本: ", style="bold yellow")
        info_text.append(f"{__version__}\n", style="bright_cyan")
        info_text.append("作者: ", style="bold yellow")
        info_text.append(f"{__author__}\n", style="white")
        info_text.append("许可证: ", style="bold yellow")
        info_text.append(f"{__license__}\n", style="white")
        info_text.append("邮箱: ", style="bold yellow")
        info_text.append(f"{__email__}\n", style="cyan")
        info_text.append("项目: ", style="bold yellow")
        info_text.append(
            "https://github.com/MisonL/semantic_tester\n", style="bright_cyan underline"
        )

        # 组合内容
        from rich.console import Group

        panel_content = Group(info_text)

        # 创建面板
        panel = Panel(
            panel_content,
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(0, 1),
            width=55,
            expand=False,
        )

        console.print()
        console.print(panel)
        console.print()

    @staticmethod
    def print_app_info():
        """打印应用信息（已废弃，功能合并到 print_startup_banner）"""
        # 保持方法存在以兼容性，但不做任何事情
        pass

    @staticmethod
    def print_provider_summary(providers_info: dict):
        """
        打印供应商状态摘要

        Args:
            providers_info: 供应商信息字典
        """
        total = providers_info.get("total", 0)
        configured = providers_info.get("configured", 0)
        current = providers_info.get("current", "无")

        print(f"📊 AI供应商状态: {configured}/{total} 已配置 | 当前: {current}")
        print()

    @staticmethod
    def print_simple_menu():
        """打印简洁的主菜单"""
        print("🎯 请选择操作:")
        print("   1. 开始新的语义分析")
        print("   2. 查看使用说明")
        print("   3. AI供应商管理")
        print("   4. 退出程序")
        print()

    @staticmethod
    def log_system_info():
        """记录系统信息"""
        import platform
        import sys

        logging.info("=== 系统信息 ===")
        logging.info(f"操作系统: {platform.system()} {platform.release()}")
        logging.info(f"Python 版本: {sys.version}")
        logging.info(f"Python 可执行文件: {sys.executable}")

    @staticmethod
    def log_package_info():
        """记录关键包版本信息"""
        try:
            import pandas
            import google
            import openpyxl

            logging.info("=== 包版本信息 ===")
            logging.info(f"pandas: {pandas.__version__}")

            # 尝试获取 Google 包版本信息
            try:
                google_version = getattr(google, "__version__", "unknown")
                logging.info(f"google-generativeai: {google_version}")
            except AttributeError:
                logging.info("google-generativeai: version unavailable")

            logging.info(f"openpyxl: {openpyxl.__version__}")
        except ImportError as e:
            logging.warning(f"无法获取包版本信息: {e}")

    @staticmethod
    def create_progress_logger(
        total_items: int, description: str = "处理进度"
    ) -> "ProgressLogger":
        """
        创建进度日志器

        Args:
            total_items: 总项目数
            description: 描述信息

        Returns:
            ProgressLogger: 进度日志器实例
        """
        return ProgressLogger(total_items, description)


class ProgressLogger:
    """进度日志器"""

    def __init__(self, total_items: int, description: str = "处理进度"):
        """
        初始化进度日志器

        Args:
            total_items: 总项目数
            description: 描述信息
        """
        self.total_items = total_items
        self.description = description
        self.current_item = 0
        self.logger = logging.getLogger(__name__)

    def update(self, increment: int = 1, message: str = ""):
        """
        更新进度

        Args:
            increment: 增量
            message: 附加消息
        """
        self.current_item += increment
        percentage = (self.current_item / self.total_items) * 100

        msg = f"{self.description}: {self.current_item}/{self.total_items} ({percentage:.1f}%)"
        if message:
            msg += f" - {message}"

        self.logger.info(msg)

    def finish(self, message: str = "完成"):
        """
        完成进度记录

        Args:
            message: 完成消息
        """
        self.logger.info(
            f"{self.description}: {self.total_items}/{self.total_items} (100.0%) - {message}"
        )


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record):
        """格式化日志记录"""
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )

        return super().format(record)
