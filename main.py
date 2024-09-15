# region imports
from AlgorithmImports import *
from tickers import get_tickers_list_as_string
from fibonacci_retracement import FibonacciRetracementIndicator

# endregion


class Aron20(QCAlgorithm):

    def initialize(self):
        self.set_brokerage_model(BrokerageName.ALPACA, AccountType.MARGIN)
        self.default_order_properties.time_in_force = TimeInForce.DAY

        self.set_start_date(2023, 9, 5)  # Set Start Date
        self.set_cash(100000)  # Set Strategy Cash
        berlin_time_zone_utc_plus_2 = "Europe/Berlin"
        self.set_time_zone(berlin_time_zone_utc_plus_2)
        ticker_strings = get_tickers_list_as_string()  # enable for prod
        # ticker_strings = ["AMZN", "CSCO"]  # speed up backtest

        self.symbols = [
            self.add_equity(ticker_string, resolution=Resolution.MINUTE).Symbol
            for ticker_string in ticker_strings
        ]

        self.vwap = {}
        self.ema9 = {}
        self.identities = {}
        self.fibonacci_retracement_levels = {}
        self._wilr = {}
        self.previous_minute_close = {}
        self.previous_minute_high = {}
        self.current_minute_high = {}
        self.take_profit_order_ticket = {}
        self.stop_order_ticket = {}
        self.orders = {}
        self.closing_prices = {}
        self.charts = {}
        self.chart_names = {}
        self.previous_day = None

        for symbol in self.symbols:
            # Initialize indicator for each symbol
            self.identities[symbol] = self.identity(symbol)
            self.vwap[symbol] = self.VWAP(symbol, 60, Resolution.MINUTE)
            self.ema9[symbol] = self.EMA(symbol, 9, Resolution.Minute)
            self._wilr[symbol] = self.wilr(
                symbol=symbol, period=14, resolution=Resolution.Minute
            )
            self.fibonacci_retracement_levels[symbol] = FibonacciRetracementIndicator(
                f"Fibo-{symbol}-daily"
            )
            self.register_indicator(
                symbol, self.fibonacci_retracement_levels[symbol], Resolution.Minute
            )

            # Initialize daily high and low
            self.previous_minute_close[symbol] = float("-inf")
            self.previous_minute_high[symbol] = float("-inf")

            # charting
            self.chart_names[symbol] = f"Trade Chart {symbol.value}"
            self.charts[symbol] = Chart(self.chart_names[symbol])
            self.charts[symbol].add_series(CandlestickSeries(name="Price", index=0))
            self.charts[symbol].add_series(Series("VWAP", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("EMA9", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("WILR", SeriesType.Line, 1))
            # skip those for now we only have 10 series per chart in current tier
            # self.charts[symbol].add_series(Series("FIBO-100", SeriesType.Line, 0))
            # self.charts[symbol].add_series(Series("FIBO-786", SeriesType.Line, 0))
            # self.charts[symbol].add_series(Series("FIBO-618", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-50", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-382", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-236", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-0", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("Entry", SeriesType.SCATTER, 0))
            self.charts[symbol].add_series(Series("Exit", SeriesType.SCATTER, 0))
            self.add_chart(self.charts[symbol])

    @staticmethod
    def is_in_time_frame(current_time: datetime.time) -> bool:
        return time(18, 0) < current_time < time(20, 0)

    # TODO move into indicator
    def get_close_vwap_divergence_percent(self, bar, symbol) -> float:
        vwap_value = self.vwap[symbol].current.value
        return (vwap_value - bar.close) / vwap_value * 100

    def is_significant(self, close_price_vwap_divergence_percent: float):
        if (
            3 >= abs(close_price_vwap_divergence_percent) >= 0.25
        ):  # relax to 0.5 to get more values with less tickers for testing
            return True
        return False

    def previous_minute_close_over_ema9(self, symbol) -> bool:
        return self.previous_minute_close[symbol] > self.ema9[symbol].Current.Value

    # TODO move into indicator
    def is_new_high(self, bar, symbol):
        return self.previous_minute_high[symbol] < bar.high

    def get_take_profit_price(self, symbol):
        return self.fibonacci_retracement_levels[symbol]._382.value

    def get_stop_loss_price(self, symbol, bar):
        amount = self.get_take_profit_price(symbol) - bar.close
        return bar.close - amount

    def on_data(self, data):
        for symbol in self.symbols:
            if symbol not in data.Bars:
                continue

            current_time = self.time.time()
            bar = data.Bars[symbol]

            if self.portfolio[symbol].invested:
                self.plot_trade(symbol, bar)

            close_vwap_divergence_percent = self.get_close_vwap_divergence_percent(
                bar, symbol
            )
            vwap_is_above_50er_fibo = (
                self.vwap[symbol].current.value
                > self.fibonacci_retracement_levels[symbol]._50.value
            )
            close_is_below_23er_fibo = (
                bar.close < self.fibonacci_retracement_levels[symbol]._236.value
            )

            if self.is_in_time_frame(self.time.time()) and self.is_significant(
                close_vwap_divergence_percent
            ):
                self.log(
                    f"{symbol} meets the criteria with a divergence of {close_vwap_divergence_percent}% at {self.time}"
                )

                if (
                    vwap_is_above_50er_fibo
                    and close_vwap_divergence_percent > 0
                    and close_is_below_23er_fibo
                ):
                    self.log(f"{symbol} direction long at {self.time}")

                    if (
                        self.previous_minute_close_over_ema9(symbol)
                        and self.is_new_high(bar, symbol)
                        and (
                            self._wilr[symbol].current.value < -90
                        )  # short would be > -10
                        and not self.portfolio[symbol].invested
                    ):
                        self.log(f"enter long for symbol {symbol} at {self.time}")
                        # we'll not track market order tickets yet, TODO later to set more precise stop loss & take profit based on actual fill price
                        self.set_holdings(
                            symbol=symbol, percentage=0.01
                        )  # enter with market order with 1% portfolio

                        # register take profit
                        take_profit_ticket = self.LimitOrder(
                            symbol,
                            -self.Portfolio[symbol].Quantity,
                            self.get_take_profit_price(symbol),
                        )
                        # register stop loss
                        stop_loss_ticket = self.StopMarketOrder(
                            symbol,
                            -self.Portfolio[symbol].Quantity,
                            self.get_stop_loss_price(symbol, bar),
                        )
                        # set up order index so we can cancel the opposite once filled
                        self.orders[stop_loss_ticket.order_id] = {
                            "oco_order_id": take_profit_ticket.order_id,
                        }
                        self.orders[take_profit_ticket.order_id] = {
                            "oco_order_id": stop_loss_ticket.order_id,
                        }
                        self.plot_trade(symbol=symbol, bar=bar)

                # TODO implement short
                # if midpoint_vwap_divergence_percent < 0:

            # liquidate all holdings by end of day
            if current_time >= time(22, 00):
                [self.liquidate(symbol=symbol) for symbol in self.symbols]

            # update previous day / minute
            # TODO use rolling window of two bars here
            self.previous_minute_close[symbol] = bar.close
            self.previous_minute_high[symbol] = bar.high

    def plot_trade(self, symbol, bar):
        self.plot(chart=self.chart_names[symbol], series="Price", bar=bar)
        self.plot(
            chart=self.chart_names[symbol],
            series="VWAP",
            value=self.vwap[symbol].current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="EMA9",
            value=self.ema9[symbol].current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="WILR",
            value=self._wilr[symbol].current.value,
        )

        # self.plot(chart = self.chart_names[symbol], series="FIBO-100", value = self.fibonacci_retracement_levels[symbol]._100.current.value)
        # skip 78 and 61 as we have max 10 series per chart in current tier
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-50",
            value=self.fibonacci_retracement_levels[symbol]._50.current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-382",
            value=self.fibonacci_retracement_levels[symbol]._382.current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-236",
            value=self.fibonacci_retracement_levels[symbol]._236.current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-0",
            value=self.fibonacci_retracement_levels[symbol]._0.current.value,
        )

    def on_order_event(self, order_event: OrderEvent):
        if order_event.status == OrderStatus.FILLED:
            if (order := self.orders.get(order_event.order_id)) is not None:  # exit
                self.transactions.cancel_order(order["oco_order_id"])
                self.plot(
                    chart=self.chart_names[order_event.symbol],
                    series="Exit",
                    value=order_event.fill_price,
                )
            else:  # plot entry
                self.plot(
                    chart=self.chart_names[order_event.symbol],
                    series="Entry",
                    value=order_event.fill_price,
                )
