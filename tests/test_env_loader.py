import os
import sys

from semantic_tester.config import env_loader as env_mod
from semantic_tester.config.env_loader import EnvLoader


def _make_loader(config: dict) -> EnvLoader:
    # 绕过 __init__，避免真实读写 .env.config
    loader = EnvLoader.__new__(EnvLoader)  # type: ignore[arg-type]
    loader.env_file = "dummy.env"
    loader.config = config
    return loader


def test_env_loader_basic_getters_and_defaults():
    loader = _make_loader(
        {
            "STR": "value",
            "INT_OK": "10",
            "INT_BAD": "not-int",
            "FLOAT_OK": "1.5",
            "FLOAT_BAD": "nan!",
            "BOOL_TRUE": "true",
            "BOOL_FALSE": "off",
            "LIST": "a, b, , c",
        }
    )

    assert loader.get_str("STR", "x") == "value"
    assert loader.get_str("MISSING", "x") == "x"

    assert loader.get_int("INT_OK", 5) == 10
    assert loader.get_int("INT_BAD", 5) == 5

    assert loader.get_float("FLOAT_OK", 2.0) == 1.5
    assert loader.get_float("FLOAT_BAD", 2.0) == 2.0

    assert loader.get_bool("BOOL_TRUE", False) is True
    assert loader.get_bool("BOOL_FALSE", True) is False

    lst = loader.get_list("LIST")
    assert lst == ["a", "b", "c"]


def test_env_loader_ai_providers_and_has_config_and_defaults():
    loader = _make_loader(
        {
            "AI_PROVIDERS": "1:Gemini:gemini;2:OpenAI:openai;3::bad",  # 第3个无效
            "OPENAI_API_KEY": "sk-test",
            "LOG_LEVEL": "DEBUG",
        }
    )

    providers = loader.get_ai_providers()
    # 当前实现会保留解析成功的三段式配置，即使名称为空也不会过滤
    ids = [p["id"] for p in providers]
    assert "gemini" in ids and "openai" in ids

    assert loader.has_config("OPENAI_API_KEY") is True
    assert loader.has_config("MISSING") is False

    # _load_defaults 只需保证可执行并填充一些默认值
    loader._load_defaults()
    assert "GEMINI_MODEL" in loader.config


def test_env_loader_print_config_status(capsys):
    loader = _make_loader(
        {
            "AI_PROVIDERS": "1:Gemini:gemini",
            "GEMINI_API_KEY": "key1,key2",
            "LOG_LEVEL": "INFO",
        }
    )

    loader.print_config_status()
    out, err = capsys.readouterr()
    assert "配置文件状态" in out
    assert "Gemini" in out


def test_read_config_file_parses_key_values_and_skips_bad_lines(tmp_path):
    env_path = tmp_path / ".env.config"
    env_path.write_text(
        "KEY=value\n# comment\nBADLINE\nOTHER=two\n",
        encoding="utf-8",
    )

    loader = _make_loader({})
    loader._read_config_file(str(env_path))

    assert loader.config["KEY"] == "value"
    assert loader.config["OTHER"] == "two"


def test_read_config_file_error_uses_defaults(monkeypatch, tmp_path):
    loader = _make_loader({})

    def bad_open(*args, **kwargs):  # type: ignore[unused-argument]
        raise OSError("boom")

    # patch 内置 open，使 _read_config_file 在尝试读取文件时抛出异常
    monkeypatch.setattr("builtins.open", bad_open)
    loader._read_config_file(str(tmp_path / "missing.env"))

    assert "GEMINI_MODEL" in loader.config


def test_get_config_file_path_handles_frozen_and_non_frozen(monkeypatch, tmp_path):
    loader = _make_loader({})

    # 非打包模式下至少返回包含文件名的路径
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    path_normal = loader._get_config_file_path()
    assert loader.env_file in os.path.basename(path_normal)

    # 打包模式下应基于 sys.executable 所在目录
    fake_exe = tmp_path / "app.exe"
    fake_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)
    path_frozen = loader._get_config_file_path()
    assert os.path.dirname(path_frozen) == str(tmp_path)
    assert os.path.basename(path_frozen) == loader.env_file


def test_create_default_config_file_from_template(tmp_path, monkeypatch):
    loader = _make_loader({})

    # 使用打包模式分支，使配置文件创建在 tmpdir 中
    fake_exe = tmp_path / "app.exe"
    fake_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)

    example_file = tmp_path / ".env.config.example"
    example_file.write_text("FOO=bar\n", encoding="utf-8")

    loader._create_default_config_file()

    config_path = tmp_path / loader.env_file
    assert config_path.exists()
    content = config_path.read_text(encoding="utf-8")
    assert "FOO=bar" in content


def test_create_default_config_file_without_template_uses_defaults(tmp_path, monkeypatch):
    loader = _make_loader({})

    # 同样使用打包模式分支，但不创建模板文件，触发默认配置写入路径
    fake_exe = tmp_path / "app.exe"
    fake_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)

    loader._create_default_config_file()

    config_path = tmp_path / loader.env_file
    assert config_path.exists()
    content = config_path.read_text(encoding="utf-8")
    # 内置默认配置中的一个关键字段
    assert "GEMINI_MODEL" in content


def test_get_env_loader_and_reload_config_singleton(monkeypatch):
    # 确保全局实例从头开始
    env_mod._env_loader = None

    def fake_load(self):  # type: ignore[unused-argument]
        self.config = {"K": "v1"}

    # 避免真实文件系统操作
    monkeypatch.setattr(EnvLoader, "load_config", fake_load, raising=False)

    first = env_mod.get_env_loader()
    assert isinstance(first, EnvLoader)
    assert first.config == {"K": "v1"}

    def fake_load2(self):  # type: ignore[unused-argument]
        self.config = {"K": "v2"}

    monkeypatch.setattr(EnvLoader, "load_config", fake_load2, raising=False)
    env_mod.reload_config()

    second = env_mod.get_env_loader()
    assert second is env_mod._env_loader
    assert second.config == {"K": "v2"}
