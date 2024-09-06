# region imports
from AlgorithmImports import *
from tickers import get_tickers_list_as_string

# endregion


class Aron20(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2023, 9, 5)  # Set Start Date
        self.set_cash(100000)  # Set Strategy Cash
        berlin_time_zone_utc_plus_2 = "Europe/Berlin"
        self.set_time_zone(berlin_time_zone_utc_plus_2)
        # ticker_strings = get_tickers_list_as_string() #enable for prod
        ticker_strings = ["AAL", "ADBE"]  # speed up backtest

        self.symbols = [
            self.add_equity(ticker_string, resolution=Resolution.MINUTE).Symbol
            for ticker_string in ticker_strings
        ]

        self.vwap = {}
        self.daily_high = {}
        self.daily_low = {}
        for symbol in self.symbols:
            # Initialize VWAP indicator for each symbol
            self.vwap[symbol] = self.VWAP(symbol, 60, Resolution.MINUTE)
            # Initialize daily high and low
            self.daily_high[symbol] = float("-inf")
            self.daily_low[symbol] = float("inf")

        self.previous_day = None

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
    def is_after_hour(current_time: datetime.time, hour: int) -> bool:
        return current_time < time(hour, 0)

    def midpoint_diverges_from_vwap(self, bar, symbol, current_time) -> bool:
        self.update_daily_high_and_low(bar, symbol)
        daily_midpoint = (self.daily_high[symbol] + self.daily_low[symbol]) / 2
        vwap_value = self.vwap[symbol].current.value
        midpoint_vwap_divergence_percent = (
            abs(daily_midpoint - vwap_value) / vwap_value * 100
        )
        if (
            3 >= midpoint_vwap_divergence_percent >= 1
        ):  # relax to 0.5 to get more values with less tickers for testing
            self.log(
                f"{symbol} meets the criteria with a divergence of {midpoint_vwap_divergence_percent}% at {self.time}"
            )
            return True
        return False

    def on_data(self, data):
        current_time = self.time.time()
        current_day = self.time.date()

        self.reset_daily_high_and_low(current_day)

        for symbol in self.symbols:
            if symbol not in data.Bars:
                continue

            bar = data.Bars[symbol]
            if self.is_after_hour(
                current_time, 18
            ) and self.midpoint_diverges_from_vwap(bar, symbol, current_time):
                # trade
                print("yaya")
