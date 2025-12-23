"""
配置加载器
从 .env.config 文件中加载所有配置参数

参考 dify_chat_tester 项目设计，适配 semantic_tester 需求
"""

import logging
import os
import sys
from typing import List, Union, Any

logger = logging.getLogger(__name__)


class EnvLoader:
    """环境配置加载器 - 从 .env.config 文件加载配置"""

    def __init__(self, env_file: str = ".env.config"):
        self.env_file = env_file
        self.config: dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        config_file_path = self._get_config_file_path()

        if not os.path.exists(config_file_path):
            logger.warning(
                f"配置文件 '{self.env_file}' 不存在，正在尝试创建默认配置..."
            )
            self._create_default_config_file()

            # 尝试再次加载配置文件
            if os.path.exists(config_file_path):
                logger.info(f"配置文件 '{self.env_file}' 已成功创建并加载")
                self._read_config_file(config_file_path)
            else:
                logger.warning(
                    f"无法创建配置文件 '{self.env_file}'，将使用内置默认配置"
                )
                self._load_defaults()
        else:
            self._read_config_file(config_file_path)

    def _read_config_file(self, config_file_path: str):
        r"""从指定路径读取配置文件

        支持两种形式的配置：
        1. 单行键值：KEY=value
        2. 使用三引号包裹的多行值：KEY=\"\"\"...\"\"\"

        示例::

            SEMANTIC_CHECK_PROMPT=\"\"\"
            这里可以写多行提示词内容
            支持换行，读取时会原样保留
            \"\"\"
        """
        multiline_key: str | None = None
        multiline_buffer: list[str] = []

        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                for line_num, raw_line in enumerate(f, 1):
                    line = raw_line.rstrip("\n")
                    stripped = line.strip()

                    # 多行值收集阶段
                    if multiline_key is not None:
                        # 查找结束标记 """
                        if '"""' in stripped:
                            end_idx = line.find('"""')
                            content_part = line[:end_idx]
                            if content_part:
                                multiline_buffer.append(content_part)
                            # 合并为最终值（保留原始换行）
                            self.config[multiline_key] = "\n".join(multiline_buffer)
                            multiline_key = None
                            multiline_buffer = []
                        else:
                            multiline_buffer.append(line)
                        continue

                    # 跳过空行和注释
                    if not stripped or stripped.startswith("#"):
                        continue

                    if "=" not in line:
                        logger.warning(
                            f"配置文件第 {line_num} 行格式错误(缺少 '='): {line}"
                        )
                        continue

                    key, value = line.split("=", 1)
                    key = key.strip()
                    value_stripped = value.lstrip()

                    # 多行值起始：KEY=""" ...
                    if value_stripped.startswith('"""'):
                        after = value_stripped[3:]
                        # 同一行就结束：KEY="""single line"""
                        if '"""' in after:
                            end_idx = after.find('"""')
                            content = after[:end_idx]
                            self.config[key] = content
                        else:
                            multiline_key = key
                            multiline_buffer = []
                            if after:
                                multiline_buffer.append(after)
                        continue

                    # 普通单行键值
                    self.config[key] = value_stripped.strip()
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            self._load_defaults()

    def _get_config_file_path(self) -> str:
        """获取配置文件的完整路径"""
        # 如果是打包后的程序
        if getattr(sys, "frozen", False):
            # 配置文件在程序所在目录
            return os.path.join(os.path.dirname(sys.executable), self.env_file)
        else:
            # 开发环境，配置文件在项目根目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # env_loader在 semantic_tester/config/ 下，需要再往上一层到项目根目录
            project_dir = os.path.dirname(os.path.dirname(current_dir))
            return os.path.join(project_dir, self.env_file)

    def _create_default_config_file(self):
        """创建默认配置文件"""
        # 获取程序运行目录
        if getattr(sys, "frozen", False):
            # PyInstaller 打包后的程序
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # env_loader在 semantic_tester/config/ 下，需要再往上一层到项目根目录
            base_dir = os.path.dirname(os.path.dirname(current_dir))

        # 尝试从项目目录查找 .env.config.example
        example_file = os.path.join(base_dir, ".env.config.example")

        # 配置文件创建在程序运行目录
        config_file_path = os.path.join(base_dir, self.env_file)

        # 如果 .env.config.example 存在，复制它作为默认配置
        if os.path.exists(example_file):
            try:
                with open(example_file, "r", encoding="utf-8") as src:
                    content = src.read()

                with open(config_file_path, "w", encoding="utf-8") as dst:
                    dst.write(content)

                logger.info(f"已从模板创建配置文件: {config_file_path}")
            except Exception as e:
                logger.error(f"创建配置文件失败: {e}")
        else:
            # 如果找不到模板文件，则基于内置默认配置生成一个简单的配置文件
            logger.warning(
                f"模板文件 {example_file} 不存在，将使用内置默认配置生成 {config_file_path}"
            )
            try:
                # 先加载内置默认配置到 self.config
                self._load_defaults()

                # 写入一个可编辑的基础配置文件
                with open(config_file_path, "w", encoding="utf-8") as dst:
                    dst.write(
                        "# 自动生成的默认配置文件\n"
                        "# 请根据需要修改相关配置项，尤其是各个 API 的密钥\n\n"
                    )
                    for key, value in self.config.items():
                        dst.write(f"{key}={value}\n")

                logger.info(f"已基于内置默认配置创建配置文件: {config_file_path}")
            except Exception as e:
                logger.error(f"基于默认配置创建配置文件失败: {e}")

    def _load_defaults(self):
        """加载默认配置"""
        logger.info("使用内置默认配置")
        self.config = {
            "WAITING_INDICATORS": "⣾,⣽,⣻,⢿,⡿,⣟,⣯,⣷",
            "WAITING_TEXT": "正在处理",
            "WAITING_DELAY": "0.1",
            "LOG_LEVEL": "INFO",
            "OUTPUT_EXCEL_FILE_NAME": "semantic_test_results.xlsx",
            "API_TIMEOUT": "60",
            "API_RETRY_COUNT": "5",
            "API_RETRY_DELAY": "60",
            "USE_FULL_DOC_MATCH": "false",
            "ENABLE_THINKING": "true",  # 默认开启思维链
        }

    # 配置获取方法
    def get_str(self, key: str, default: str = "") -> str:
        """获取字符串配置"""
        return self.config.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(self.config.get(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"配置 {key} 不是有效整数，使用默认值 {default}")
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return float(self.config.get(key, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"配置 {key} 不是有效浮点数，使用默认值 {default}")
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = self.config.get(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def get_list(
        self, key: str, default: Union[List[str], None] = None, separator: str = ","
    ) -> List[str]:
        """获取列表配置"""
        if default is None:
            default = []

        value = self.config.get(key, "")
        if not value:
            return default

        return [item.strip() for item in value.split(separator) if item.strip()]

    def has_config(self, key: str) -> bool:
        """检查是否存在某个配置"""
        return key in self.config and self.config[key].strip() != ""

    def print_config_status(self):
        """打印配置状态"""
        print("\n=== 配置文件状态 ===")
        print(f"配置文件: {self.env_file}")
        print(f"配置项数量: {len(self.config)}")
        print(f"日志级别: {self.get_str('LOG_LEVEL', 'INFO')}")


# 全局配置加载器实例
_env_loader = None


def get_env_loader() -> EnvLoader:
    """获取全局配置加载器实例"""
    global _env_loader
    if _env_loader is None:
        _env_loader = EnvLoader()
    return _env_loader


def reload_config():
    """重新加载配置"""
    global _env_loader
    _env_loader = EnvLoader()
    logger.info("配置已重新加载")
