import json
import os
import tempfile

from semantic_tester.config.settings import Settings, Config


def test_settings_to_from_dict_roundtrip():
    data = {
        "default_knowledge_base_dir": "/kb",
        "default_output_dir": "/out",
        "auto_save_interval": 5,
        "max_retries": 3,
        "default_retry_delay": 30,
        "log_level": "DEBUG",
        "show_comparison_result": True,
        "auto_detect_format": False,
    }
    s = Settings.from_dict(data)
    assert s.to_dict() == data


def test_config_load_save_and_get_set_reset_print(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")

        # 初始时文件不存在，应使用默认设置
        cfg = Config(config_file=cfg_path)
        assert isinstance(cfg.settings, Settings)

        # 修改部分设置并保存
        cfg.set_setting("auto_save_interval", 7)
        cfg.set_setting("log_level", "WARNING")
        assert cfg.save_settings() is True

        # 重新加载，确认持久化
        cfg2 = Config(config_file=cfg_path)
        assert cfg2.settings.auto_save_interval == 7
        assert cfg2.settings.log_level == "WARNING"

        # get_setting / reset_to_defaults
        assert cfg2.get_setting("auto_save_interval") == 7
        assert cfg2.get_setting("unknown_key") is None

        cfg2.reset_to_defaults()
        assert cfg2.settings.auto_save_interval == Settings().auto_save_interval

        # print_settings 只需确保输出包含关键字段
        cfg2.print_settings()
        out, _ = capsys.readouterr()
        assert "auto_save_interval" in out

        # update_from_user_input：模拟输入
        monkeypatch.setattr("builtins.input", lambda prompt="": "20")
        updated = cfg2.update_from_user_input("auto_save_interval", "设置间隔")
        assert updated is True
        assert cfg2.settings.auto_save_interval == 20

        # 非法 key
        updated = cfg2.update_from_user_input("not_exists", "提示")
        assert updated is False

        # get_default_output_path / ensure_output_dir
        out_path = cfg2.get_default_output_path(os.path.join(tmpdir, "a.xlsx"))
        assert out_path.endswith("_评估结果.xlsx")

        nested_out = os.path.join(tmpdir, "sub", "b.xlsx")
        cfg2.ensure_output_dir(nested_out)
        assert os.path.isdir(os.path.join(tmpdir, "sub"))

        # 属性访问器
        assert isinstance(cfg2.auto_save_interval, int)
        assert isinstance(cfg2.max_retries, int)
        assert isinstance(cfg2.default_retry_delay, int)
        assert isinstance(cfg2.log_level, str)


def test_config_load_invalid_json_uses_defaults(tmp_path, caplog):
    cfg_path = tmp_path / "bad.json"
    # 写入无效 JSON 内容，触发 _load_settings 的异常分支
    cfg_path.write_text("{invalid", encoding="utf-8")

    with caplog.at_level("WARNING"):
        cfg = Config(config_file=str(cfg_path))

    assert isinstance(cfg.settings, Settings)
    # 即使日志格式变更，这里只要产生 warning 级别日志即可
    assert any(record.levelname == "WARNING" for record in caplog.records)


def test_config_save_settings_failure(monkeypatch, tmp_path, caplog):
    cfg_path = tmp_path / "config.json"
    cfg = Config(config_file=str(cfg_path))

    # 模拟 open 抛出异常，触发 save_settings 的错误分支
    def _boom(*args, **kwargs):  # pragma: no cover - 简单异常抛出
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", _boom)

    with caplog.at_level("ERROR"):
        ok = cfg.save_settings()

    assert ok is False
    assert any("保存配置文件失败" in record.getMessage() for record in caplog.records)


def test_update_from_user_input_edge_cases(monkeypatch, tmp_path, caplog):
    cfg_path = tmp_path / "config.json"
    cfg = Config(config_file=str(cfg_path))

    # 空输入：应返回 False 且不修改值
    orig_interval = cfg.settings.auto_save_interval
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    updated = cfg.update_from_user_input("auto_save_interval", "设置间隔")
    assert updated is False
    assert cfg.settings.auto_save_interval == orig_interval

    # 布尔类型：y / n 映射
    cfg.settings.show_comparison_result = False
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    updated = cfg.update_from_user_input("show_comparison_result", "是否显示")
    assert updated is True
    assert cfg.settings.show_comparison_result is True

    # 非法整数输入：触发异常分支并返回 False
    cfg.settings.auto_save_interval = 10
    monkeypatch.setattr("builtins.input", lambda prompt="": "not-int")
    with caplog.at_level("ERROR"):
        updated = cfg.update_from_user_input("auto_save_interval", "设置间隔")
    assert updated is False
    assert cfg.settings.auto_save_interval == 10
    assert any("设置值格式错误" in record.getMessage() for record in caplog.records)
