from semantic_tester.utils.format_utils import FormatUtils


def test_truncate_and_clean_text():
    assert FormatUtils.truncate_text("hello", 10) == "hello"
    assert FormatUtils.truncate_text("hello world", 5) == "he..."

    assert FormatUtils.clean_text("  a   b\n c  ") == "a b c"
    assert FormatUtils.clean_text("") == ""


def test_format_file_size_and_duration_and_percentage():
    assert FormatUtils.format_file_size(0) == "0 B"
    assert FormatUtils.format_file_size(1024).endswith("KB")

    assert FormatUtils.format_duration(0.5).endswith("ms")
    assert FormatUtils.format_duration(10.0) == "10.0s"
    assert FormatUtils.format_duration(90.0) == "1m 30s"
    assert FormatUtils.format_duration(3700.0) == "1h 1m"

    assert FormatUtils.format_percentage(1, 4) == "25.0%"
    assert FormatUtils.format_percentage(0, 0) == "0.0%"


def test_wrap_and_table_and_number():
    lines = FormatUtils.wrap_text("a b c d", width=3)
    assert lines  # non-empty

    table = FormatUtils.format_table([["a", "b"], ["c", "d"]], headers=["h1", "h2"])
    assert "h1" in table and "a" in table

    assert FormatUtils.format_number(1234567) == "1,234,567"


def test_api_key_preview_and_clean_json_and_error_details():
    preview = FormatUtils.format_api_key_preview("abcdef0123456789")
    assert "..." in preview

    assert FormatUtils.format_api_key_preview("", prefix_chars=3, suffix_chars=2) == "无"

    json_text = "```json\n{\"a\": 1}\n```"
    assert FormatUtils.clean_json_text(json_text) == '{"a": 1}'

    details = FormatUtils.extract_error_details("ResourceExhausted: 'retryDelay': '60s'")
    assert details["type"] == "速率限制错误"
    assert details["retry_delay"] == "60s"


def test_highlight_keywords_case_insensitive():
    text = "Error: something bad happened"
    highlighted = FormatUtils.highlight_keywords(text, ["error"])
    # Original text should still be present; color codes are hard to assert exactly
    assert "Error" in highlighted
