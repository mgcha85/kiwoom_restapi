import unittest
from trading.trade_executor import TradeExecutor

class TestOrderExecution(unittest.TestCase):
    def test_order_execution_and_db_save(self):
        token = 'dummy_token'
        executor = TradeExecutor(token)
        try:
            executor.execute_trades()
        except Exception as e:
            self.fail(f'execute_trades() raised an Exception: {e}')

if __name__ == '__main__':
    unittest.main()