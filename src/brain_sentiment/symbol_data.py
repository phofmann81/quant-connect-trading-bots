# region imports
from AlgorithmImports import *
from typing import Any

# from QuantConnect.DataSource import *

# endregion


# Your New Python File
class SymbolData:

    def __init__(self, algorithm: Any, symbol: Any) -> None:
        self.algorithm = algorithm
        # Requesting the processed shorter term (7-day) sentiment score data for sentiment trading
        self.dataset_symbol = algorithm.add_data(
            BrainSentimentIndicator7Day, symbol
        ).symbol
        self.ema_50 = algorithm.EMA(symbol=symbol, period=50)
        self.ema_200 = algorithm.EMA(symbol=symbol, period=200)
        self.bar_window = RollingWindow[TradeBar](3)
        self.target_direction = InsightDirection.FLAT
        self._latest_sentiment_value = None

        # Historical data
        history = algorithm.history(self.dataset_symbol, 100, Resolution.DAILY)
        # algorithm.debug(f"We got {len(history)} items from our history request for {self.dataset_symbol}")
        if history.empty:
            return

        # Warm up historical sentiment values, cache for comparing last sentiment score to trade, making it immediately tradable signal
        previous_sentiment_values = history.loc[self.dataset_symbol].sentiment.values
        for sentiment in previous_sentiment_values:
            self.update(sentiment)

    def dispose(self, symbol) -> None:
        # Unsubscribe from the Brain Sentiment feed for this security to release computational resources
        self.algorithm.remove_security(self.dataset_symbol)
        # also unsubscribe the symbol from the algorithm
        self.algorithm.remove_security(symbol)

    def update(self, sentiment: float) -> None:
        # Comparing the last sentiment score and decide to buy if the sentiment increases to ride the popularity
        if self._latest_sentiment_value is not None:
            if sentiment > 0 and sentiment > self._latest_sentiment_value:
                self.target_direction = InsightDirection.UP
            else:
                self.target_direction = InsightDirection.FLAT

            if sentiment < 0 and sentiment < self._latest_sentiment_value:
                self.target_direction = InsightDirection.DOWN
            else:
                self.target_direction = InsightDirection.FLAT

        self._latest_sentiment_value = sentiment

    def update_bar(self, bar):
        self.bar_window.add(bar)
