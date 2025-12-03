"""
应用程序设置

管理应用程序的配置设置。
"""

import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """应用程序设置数据类"""

    default_knowledge_base_dir: str = ""
    default_output_dir: str = ""
    auto_save_interval: int = 10  # 每处理多少条记录自动保存一次
    max_retries: int = 5  # API 调用最大重试次数
    default_retry_delay: int = 60  # 默认重试延迟（秒）
    log_level: str = "INFO"
    show_comparison_result: bool = False  # 是否在控制台显示比对结果
    auto_detect_format: bool = True  # 是否自动检测文件格式

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Settings":
        """从字典创建设置"""
        return cls(**data)


class Config:
    """配置管理器"""

    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.settings = self._load_settings()

    def _load_settings(self) -> Settings:
        """
        加载设置

        Returns:
            Settings: 设置对象
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    settings = Settings.from_dict(data)
                    logger.info(f"成功加载配置文件: {self.config_file}")
                    return settings
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认设置")
        else:
            logger.info("配置文件不存在，使用默认设置")

        return Settings()

    def save_settings(self) -> bool:
        """
        保存设置

        Returns:
            bool: 是否保存成功
        """
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def get_setting(self, key: str) -> Optional[Any]:
        """
        获取设置值

        Args:
            key: 设置键名

        Returns:
            设置值，如果不存在则返回 None
        """
        return getattr(self.settings, key, None)

    def set_setting(self, key: str, value) -> bool:
        """
        设置配置值

        Args:
            key: 设置键名
            value: 设置值

        Returns:
            bool: 是否设置成功
        """
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            return True
        else:
            logger.warning(f"未知的设置项: {key}")
            return False

    def reset_to_defaults(self):
        """重置为默认设置"""
        self.settings = Settings()
        logger.info("配置已重置为默认值")

    def print_settings(self):
        """打印当前设置"""
        print("\n=== 当前配置设置 ===")
        settings_dict = self.settings.to_dict()
        for key, value in settings_dict.items():
            if isinstance(value, bool):
                display_value = "是" if value else "否"
            elif value == "":
                display_value = "未设置"
            else:
                display_value = str(value)
            print(f"{key}: {display_value}")

    def update_from_user_input(self, key: str, prompt: str) -> bool:
        """
        从用户输入更新设置

        Args:
            key: 设置键名
            prompt: 输入提示

        Returns:
            bool: 是否更新成功
        """
        if not hasattr(self.settings, key):
            logger.warning(f"未知的设置项: {key}")
            return False

        current_value = getattr(self.settings, key)
        current_display = (
            "是"
            if current_value
            else "否"
            if isinstance(current_value, bool)
            else str(current_value)
        )

        user_input = input(f"{prompt} (当前: {current_display}): ").strip()

        if not user_input:
            return False  # 用户没有输入，保持原值

        # 根据设置类型转换输入值
        try:
            new_value: Any = None
            if isinstance(current_value, bool):
                new_value = user_input.lower() in ["y", "yes", "是", "true", "1"]
            elif isinstance(current_value, int):
                new_value = int(user_input)
            elif isinstance(current_value, str):
                new_value = user_input
            else:
                new_value = user_input

            setattr(self.settings, key, new_value)
            logger.info(f"设置 {key} 已更新为: {new_value}")
            return True

        except ValueError as e:
            logger.error(f"设置值格式错误: {e}")
            return False

    def get_default_output_path(self, input_path: str) -> str:
        """
        获取默认输出路径

        Args:
            input_path: 输入文件路径

        Returns:
            str: 默认输出路径
        """
        base_name = os.path.splitext(input_path)[0]
        return f"{base_name}_评估结果.xlsx"

    def ensure_output_dir(self, output_path: str):
        """
        确保输出目录存在

        Args:
            output_path: 输出文件路径
        """
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录: {output_dir}")

    @property
    def auto_save_interval(self) -> int:
        """获取自动保存间隔"""
        return self.settings.auto_save_interval

    @property
    def max_retries(self) -> int:
        """获取最大重试次数"""
        return self.settings.max_retries

    @property
    def default_retry_delay(self) -> int:
        """获取默认重试延迟"""
        return self.settings.default_retry_delay

    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self.settings.log_level
