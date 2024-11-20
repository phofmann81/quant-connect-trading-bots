# region imports
from AlgorithmImports import *
from symbol_data import SymbolData
from operator import gt, lt

# endregion

class BrainSentimentAlphaModel(AlphaModel):

    symbol_data_by_symbol = {}

    def update_bars(self, bars: Dict[Symbol, TradeBar]):
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if symbol in bars:
                symbol_data.update_bar(bars[symbol])

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

        for symbol, bar in slice.bars.items():
            symbol_data = self.symbol_data_by_symbol.get(symbol)
            if not symbol_data:
                continue
            if symbol_data.true_range.current.value < 2:
                continue

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

    def check_stop_loss(self, insights: List[Insight], algorithm) -> List[Insight]:
        invested_symbols = [
            symbol
            for symbol, security in algorithm.securities.items()
            if security.invested
        ]
        for symbol in invested_symbols:
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

        # Issue orders at 9pm
        if algorithm.time.time() == time(21, 1):
            algorithm.debug(f"total active securities: {len(slice.bars)}")
            insights += self.generate_insights(slice, insights, algorithm)

        if algorithm.time.time() > time(21, 1):
            insights += self.check_stop_loss(insights, algorithm)

        return insights

    def check_previous_bar(self, bar_window, is_long):

        def is_inner_candle(bar_window):
            return (
                bar_window[0].high <= bar_window[1].high
                and bar_window[0].low >= bar_window[1].low
            )

        def is_outer_candle(bar_window):
            return (
                bar_window[0].high > bar_window[1].high
                or bar_window[0].low < bar_window[1].low
            )

        def get_bar_direction(bar):
            return 1 if bar.close >= bar.open else -1

        if is_long:
            return (
                is_outer_candle(bar_window) and get_bar_direction(bar_window[0]) == 1
            ) or (
                is_inner_candle(bar_window) and get_bar_direction(bar_window[0]) == -1
            )

        else:
            return (
                is_outer_candle(bar_window) and get_bar_direction(bar_window[0]) == -1
            ) or (is_inner_candle(bar_window) and get_bar_direction(bar_window[0]) == 1)

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
