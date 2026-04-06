import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from arbitrage_engine import ArbitrageEngine

class TestArbitrageEngine(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.engine = ArbitrageEngine(llm_provider=self.mock_llm, initial_capital=10000.0)

    def test_get_current_price(self):
        price = self.engine.get_current_price("BTC")
        self.assertTrue(50000 < price < 70000)

    def test_market_sentiment_positive(self):
        self.mock_llm.call.return_value = "0.8"
        sentiment = self.engine.get_market_sentiment("AAPL")
        self.assertAlmostEqual(sentiment, 0.8)

    def test_market_sentiment_negative(self):
        self.mock_llm.call.return_value = "-0.7"
        sentiment = self.engine.get_market_sentiment("AAPL")
        self.assertAlmostEqual(sentiment, -0.7)

    @patch.object(ArbitrageEngine, 'get_current_price', return_value=100.0)
    def test_execute_trade_buy_success(self, mock_price):
        success = self.engine.execute_trade("BUY", "AAPL", 1000.0)
        self.assertTrue(success)
        self.assertAlmostEqual(self.engine.capital, 9000.0)
        self.assertAlmostEqual(self.engine.portfolio["AAPL"], 10.0)
        self.assertEqual(len(self.engine.trade_history), 1)

    @patch.object(ArbitrageEngine, 'get_current_price', return_value=100.0)
    def test_execute_trade_buy_insufficient_funds(self, mock_price):
        success = self.engine.execute_trade("BUY", "AAPL", 20000.0)
        self.assertFalse(success)
        self.assertAlmostEqual(self.engine.capital, 10000.0)
        self.assertNotIn("AAPL", self.engine.portfolio)

    @patch.object(ArbitrageEngine, 'get_current_price', return_value=100.0)
    def test_execute_trade_sell_success(self, mock_price):
        self.engine.portfolio["AAPL"] = 5.0 # Pre-load portfolio
        success = self.engine.execute_trade("SELL", "AAPL", 200.0)
        self.assertTrue(success)
        self.assertAlmostEqual(self.engine.capital, 10200.0)
        self.assertAlmostEqual(self.engine.portfolio["AAPL"], 3.0)

    @patch.object(ArbitrageEngine, 'get_market_sentiment')
    @patch.object(ArbitrageEngine, 'get_current_price', return_value=100.0)
    def test_run_arbitrage_cycle(self, mock_price, mock_sentiment):
        # Simulate strong buy signal for BTC
        mock_sentiment.side_effect = lambda asset: 0.9 if asset == "BTC" else 0.0
        
        portfolio = self.engine.run_arbitrage_cycle(["BTC"])
        
        # Should have invested 10% of capital (1000.0) at price 100
        self.assertIn("BTC", portfolio)
        self.assertAlmostEqual(portfolio["BTC"], 10.0)
        self.assertAlmostEqual(self.engine.capital, 9000.0)

if __name__ == '__main__':
    unittest.main()
