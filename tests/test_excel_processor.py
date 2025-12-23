import os
import tempfile

import pandas as pd

from semantic_tester.excel.processor import ExcelProcessor


def _create_dify_like_excel(path: str) -> None:
    """Create a minimal Dify Chat Tester like Excel file for testing."""
    df = pd.DataFrame(
        {
            "时间戳": ["2025-01-01 00:00:00"],
            "原始问题": ["今天天气怎么样？"],
            "Dify响应": ["今天天气很好。"],
            "是否成功": ["是"],
        }
    )
    df.to_excel(path, index=False)


def test_excel_processor_dify_format_end_to_end():
    """Exercise主要非交互路径：加载->检测格式->自动映射->读写结果->断点续传。"""

    with tempfile.TemporaryDirectory() as tmpdir:
        excel_path = os.path.join(tmpdir, "dify.xlsx")
        _create_dify_like_excel(excel_path)

        processor = ExcelProcessor(excel_path)

        # 基础信息
        assert processor.validate_file_exists() is True
        assert processor.get_total_records() == 0

        # 加载 Excel
        assert processor.load_excel() is True
        assert processor.get_total_records() == 1
        assert "原始问题" in processor.column_names

        # 检测格式，应识别为 Dify 格式
        fmt = processor.detect_format()
        assert fmt["is_dify_format"] is True
        assert fmt["question_col"] == "原始问题"
        assert fmt["response_cols"] == ["Dify响应"]

        # 显示格式信息（主要是打印，不抛异常即可）
        processor.display_format_info()

        # 自动添加文档名称列
        processor.auto_add_document_column()
        assert "文档名称" in processor.column_names

        # 自动列映射
        column_mapping = processor.get_user_column_mapping(auto_config=True)
        assert set(column_mapping.keys()) == {
            "doc_name_col_index",
            "question_col_index",
            "ai_answer_col_index",
        }

        # 结果列配置（自动模式）
        result_columns = processor.get_result_columns(auto_config=True)
        assert set(result_columns.keys()) == {"similarity_result", "reason"}

        # 设置结果列 dtype
        processor.setup_result_columns(result_columns)

        # 读取行数据
        row_data = processor.get_row_data(0, column_mapping)
        assert row_data["question"] == "今天天气怎么样？"
        assert row_data["ai_answer"] == "今天天气很好。"

        # 写入结果并检查 has_result / get_result
        processor.save_result(0, "是", "回答与文档一致", result_columns)
        assert processor.has_result(0, result_columns) is True

        sim_col_name = result_columns["similarity_result"][0]
        assert processor.get_result(0, sim_col_name) == "是"

        # 保存中间结果和最终结果
        intermediate_path = os.path.join(tmpdir, "intermediate.xlsx")
        final_path = os.path.join(tmpdir, "final.xlsx")

        processor.save_intermediate_results(intermediate_path, processed_count=1)
        assert os.path.exists(intermediate_path)

        processor.save_final_results(final_path)
        assert os.path.exists(final_path)

        # 断点续传：从已有结果文件加载结果
        processor2 = ExcelProcessor(excel_path)
        assert processor2.load_excel() is True
        processor2.detect_format()
        processor2.auto_add_document_column()
        column_mapping2 = processor2.get_user_column_mapping(auto_config=True)
        result_columns2 = processor2.get_result_columns(auto_config=True)

        loaded = processor2.load_existing_results(final_path, result_columns2)
        assert loaded == 1
        assert processor2.has_result(0, result_columns2) is True

        # get_result 在第二个处理器上同样可用
        sim_col_name2 = result_columns2["similarity_result"][0]
        assert processor2.get_result(0, sim_col_name2) == "是"
