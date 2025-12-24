
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from semantic_tester.excel.processor import ExcelProcessor

class TestOptionalColumns(unittest.TestCase):
    def setUp(self):
        self.processor = ExcelProcessor("dummy_path.xlsx")
        self.processor.df = pd.DataFrame({
            "Question": ["Q1", "Q2"],
            "Answer": ["A1", "A2"]
        })
        self.processor.column_names = ["Question", "Answer"]
        self.processor.format_info = {"question_col": "Question", "response_cols": ["Answer"]}
        # Mock logic that would normally be in utils to prevent actual dependency issues in this unit test if possible,
        # but here we rely on the project structure.

    @patch('builtins.input', side_effect=['']) 
    def test_get_column_index_optional_skip(self, mock_input):
        # Test skipping optional input
        idx = self.processor._get_column_index_by_input("DocName", "Prompt", optional=True)
        self.assertEqual(idx, -1)

    @patch('builtins.input', side_effect=['1']) 
    def test_get_column_index_optional_provide(self, mock_input):
        idx = self.processor._get_column_index_by_input("Question", "Prompt", optional=True)
        self.assertEqual(idx, 0)

    @patch('builtins.input', side_effect=['', '1', '2'])
    def test_manual_configure_columns_skip_doc_name(self, mock_input):
        # inputs: 
        # 1. Doc Name -> skip ('')
        # 2. Question -> 1
        # 3. Answer -> 2
        
        mapping = self.processor._manual_configure_columns()
        self.assertEqual(mapping['doc_name_col_index'], -1)
        self.assertEqual(mapping['question_col_index'], 0)
        self.assertEqual(mapping['ai_answer_col_index'], 1)



    def test_get_row_data_unknown_doc(self):
        mapping = {
            "doc_name_col_index": -1,
            "question_col_index": 0,
            "ai_answer_col_index": 1
        }
        # Row 0
        data = self.processor.get_row_data(0, mapping)
        self.assertEqual(data['doc_name'], "未知文档")
        self.assertEqual(data['question'], "Q1")
        self.assertEqual(data['ai_answer'], "A1")

if __name__ == '__main__':
    unittest.main()
