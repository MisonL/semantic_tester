"""
Excel 工具函数

提供 Excel 单元格操作的工具函数。
"""

import logging
from typing import List

import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.cell import MergedCell

logger = logging.getLogger(__name__)


def write_cell_safely(worksheet: Worksheet, row: int, col: int, value: str):
    """
    安全地写入 Excel 单元格，处理合并单元格的情况。
    如果目标单元格是合并单元格的一部分，则写入合并区域的左上角单元格。

    Args:
        worksheet: Excel 工作表对象
        row: 行号（从1开始）
        col: 列号（从1开始）
        value: 要写入的值
    """
    cell_obj = worksheet.cell(row=row, column=col)
    if isinstance(cell_obj, MergedCell):
        # 如果是合并单元格的一部分，找到其合并区域的左上角单元格
        for merged_range in worksheet.merged_cells.ranges:
            if cell_obj.coordinate in merged_range:
                min_col, min_row, max_col, max_row = merged_range.bounds
                worksheet.cell(row=min_row, column=min_col).value = value  # type: ignore
                return
    else:
        cell_obj.value = value


def get_column_index(column_names: List[str], col_input: str) -> int:
    """
    获取列索引。

    Args:
        column_names: 列名列表
        col_input: 用户输入的列标识（序号或列名）

    Returns:
        int: 列索引（从0开始），如果无效则返回 -1
    """
    try:
        col_num = int(col_input)
        if 1 <= col_num <= len(column_names):
            return col_num - 1
        else:
            return -1  # 无效序号
    except ValueError:
        try:
            return column_names.index(col_input)
        except ValueError:
            return -1  # 未找到列名


def get_or_add_column(df: pd.DataFrame, column_names: List[str], col_input: str) -> int:
    """
    获取或新增列的索引。

    Args:
        df: pandas DataFrame 对象
        column_names: 列名列表
        col_input: 用户输入的列标识（序号或列名）

    Returns:
        int: 列索引（从0开始）
    """
    try:
        col_num = int(col_input)
        if 1 <= col_num <= len(column_names):
            return col_num - 1
        else:
            # 如果是无效序号，但用户可能想新增一个名为数字的列
            new_col_name = col_input
            df[new_col_name] = pd.Series(dtype="object")
            column_names.append(new_col_name)
            logger.info(f"已新增列: '{new_col_name}'")
            return len(column_names) - 1
    except ValueError:
        if col_input in column_names:
            return column_names.index(col_input)
        else:
            # 新增列
            df[col_input] = pd.Series(dtype="object")
            column_names.append(col_input)
            logger.info(f"已新增列: '{col_input}'")
            return len(column_names) - 1
