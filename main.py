# region imports
from AlgorithmImports import *
from tickers import get_tickers_list_as_string

# endregion


class Aron20(QCAlgorithm):

    def initialize(self):
        self.set_brokerage_model(BrokerageName.ALPACA, AccountType.MARGIN)
        self.default_order_properties.time_in_force = TimeInForce.DAY

        self.set_start_date(2023, 9, 5)  # Set Start Date
        self.set_cash(100000)  # Set Strategy Cash
        berlin_time_zone_utc_plus_2 = "Europe/Berlin"
        self.set_time_zone(berlin_time_zone_utc_plus_2)
        ticker_strings = get_tickers_list_as_string() #enable for prod
        # ticker_strings = ["AAL", "ADBE"]  # speed up backtest

        self.symbols = [
            self.add_equity(ticker_string, resolution=Resolution.MINUTE).Symbol
            for ticker_string in ticker_strings
        ]

        self.vwap = {}
        self.ema9 = {}
        self.fibonacci_retracement_levels = {}
        self.daily_high = {}
        self.daily_low = {}
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
            self.vwap[symbol] = self.VWAP(symbol, 60, Resolution.MINUTE)
            self.ema9[symbol] = self.EMA(symbol, 9, Resolution.Minute)
            self.fibonacci_retracement_levels[symbol] = RollingWindow[float](20)    

            # Initialize daily high and low
            self.daily_high[symbol] = float("-inf")
            self.daily_low[symbol] = float("inf")
            self.previous_minute_close[symbol] = float("-inf")
            self.previous_minute_high[symbol] = float("-inf")

            # plot
            self.closing_prices[symbol] = RollingWindow[float](20)    
            self.chart_names[symbol] = f"Trade Chart {symbol.value}"

            self.charts[symbol] = Chart(self.chart_names[symbol])

            self.charts[symbol].add_series(Series("Price", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("VWAP", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("EMA9", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-100", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-78", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-61", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-50", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-38", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-23", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("FIBO-0", SeriesType.Line, 0))
            self.charts[symbol].add_series(Series("Entry", SeriesType.Scatter, 1))
            self.charts[symbol].add_series(Series("Exit", SeriesType.Scatter, 1))
            self.add_chart(self.charts[symbol])



    def reset_daily_high_and_low(self, current_day: datetime.date) -> None:
        # Reset daily high and low at the start of each new day
        if self.previous_day != current_day:
            self.previous_day = current_day
            for symbol in self.symbols:
                self.daily_high[symbol] = float("-inf")
                self.daily_low[symbol] = float("inf")

    def update_daily_high_and_low(self, bar, symbol) -> None:
        # Update the daily high and low
        self.daily_high[symbol] = max(self.daily_high[symbol], bar.high)
        self.daily_low[symbol] = min(self.daily_low[symbol], bar.low)


    @staticmethod
    def is_in_time_frame(current_time: datetime.time) -> bool: 
        return time(18,0) < current_time < time(20,0)

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

    def is_new_high(self, bar, symbol):
        return self.previous_minute_high[symbol] < bar.high

    def get_take_profit_price(self, symbol):
        return self.fibonacci_retracement_levels[symbol][0]["level_38.2%"]

    def get_stop_loss_price(self, symbol, bar):
        amount = self.get_take_profit_price(symbol) - bar.close
        return bar.close - amount

    @staticmethod
    def get_fibonacci_retracement_levels(high, low):
        # Calculate the difference between high and low
        diff = high - low

        # Define Fibonacci levels
        levels = {
            "level_100%": high,  # 100% retracement (high)
            "level_78.6%": low + 0.786 * diff,  # 78.6% retracement
            "level_61.8%": low + 0.618 * diff,  # 61.8% retracement
            "level_50%": low + 0.5 * diff,  # 50% retracement
            "level_38.2%": low + 0.382 * diff,  # 38.2% retracement
            "level_23.6%": low + 0.236 * diff,  # 23.6% retracement
            "level_0%": low,  # 0% retracement (low)
        }

        return levels

    def on_data(self, data):
        current_time = self.time.time()
        current_day = self.time.date()

        self.reset_daily_high_and_low(current_day)

        for symbol in self.symbols:
            if symbol not in data.Bars:
                continue
            

            # risky stuff, this all assumes a fixed order of events for updating
            bar = data.Bars[symbol]
            
            self.update_daily_high_and_low(bar, symbol)
            self.fibonacci_retracement_levels[symbol].add(
                self.get_fibonacci_retracement_levels(
                    self.daily_high[symbol], self.daily_low[symbol]
                )
            )

            self.closing_prices[symbol].add(bar.close)

            close_vwap_divergence_percent = self.get_close_vwap_divergence_percent(
                bar, symbol
            )
            vwap_is_above_50er_fibo = (
                self.vwap[symbol].current.value
                > self.fibonacci_retracement_levels[symbol]["level_50%"]
            )
            close_is_below_23er_fibo = (
                bar.close < self.fibonacci_retracement_levels[symbol]["level_23.6%"]
            )

            if self.is_in_time_frame(current_time) and self.is_significant(
                close_vwap_divergence_percent
            ):
                self.log(
                    f"{symbol} meets the criteria with a divergence of {close_vwap_divergence_percent}% at {self.time}"
                )

                if vwap_is_above_50er_fibo and close_vwap_divergence_percent > 0 and close_is_below_23er_fibo:
                    self.log(f"{symbol} direction long at {self.time}")

                    if (
                        self.previous_minute_close_over_ema9(symbol)
                        and self.is_new_high(bar, symbol)
                        and not self.portfolio[symbol].invested
                    ):
                        self.log(f"enter long for symbol {symbol} at {self.time}")
                        # we'll not track market order tickets yet, TODO later to set more precise stop loss & take profit based on actual fill price
                        self.set_holdings(
                            symbol, 0.01
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
                            "ticket": stop_loss_ticket
                        }
                        self.orders[take_profit_ticket.order_id] = {
                            "oco_order_id": stop_loss_ticket.order_id, 
                            "ticket": take_profit_ticket
                        }

                        self.entry_price[symbol] = bar.close

                        self.plot_trade(symbol)

                # TODO implement short
                # if midpoint_vwap_divergence_percent < 0:
            
            # liquidate all holdings by end of day 
            if current_time >= time(21,59): 
                [self.liquidate(symbol=symbol) for symbol in self.symbols]

            # update previous day / minute
            self.previous_minute_close[symbol] = bar.close
            self.previous_minute_high[symbol] = bar.high

    
    def plot_trade(self, symbol): 
        for symbol in self.symbols: 

            for i in range(self.closing_prices[symbol].count):
                self.plot(chart = self.chart_names[symbol], series="Price", value = self.closing_prices[symbol][i])
                self.plot(chart = self.chart_names[symbol], series="VWAP", value = self.vwap[symbol][i])
                self.plot(chart = self.chart_names[symbol], series="EMA9", value = self.ema9[symbol][i])
                self.plot(chart = self.chart_names[symbol], series="FIBO-100", value = self.fibonacci_retracement_levels[symbol][i]["level_100%"])
                self.plot(chart = self.chart_names[symbol], series="FIBO-78", value = self.fibonacci_retracement_levels[symbol][i]["level_78.6%"])
                self.plot(chart = self.chart_names[symbol], series="FIBO-61", value = self.fibonacci_retracement_levels[symbol][i]["level_61.8%"])
                self.plot(chart = self.chart_names[symbol], series="FIBO-50", value = self.fibonacci_retracement_levels[symbol][i]["level_50%"])
                self.plot(chart = self.chart_names[symbol], series="FIBO-38", value = self.fibonacci_retracement_levels[symbol][i]["level_38.2%"])
                self.plot(chart = self.chart_names[symbol], series="FIBO-23", value = self.fibonacci_retracement_levels[symbol][i]["level_23.6%"])
                self.plot(chart = self.chart_names[symbol], series="FIBO-0", value = self.fibonacci_retracement_levels[symbol][i]["level_0%"])
                self.plot(chart = self.chart_names[symbol], series="Entry", value = self.entry_price[symbol])
                self.plot(chart = self.chart_names[symbol], series="Exit", value = self.exit_price[symbol])

        
    def on_order_event(self, order_event: OrderEvent):
        if order_event.status == OrderStatus.FILLED:
            if (order := self.orders.get(order_event.order_id)) is not None:
                self.transactions.cancel_order(order["oco_order_id"])
                self.exit_time[order_event.symbol] = self.Time
                self.exit_price[order_event.symbol] = order_event.fill_price                
