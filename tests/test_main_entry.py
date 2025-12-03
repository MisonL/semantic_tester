import importlib
import runpy
import sys
import types


def test_semantic_tester_main_importable():
    """确保 semantic_tester.__main__ 可被导入且暴露 main 函数。

    不直接执行 main()，避免真正运行 CLI 逻辑，只验证入口结构正确。
    """

    mod = importlib.import_module("semantic_tester.__main__")
    assert hasattr(mod, "main")


def test_semantic_tester_main_runs_when_module_as_script():
    """执行 semantic_tester.__main__ 作为脚本时，应调用 main()。"""

    called = {"flag": False}

    stub = types.ModuleType("main")

    def fake_main():  # type: ignore[unused-argument]
        called["flag"] = True

    stub.main = fake_main  # type: ignore[attr-defined]
    sys.modules["main"] = stub

    # 以 __main__ 方式运行模块，触发 if __name__ == "__main__" 分支
    runpy.run_module("semantic_tester.__main__", run_name="__main__")

    assert called["flag"] is True
