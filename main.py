# region imports
from AlgorithmImports import *
from tickers import get_tickers_list_as_string
from fibonacci_retracement import FibonacciRetracementIndicator
from high_volume_universe_selection_model import HighVolumeUniverseSelectionModel

# from oco_margin_model import OCOMarginModel


class Aron20(QCAlgorithm):

    def initialize(self):
        self.set_brokerage_model(
            BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.MARGIN
        )
        self.total_trades = 0
        self.winning_trades = 0

        # liquidate all holdings by end of day
        self.default_order_properties.time_in_force = TimeInForce.DAY
        self.settings.liquidate_enabled = True

        self.set_start_date(2024, 3, 22)  # Set Start Date
        self.set_cash(100000)  # Set Strategy Cash
        berlin_time_zone_utc_plus_2 = "Europe/Berlin"
        self.set_time_zone(berlin_time_zone_utc_plus_2)
        ticker_strings = get_tickers_list_as_string()  # enable for prod
        # ticker_strings = ["AMZN", "CSCO"]  # speed up backtest

        self.symbols = []

        for ticker_string in ticker_strings:
            self.symbols.append(
                self.add_equity(ticker_string, resolution=Resolution.MINUTE).Symbol
            )
            self.securities[ticker_string].set_margin_model(SecurityMarginModel.NULL)

        self._vwap = {}
        self._ema9 = {}
        self._fibonacci_retracement_levels = {}
        self._wilr = {}
        self._atr = {}
        self.previous_minute_close = {}
        self.previous_minute_high = {}
        self.previous_minute_low = {}
        self.current_minute_high = {}
        self.take_profit_order_ticket = {}
        self.stop_order_ticket = {}
        self.orders = {}
        self.closing_prices = {}
        self.charts = {}
        self.chart_names = {}
        self.previous_day = None
        self.traded_today = {}

        # scheduled actions
        self.schedule.on(
            self.date_rules.every_day(), self.time_rules.at(21, 55), self.liquidate
        )

        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.at(21, 55),
            self.reset_traded_today,
        )

        for symbol in self.symbols:
            # Initialize indicator for each symbol
            self._vwap[symbol] = self.vwap(symbol=symbol)
            self._ema9[symbol] = self.ema(symbol=symbol, period=9)
            self._wilr[symbol] = self.wilr(
                symbol=symbol, period=14, resolution=Resolution.Minute
            )
            self._atr[symbol] = self.ATR(
                symbol=symbol, period=14, resolution=Resolution.Minute
            )
            # custom indicators
            self._fibonacci_retracement_levels[symbol] = FibonacciRetracementIndicator(
                f"Fibo-{symbol}-daily"
            )
            self.register_indicator(
                symbol, self._fibonacci_retracement_levels[symbol], Resolution.Minute
            )

            # warm up indicators with full day
            self.warm_up_indicator(
                symbol=symbol,
                periods=14,
                indicators=[self._atr[symbol], self._vwap[symbol]],
            )
            # ema9s want indicator datapoint, not tradebar
            history = self.history[TradeBar](
                symbol=symbol, periods=9, resolution=Resolution.Minute
            )
            for bar in history:
                self._ema9[symbol].update(IndicatorDataPoint(bar.end_time, bar.close))

            self.warm_up_indicator(
                symbol=symbol, periods=14, indicators=[self._wilr[symbol]]
            )

            # Initialize daily high and low
            self.previous_minute_close[symbol] = float("-inf")
            self.previous_minute_high[symbol] = float("-inf")
            self.previous_minute_low[symbol] = float("inf")

            # charting
            self.chart_names[symbol] = f"Trade Chart {symbol.value}"
            self.charts[symbol] = Chart(self.chart_names[symbol])
            self.charts[symbol].add_series(CandlestickSeries(name="Price", index=0))
            self.charts[symbol].add_series(Series("VWAP", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("EMA9", SeriesType.Line, 0))
            # self.charts[symbol].add_series(Series("WILR", SeriesType.Line, 1))
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

    def reset_traded_today(self):
        self.traded_today = {}

    def warm_up_indicator(self, symbol, periods: int, indicators: List[Indicator]):
        history = self.history[TradeBar](
            symbol=symbol, periods=periods, resolution=Resolution.Minute
        )
        for bar in history:
            for indicator in indicators:
                indicator.update(bar)

    @staticmethod
    def is_in_time_frame(current_time: datetime.time) -> bool:
        return time(18, 0) < current_time < time(21, 0)

    def get_close_vwap_divergence_percent(self, bar, symbol) -> float:
        vwap_value = self._vwap[symbol].current.value
        return (vwap_value - bar.close) / vwap_value * 100

    def is_significant(self, close_price_vwap_divergence_percent: float):
        if (
            3
            >= abs(close_price_vwap_divergence_percent)
            >= float(self.get_parameter("close_vwap_div_threshold"))
        ):  # relax to 0.5 to get more values with less tickers for testing
            return True
        return False

    def previous_minute_close_over_ema9(self, symbol) -> bool:
        return self.previous_minute_close[symbol] > self._ema9[symbol].previous.price

    def is_new_high(self, bar, symbol):
        return self.previous_minute_high[symbol] < bar.high

    def is_new_low(self, bar, symbol):
        return self.previous_minute_low[symbol] > bar.low

    def get_take_profit_price_long(self, symbol):
        return self._fibonacci_retracement_levels[symbol]._382.current.value

    def get_take_profit_price_short(self, symbol):
        return self._fibonacci_retracement_levels[symbol]._618.current.value

    def get_stop_loss_price_long(self, symbol, bar):
        return self._fibonacci_retracement_levels[symbol]._0.current.value - (
            2 * self._atr[symbol].current.value
        )

    def get_stop_loss_price_short(self, symbol, bar):
        return self._fibonacci_retracement_levels[symbol]._100.current.value + (
            2 * self._atr[symbol].current.value
        )

    def stop_loss_has_enough_space_long(self, symbol, bar):
        distance = self.stop_loss_distance_long(symbol, bar)
        return ((bar.close + distance) * 1.3) <= self._fibonacci_retracement_levels[
            symbol
        ]._382.current.value

    def stop_loss_has_enough_space_short(self, symbol, bar):
        distance = self.stop_loss_distance_short(symbol, bar)
        return (bar.close - distance) * 1.3 >= self._fibonacci_retracement_levels[
            symbol
        ]._618.current.value

    def stop_loss_distance_long(self, symbol, bar):
        return bar.close - self.get_stop_loss_price_long(symbol, bar)

    def stop_loss_distance_short(self, symbol, bar):
        return self.get_stop_loss_price_short(symbol, bar) - bar.close

    def get_position_size(self, stop_loss_distance):
        # Risk per trade is 1% of portfolio
        risk_per_trade = self.portfolio.total_portfolio_value * 0.01

        # Risk per share is the difference between the current price and the stop loss distance
        risk_per_share = stop_loss_distance

        # Calculate the position size
        position_size = risk_per_trade / risk_per_share

        return position_size

    def register_oco_orders(self, take_profit_ticket, stop_loss_ticket):
        # set up order index so we can cancel the opposite once filled
        self.orders[stop_loss_ticket.order_id] = {
            "oco_order_id": take_profit_ticket.order_id,
            "type": "stop_loss",
        }
        self.orders[take_profit_ticket.order_id] = {
            "oco_order_id": stop_loss_ticket.order_id,
            "type": "take_profit",
        }
        return None

    def on_end_of_algorithm(self):
        if self.total_trades > 0:
            hit_rate = self.winning_trades / self.total_trades
            self.debug(f"Hit Rate: {hit_rate:.2%}")

    def on_data(self, data):
        current_time = self.time.time()

        for symbol in self.symbols:
            if symbol not in data.Bars or symbol in self.traded_today:
                continue

            bar = data.Bars[symbol]

            if not self.is_in_time_frame(current_time):
                self.update_previous_minute_values(symbol, bar)
                return None

            if self.portfolio[symbol].invested:
                self.plot_trade(symbol, bar)

            close_vwap_divergence_percent = self.get_close_vwap_divergence_percent(
                bar, symbol
            )

            # long
            vwap_is_above_50er_fibo = (
                self._vwap[symbol].current.value
                > self._fibonacci_retracement_levels[symbol]._50.current.value
            )
            # long
            close_is_below_23er_fibo = (
                bar.close
                < self._fibonacci_retracement_levels[symbol]._236.current.value
            )
            # short
            close_is_above_78er_fibo = (
                bar.close
                > self._fibonacci_retracement_levels[symbol]._786.current.value
            )

            if self.is_significant(close_vwap_divergence_percent):

                if (
                    vwap_is_above_50er_fibo
                    and close_vwap_divergence_percent > 0
                    and close_is_below_23er_fibo
                    and self.stop_loss_has_enough_space_long(symbol, bar)
                ):

                    if (
                        self.previous_minute_close_over_ema9(symbol)
                        and self.is_new_high(bar, symbol)
                        and (self._wilr[symbol].current.value < -90)
                        and not self.portfolio[symbol].invested
                    ):
                        self.market_order(
                            symbol=symbol,
                            quantity=self.get_position_size(
                                self.stop_loss_distance_long(symbol, bar)
                            ),
                        )  # enter with market order with 1% portfolio
                        self.traded_today[symbol] = True
                        # register take profit
                        take_profit_ticket = self.LimitOrder(
                            symbol,
                            -self.Portfolio[symbol].Quantity,
                            self.get_take_profit_price_long(symbol),
                        )
                        # register stop loss
                        stop_loss_ticket = self.StopMarketOrder(
                            symbol,
                            -self.Portfolio[symbol].Quantity,
                            self.get_stop_loss_price_long(symbol, bar),
                        )
                        self.register_oco_orders(take_profit_ticket, stop_loss_ticket)
                        self.plot_trade(symbol=symbol, bar=bar)
                elif (
                    not vwap_is_above_50er_fibo
                    and close_vwap_divergence_percent < 0
                    and close_is_above_78er_fibo
                    and self.stop_loss_has_enough_space_short(symbol, bar)
                ):

                    if (
                        not self.previous_minute_close_over_ema9(symbol)  # TODO check
                        and self.is_new_low(bar, symbol)
                        and (self._wilr[symbol].current.value > -10)
                        and not self.portfolio[symbol].invested
                    ):
                        self.market_order(
                            symbol=symbol,
                            quantity=-self.get_position_size(
                                self.stop_loss_distance_short(symbol, bar)
                            ),
                        )

                        self.traded_today[symbol] = True

                        # register take profit
                        take_profit_ticket = self.LimitOrder(
                            symbol,
                            -self.Portfolio[symbol].Quantity,
                            self.get_take_profit_price_short(symbol),
                        )
                        # register stop loss
                        stop_loss_ticket = self.StopMarketOrder(
                            symbol,
                            -self.Portfolio[symbol].Quantity,
                            self.get_stop_loss_price_short(symbol, bar),
                        )
                        self.register_oco_orders(take_profit_ticket, stop_loss_ticket)

                        self.plot_trade(symbol=symbol, bar=bar)

            self.update_previous_minute_values(symbol, bar)

    def update_previous_minute_values(self, symbol, bar):
        self.previous_minute_close[symbol] = bar.close
        self.previous_minute_high[symbol] = bar.high
        self.previous_minute_low[symbol] = bar.low

    def plot_trade(self, symbol, bar):
        self.plot(chart=self.chart_names[symbol], series="Price", bar=bar)
        self.plot(
            chart=self.chart_names[symbol],
            series="VWAP",
            value=self._vwap[symbol].current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="EMA9",
            value=self._ema9[symbol].current.value,
        )
        # self.plot(
        #     chart=self.chart_names[symbol],
        #     series="WILR",
        #     value=self._wilr[symbol].current.value,
        # )

        # self.plot(chart = self.chart_names[symbol], series="FIBO-100", value = self.fibonacci_retracement_levels[symbol]._100.current.value)
        # skip 78 and 61 as we have max 10 series per chart in current tier
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-50",
            value=self._fibonacci_retracement_levels[symbol]._50.current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-382",
            value=self._fibonacci_retracement_levels[symbol]._382.current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-236",
            value=self._fibonacci_retracement_levels[symbol]._236.current.value,
        )
        self.plot(
            chart=self.chart_names[symbol],
            series="FIBO-0",
            value=self._fibonacci_retracement_levels[symbol]._0.current.value,
        )

    def on_order_event(self, order_event: OrderEvent):
        if order_event.status == OrderStatus.FILLED:
            if (order := self.orders.get(order_event.order_id)) is not None:  # exit
                self.transactions.cancel_order(order["oco_order_id"])
                if order["type"] == "take_profit":
                    self.winning_trades += 1
                self.plot(
                    chart=self.chart_names[order_event.symbol],
                    series="Exit",
                    value=order_event.fill_price,
                )
            else:  # plot entry
                self.total_trades += 1
                self.plot(
                    chart=self.chart_names[order_event.symbol],
                    series="Entry",
                    value=order_event.fill_price,
                )
