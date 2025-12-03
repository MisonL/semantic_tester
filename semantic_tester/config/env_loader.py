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
        """从指定路径读取配置文件"""
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        self.config[key.strip()] = value.strip()
                    else:
                        logger.warning(f"配置文件第 {line_num} 行格式错误: {line}")
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
            logger.warning(f"模板文件 {example_file} 不存在，无法创建默认配置")

    def _load_defaults(self):
        """加载默认配置"""
        logger.info("使用内置默认配置")
        self.config = {
            "AI_PROVIDERS": "1:Gemini:gemini;2:OpenAI兼容接口:openai;3:Anthropic兼容接口:anthropic;4:Dify:dify;5:iFlow:iflow",
            "GEMINI_MODEL": "gemini-2.5-flash",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
            "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
            "DIFY_BASE_URL": "https://api.dify.ai/v1",
            "BATCH_REQUEST_INTERVAL": "1.0",
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

    def get_ai_providers(self) -> List[dict]:
        """获取AI供应商配置"""
        providers_str = self.get_str("AI_PROVIDERS", "1:Gemini:gemini")
        providers: list[dict[str, Any]] = []

        if not providers_str:
            return providers

        try:
            for provider_str in providers_str.split(";"):
                if not provider_str.strip():
                    continue
                parts = provider_str.strip().split(":")
                if len(parts) >= 3:
                    providers.append(
                        {"index": int(parts[0]), "name": parts[1], "id": parts[2]}
                    )
        except (ValueError, IndexError) as e:
            logger.error(f"解析AI供应商配置失败: {e}")
            # 返回默认的Gemini供应商
            providers = [{"index": 1, "name": "Gemini", "id": "gemini"}]

        return providers

    def has_config(self, key: str) -> bool:
        """检查是否存在某个配置"""
        return key in self.config and self.config[key].strip() != ""

    def print_config_status(self):
        """打印配置状态"""
        print("\n=== 配置文件状态 ===")
        print(f"配置文件: {self.env_file}")
        print(f"配置项数量: {len(self.config)}")

        # 显示关键配置状态（不显示敏感信息）
        ai_providers = self.get_ai_providers()
        print(f"AI供应商: {', '.join([p['name'] for p in ai_providers])}")

        # 支持 GEMINI_API_KEY / GEMINI_API_KEYS 两种命名
        gemini_keys = self.get_list("GEMINI_API_KEY") or self.get_list(
            "GEMINI_API_KEYS"
        )
        print(
            f"Gemini API密钥: {'已配置' if gemini_keys else '未配置'} ({len(gemini_keys)} 个)"
        )

        print(
            f"OpenAI API密钥: {'已配置' if self.has_config('OPENAI_API_KEY') else '未配置'}"
        )
        print(
            f"Dify API密钥: {'已配置' if self.has_config('DIFY_API_KEY') else '未配置'}"
        )
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
