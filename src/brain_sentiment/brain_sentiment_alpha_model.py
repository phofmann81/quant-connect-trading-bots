# region imports
from AlgorithmImports import *
from QuantConnect.DataSource import *
from symbol_data import SymbolData
from operator import gt, lt

# endregion


# Your New Python File
class BrainSentimentAlphaModel(AlphaModel):

    symbol_data_by_symbol = {}
    symbols_with_news = []

    def update(self, algorithm: QCAlgorithm, slice: Slice) -> List[Insight]:
        insights = []

        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if not slice.bars.get(symbol):
                continue

            symbol_data.update_bar(slice.bars[symbol])
            # Update trade direction based on updated data
            if (
                slice.contains_key(symbol_data.dataset_symbol)
                and slice[symbol_data.dataset_symbol] is not None
            ):

                sentiment_data = slice[symbol_data.dataset_symbol]
                sentiment = sentiment_data.sentiment
                symbol_data.update(sentiment)

                if (
                    abs(sentiment) > 0.4
                    and sentiment_data.sentimental_article_mentions > 30
                ):
                    algorithm.debug(f"symbol {symbol.value}: sentiment: {sentiment}")
                    self.symbols_with_news.append(symbol)

            # Issue orders at 9pm
        if algorithm.time.time() == time(21, 1):

            for symbol in self.symbols_with_news:
                symbol_data = self.symbol_data_by_symbol[symbol]

                if (
                    slice.bars[symbol].close > symbol_data.ema_50.current.value
                    and slice.bars[symbol].close > symbol_data.ema_200.current.value
                    and self.check_previous_bar(symbol_data.bar_window, True)
                ):
                    insights.append(
                        Insight.price(
                            symbol, timedelta(hours=1), direction=InsightDirection.UP
                        )
                    )
                elif (
                    slice.bars[symbol].close < symbol_data.ema_50.current.value
                    and slice.bars[symbol].close < symbol_data.ema_200.current.value
                    and self.check_previous_bar(symbol_data.bar_window, False)
                ):
                    insights.append(
                        Insight.price(
                            symbol, timedelta(hours=1), direction=InsightDirection.DOWN
                        )
                    )

        if algorithm.time.time() > time(21, 1):
            for symbol in self.symbols_with_news:
                symbol_data = self.symbol_data_by_symbol[symbol]

                if self.price_cross_ema_200(
                    symbol_data.bar_window, symbol_data.ema_200
                ):  # Stop Loss
                    insights.append(
                        Insight.price(
                            symbol,
                            timedelta(hours=2),
                            direction=InsightDirection.FLAT,
                        )
                    )

        if algorithm.time.time() == time(22, 0):
            self.symbols_with_news = []

        return insights

    def check_previous_bar(self, bar_window, is_long):
        op_1 = gt if is_long else lt
        op_2 = lt if is_long else gt

        def get_bar_range(bar):
            return bar.high - bar.low

        def get_bar_direction(bar):
            return 1 if bar.open > bar.close else -1

        if (
            op1(get_bar_range(bar_window[0]), get_bar_range(bar_window[1]))
            and get_bar_direction(bar_window[0]) == 1
        ) or (
            op2(get_bar_range(bar_window[0]), get_bar_range(bar_window[1]))
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
