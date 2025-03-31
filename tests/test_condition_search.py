import unittest
from src.trading.condition_search import ConditionSearch

class TestConditionSearch(unittest.TestCase):
    def test_load_conditions_and_get_codes(self):
        token = 'dummy_token'
        cs = ConditionSearch(token)
        conditions = { 'stk_cd': '005930' }
        codes = cs.search_conditions(conditions)
        self.assertIsInstance(codes, list)
        self.assertTrue(len(codes) > 0)

if __name__ == '__main__':
    unittest.main()