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

    def is_jump(self, window):
        if (
            window[0].sentiment_7_days is None
            or window[0].total_buzz_volume_7_days is None
            or window[1].sentiment_7_days is None
            or window[1].total_buzz_volume_7_days is None
        ):
            return False

        diff_sentiment = window[1].sentiment_7_days - window[0].sentiment_7_days

        diff_total_buzz_volume = (
            window[1].total_buzz_volume_7_days - window[0].total_buzz_volume_7_days
        )

        return abs(diff_sentiment) > 0.2 or abs(diff_total_buzz_volume) > 1

    def universe_selection(
        self,
        data: List[BrainSentimentIndicatorUniverse],
    ) -> List[Symbol]:
        news_today = []
        diffs = []

        self.algorithm.debug(
            f"symbol candidates in universe: {len(self.symbol_data_by_symbol)}"
        )
        self.algorithm.debug(f"date: {self.algorithm.time}")
        for b in data:
            if b.symbol not in self.symbol_data_by_symbol:
                self.symbol_data_by_symbol[b.symbol] = UniverseSymbolData()

            self.symbol_data_by_symbol[b.symbol].window.add(b)

            if self.symbol_data_by_symbol[b.symbol].window.is_ready:
                if self.is_jump(self.symbol_data_by_symbol[b.symbol].window):
                    news_today.append(b.symbol)
                    # self.algorithm.debug(f"{b.symbol.value} has sentiment {b.sentiment_7_days} and buzz factor {b.total_buzz_volume_7_days}")

        self.algorithm.debug(
            f"news: {len(news_today)}, fundamentals: {len(self.fundamental_universe_ref.fundamental_symbols)}"
        )
        self.algorithm.debug(
            f"fundamental symbols: {[s.value for s in self.fundamental_universe_ref.fundamental_symbols]}"
        )

        result = list(
            set(news_today) & set(self.fundamental_universe_ref.fundamental_symbols)
        )

        self.algorithm.debug(f"universe result today: {len(result)}")
        self.algorithm.debug(f"symbols: {([s.value for s in result])}")

        return result
