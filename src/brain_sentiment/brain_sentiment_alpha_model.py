# region imports
from AlgorithmImports import *

# from QuantConnect.DataSource import *
from src.brain_sentiment.symbol_data import SymbolData
from operator import gt, lt
from datetime import time

# endregion


# Your New Python File
class BrainSentimentAlphaModel(AlphaModel):

    symbol_data_by_symbol = {}
    symbols_with_news = []

    def update_bars(self, bars: Dict[Symbol, TradeBar]):
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if symbol in bars:
                symbol_data.update_bar(bars[symbol])

    def update_symbols_with_news(self, slice, algorithm):
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if (
                slice.contains_key(symbol_data.dataset_symbol)
                and slice[symbol_data.dataset_symbol] is not None
            ):

                sentiment_data = slice[symbol_data.dataset_symbol]
                sentiment = sentiment_data.sentiment
                # symbol_data.update(sentiment)
                if (
                    abs(sentiment) > 0.4
                    and sentiment_data.sentimental_article_mentions > 30
                ):
                    algorithm.debug(f"symbol {symbol.value}: sentiment: {sentiment}")
                    self.symbols_with_news.append(symbol)

    def check_entry_condition_ema_close(
        self, bar, ema_20, ema_50, ema_200, is_long: bool
    ):
        op = gt if is_long else lt
        return (
            op(bar.close, ema_50)
            and op(bar.close, ema_200)
            and op(ema_20, ema_50)
            and op(ema_50, ema_200)
        )

    def check_entry_condition_open_ema_20(self, bar, ema_20, is_long: bool):
        op = gt if is_long else lt
        return op(bar.open, ema_20)

    def generate_insights(
        self, slice, insights: List[Insight], algorithm
    ) -> List[Insight]:
        algorithm.debug(f"total symbols with news: {len(self.symbols_with_news)}")

        for symbol in self.symbols_with_news:
            symbol_data = self.symbol_data_by_symbol[symbol]
            bar = slice.bars[symbol]
            ema_20 = symbol_data.ema_20.current.value
            ema_50 = symbol_data.ema_50.current.value
            ema_200 = symbol_data.ema_200.current.value

            if (
                self.check_entry_condition_ema_close(
                    bar,
                    ema_20,
                    ema_50,
                    ema_200,
                    True,
                )
                and self.check_previous_bar(symbol_data.bar_window, True)
                and self.check_entry_condition_open_ema_20(bar, ema_20, True)
            ):
                insights.append(
                    Insight.price(
                        symbol, timedelta(hours=1), direction=InsightDirection.UP
                    )
                )
            elif (
                self.check_entry_condition_ema_close(
                    bar,
                    ema_20,
                    ema_50,
                    ema_200,
                    False,
                )
                and self.check_previous_bar(symbol_data.bar_window, False)
                and self.check_entry_condition_open_ema_20(bar, ema_20, False)
            ):
                insights.append(
                    Insight.price(
                        symbol, timedelta(hours=1), direction=InsightDirection.DOWN
                    )
                )
        return insights

    def check_stop_loss(self, insights: List[Insight]) -> List[Insight]:
        for symbol in self.symbols_with_news:
            symbol_data = self.symbol_data_by_symbol[symbol]

            if self.close_cross_ema_200(
                symbol_data.bar_window, symbol_data.ema_200
            ):  # Stop Loss
                insights.append(
                    Insight.price(
                        symbol,
                        timedelta(hours=1),
                        direction=InsightDirection.FLAT,
                    )
                )
        return insights

    def update(self, algorithm: QCAlgorithm, slice: Slice) -> List[Insight]:
        insights = []

        if len(slice.bars) > 0:
            self.update_bars(slice.bars)

        # TODO only do this for the 13,0 time all the others have no data i think
        if slice.get(BrainSentimentIndicator7Day).count > 0:
            self.update_symbols_with_news(slice, algorithm)
            algorithm.debug(
                f"total active securities: {len(algorithm.active_securities)}"
            )

        # Issue orders at 9pm
        if algorithm.time.time() == time(21, 1):
            insights += self.generate_insights(slice, insights, algorithm)

        if algorithm.time.time() > time(21, 1):
            insights += self.check_stop_loss(insights)

        if algorithm.time.time() == time(22, 0):
            self.symbols_with_news = []

        return insights

    def check_previous_bar(self, bar_window, is_long):
        def evaluate(condition, is_long):
            return condition if is_long else not condition

        def get_bar_range(bar):
            return bar.high - bar.low

        def get_bar_direction(bar):
            return 1 if bar.open > bar.close else -1

        if (
            evaluate(
                get_bar_range(bar_window[0]) > get_bar_range(bar_window[1]), is_long
            )
            and get_bar_direction(bar_window[0]) == 1
        ) or (
            evaluate(
                get_bar_range(bar_window[0]) < get_bar_range(bar_window[1]), is_long
            )
            and get_bar_direction(bar_window[0]) == -1
        ):
            return True

        return False

    def close_cross_ema_200(self, bar_window, ema_200):

        if not ema_200.is_ready or ema_200.previous.value == 0.0:
            return False

        return (
            bar_window[0].close > ema_200.current.value
            and bar_window[1].close <= ema_200.previous.value
        ) or (
            bar_window[0].close < ema_200.current.value
            and bar_window[1].close >= ema_200.previous.value
        )

    def on_securities_changed(
        self, algorithm: QCAlgorithm, changes: SecurityChanges
    ) -> None:
        for security in changes.added_securities:
            symbol = security.symbol
            self.symbol_data_by_symbol[symbol] = SymbolData(algorithm, symbol)

        for security in changes.removed_securities:
            symbol = security.symbol
            symbol_data = self.symbol_data_by_symbol.pop(symbol, None)
            if symbol_data:
                symbol_data.dispose(symbol)
