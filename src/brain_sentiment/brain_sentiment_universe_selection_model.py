# region imports
from AlgorithmImports import *
from heapq import nlargest
import statistics as s


class UniverseSymbolData:
    def __init__(self):
        self.window = RollingWindow[BrainSentimentIndicatorUniverse](2)


class BrainSentimentUniverseSelectionModel:
    def __init__(self, fundamental_universe_ref, algorithm):
        """
        Parameters:
        - fundamental_symbols_ref: A reference to the list of fundamental symbols from FundamentalUniverseSelectionModel.
        """
        self.fundamental_universe_ref = fundamental_universe_ref
        self.symbol_data_by_symbol = {}
        self.algorithm = algorithm

    def get_diff(self, window):
        if window[0].sentiment_7_days is None or window[1].sentiment_7_days is None:
            return 0
        return abs(window[1].sentiment_7_days - window[0].sentiment_7_days)

    def is_jump(self, window):
        if window[0].sentiment_7_days is None or window[1].sentiment_7_days is None:
            return False

        diff = window[1].sentiment_7_days - window[0].sentiment_7_days

        return abs(diff) > 0.2

    def universe_selection(
        self,
        data: List[BrainSentimentIndicatorUniverse],
    ) -> List[Symbol]:

        news_today = []
        diffs = []

        for b in data:
            if b.symbol not in self.symbol_data_by_symbol:
                self.symbol_data_by_symbol[b.symbol] = UniverseSymbolData()

            self.symbol_data_by_symbol[b.symbol].window.add(b)

            if self.symbol_data_by_symbol[b.symbol].window.is_ready:
                diffs.append(self.get_diff(self.symbol_data_by_symbol[b.symbol].window))
                if self.is_jump(self.symbol_data_by_symbol[b.symbol].window):
                    news_today.append(b.symbol)

        stats = [round(q, 1) for q in s.quantiles(diffs, n=100)][-5:]
        self.algorithm.debug(f"diff 95 percentile stats: {stats}")
        return list(
            set(news_today) & set(self.fundamental_universe_ref.fundamental_symbols)
        )
