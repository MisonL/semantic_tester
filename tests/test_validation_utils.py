
import unittest
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from semantic_tester.utils.validation_utils import ValidationUtils

class TestValidationUtils(unittest.TestCase):
    def test_validate_row_data_empty_ai_answer(self):
        row_data = {
            "question": "Valid Question",
            "ai_answer": "", # Empty answer
            "doc_name": "test.md"
        }
        # This should return errors now as we reverted the loose validation
        errors = ValidationUtils.validate_row_data(row_data)
        self.assertIn("AI回答内容为空", errors, f"Expected error for empty AI answer, but got: {errors}")

    def test_validate_row_data_valid(self):
        row_data = {
            "question": "Valid Question",
            "ai_answer": "Valid Answer",
            "doc_name": "test.md"
        }
        errors = ValidationUtils.validate_row_data(row_data)
        self.assertEqual(errors, [])

    def test_validate_row_data_empty_question(self):
        row_data = {
            "question": "",
            "ai_answer": "Valid Answer",
            "doc_name": "test.md"
        }
        errors = ValidationUtils.validate_row_data(row_data)
        self.assertIn("问题内容为空", errors)

if __name__ == '__main__':
    unittest.main()
