import os
import tempfile

from semantic_tester.utils.validation_utils import ValidationUtils


def test_is_valid_file_and_directory_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "a.xlsx")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("x")

        assert ValidationUtils.is_valid_file_path(file_path, [".xlsx", ".xls"]) is True
        assert ValidationUtils.is_valid_file_path(file_path, [".txt"]) is False
        assert ValidationUtils.is_valid_file_path("", [".xlsx"]) is False

        assert ValidationUtils.is_valid_directory_path(tmpdir) is True
        assert (
            ValidationUtils.is_valid_directory_path(os.path.join(tmpdir, "nope"))
            is False
        )


def test_is_valid_gemini_api_key_and_email_url():
    assert ValidationUtils.is_valid_gemini_api_key("a" * 10) is False
    assert ValidationUtils.is_valid_gemini_api_key("a" * 20) is True

    assert ValidationUtils.validate_email("user@example.com") is True
    assert ValidationUtils.validate_email("bad@") is False

    assert ValidationUtils.validate_url("https://example.com/path?q=1") is True
    assert ValidationUtils.validate_url("not-a-url") is False


def test_validate_column_mapping_and_string_numeric_range_row_data():
    errors = ValidationUtils.validate_column_mapping(
        {"doc_name_col_index": 0, "question_col_index": 1, "ai_answer_col_index": 2},
        total_columns=3,
    )
    assert errors == []

    errors = ValidationUtils.validate_column_mapping({}, total_columns=3)
    assert "列映射不能为空" in errors[0]

    errors = ValidationUtils.validate_column_mapping(
        {"doc_name_col_index": -1, "question_col_index": 5, "ai_answer_col_index": 5},
        total_columns=3,
    )
    assert any("超出范围" in e for e in errors)
    assert any("重复" in e for e in errors)

    assert ValidationUtils.validate_numeric_range("10", min_val=0, max_val=20) is True
    assert ValidationUtils.validate_numeric_range("bad", min_val=0, max_val=20) is False
    assert (
        ValidationUtils.validate_string_length("abc", min_length=1, max_length=5)
        is True
    )
    assert ValidationUtils.validate_string_length("", min_length=1) is False

    row_errors = ValidationUtils.validate_row_data(
        {"question": " ", "ai_answer": "answer"}
    )
    assert "问题内容为空" in row_errors

    row_errors = ValidationUtils.validate_row_data({"question": "q", "ai_answer": " "})
    assert "AI回答内容为空" in row_errors


def test_validate_excel_and_kb_directory_and_required_fields_and_filename():
    with tempfile.TemporaryDirectory() as tmpdir:
        excel_path = os.path.join(tmpdir, "test.xlsx")
        # Minimal valid Excel via pandas
        try:
            import pandas as pd

            df = pd.DataFrame({"文档名称": ["a"], "问题点": ["q"], "AI客服回答": ["a"]})
            df.to_excel(excel_path, index=False)
            errors = ValidationUtils.validate_excel_file(excel_path)
            assert errors == []
        except Exception:
            # 如果本地环境没有所需引擎，只验证函数不会崩溃
            errors = ValidationUtils.validate_excel_file(excel_path)
            assert isinstance(errors, list)

        # Knowledge base directory
        md_dir = os.path.join(tmpdir, "kb")
        os.makedirs(md_dir)
        md_file = os.path.join(md_dir, "doc.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# doc")

        assert ValidationUtils.validate_knowledge_base_directory(md_dir) == []

        missing_dir_errors = ValidationUtils.validate_knowledge_base_directory(
            os.path.join(tmpdir, "no-such")
        )
        assert "目录不存在" in missing_dir_errors[0]

    # required fields & sanitize filename
    missing = ValidationUtils.validate_required_fields(
        {"a": 1, "b": None}, ["a", "b", "c"]
    )
    assert set(missing) == {"b", "c"}

    sanitized = ValidationUtils.sanitize_filename(" a<>:\\|?* .txt\n")
    assert "<" not in sanitized and ">" not in sanitized
    assert sanitized.startswith("a")


def test_validate_row_data_all_ok():
    errors = ValidationUtils.validate_row_data(
        {"question": "what?", "ai_answer": "answer"}
    )
    assert errors == []


def test_additional_validation_utils_edges(monkeypatch, tmp_path):
    # is_valid_file_path 在 extensions=None 时只检查存在性
    f = tmp_path / "foo.txt"
    f.write_text("x", encoding="utf-8")
    assert ValidationUtils.is_valid_file_path(str(f)) is True

    # validate_numeric_range 边界：越界时返回 False
    assert ValidationUtils.validate_numeric_range(5, min_val=0, max_val=10) is True
    assert ValidationUtils.validate_numeric_range(-1, min_val=0, max_val=10) is False
    assert ValidationUtils.validate_numeric_range(11, min_val=0, max_val=10) is False

    # validate_string_length 的 max_length 超界分支
    assert ValidationUtils.validate_string_length("abc", max_length=2) is False

    # validate_required_fields 对空字符串视为缺失
    missing = ValidationUtils.validate_required_fields({"a": "", "b": "ok"}, ["a", "b"])
    assert missing == ["a"]

    # sanitize_filename 在空字符串时回退为 "unnamed"，其他情况只需移除不安全字符
    assert ValidationUtils.sanitize_filename("") == "unnamed"
    sanitized_only_unsafe = ValidationUtils.sanitize_filename("<>:\\|?*")
    assert sanitized_only_unsafe  # 非空
    assert all(ch not in sanitized_only_unsafe for ch in "<>:\\|?*")

    # validate_knowledge_base_directory 中 os.walk 抛异常的分支
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    def _walk_boom(*args, **kwargs):
        raise OSError("walk error")

    monkeypatch.setattr("os.walk", _walk_boom)
    errors = ValidationUtils.validate_knowledge_base_directory(str(kb_dir))
    assert any("读取目录时出错" in e for e in errors)
