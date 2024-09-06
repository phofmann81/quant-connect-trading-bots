# region imports
from AlgorithmImports import *
from tickers import get_tickers_list_as_string
# endregion

class Aron20(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2023, 9, 5)    # Set Start Date
        self.set_cash(100000)              # Set Strategy Cash
        berlin_time_zone_utc_plus_2 = "Europe/Berlin"
        self.set_time_zone(berlin_time_zone_utc_plus_2)
        # ticker_strings = get_tickers_list_as_string() #enable for prod
        ticker_strings = [ "AAL", "ADBE"] # speed up backtest
        
        self.symbols = [
            self.add_equity(ticker_string, resolution=Resolution.MINUTE).Symbol 
            for ticker_string in ticker_strings
        ]
                                
        self.vwap = {}
        self.ema9 = {}
        self.daily_high = {}
        self.daily_low = {}
        self.previous_minute_close = {}
        self.previous_minute_high = {}
        self.current_minute_high = {}

        for symbol in self.symbols:
            # Initialize VWAP indicator for each symbol
            self.vwap[symbol] = self.VWAP(symbol, 60, Resolution.MINUTE)
            self.ema9[symbol] = self.EMA(symbol, 9, Resolution.Minute)

            # Initialize daily high and low
            self.daily_high[symbol] = float('-inf')
            self.daily_low[symbol] = float('inf')
            self.previous_minute_close[symbol] = float('-inf')
            self.previous_minute_high[symbol] = float('-inf')
        
        self.previous_day = None


    def reset_daily_high_and_low(self, current_day: datetime.date ) -> None: 
        # Reset daily high and low at the start of each new day
        if self.previous_day != current_day:
            self.previous_day = current_day
            for symbol in self.symbols:
                self.daily_high[symbol] = float('-inf')
                self.daily_low[symbol] = float('inf')
                        
    def update_daily_high_and_low(self, bar, symbol)-> None:
        # Update the daily high and low        
        self.daily_high[symbol] = max(self.daily_high[symbol], bar.high)
        self.daily_low[symbol] = min(self.daily_low[symbol], bar.low)
    
    @staticmethod
    def is_after_hour(current_time: datetime.time, hour: int) -> bool: 
        return current_time < time(hour,0)

    def get_midpoint_vwap_divergence_percent(self, bar, symbol, current_time) -> float: 
        self.update_daily_high_and_low(bar, symbol)                    
        daily_midpoint = (self.daily_high[symbol] + self.daily_low[symbol]) / 2        
        vwap_value = self.vwap[symbol].current.value        
        return (daily_midpoint - vwap_value) / vwap_value * 100
    
    
    def is_significant(self, midpoint_vwap_divergence_percent: float): 
        if (3 >= abs(midpoint_vwap_divergence_percent) >= 1): # relax to 0.5 to get more values with less tickers for testing
            return True        
        return False

    def previous_minute_close_over_ema9(self, symbol) -> bool: 
        return self.previous_minute_close[symbol] > self.ema9[symbol].Current.Value
    
    def is_new_high(self, bar, symbol): 
        return self.previous_minute_high[symbol] < bar.high

    def on_data(self, data):
        current_time = self.time.time()
        current_day = self.time.date()

        self.reset_daily_high_and_low(current_day)
     
        for symbol in self.symbols:
            if symbol not in data.Bars:
                continue
            
            bar = data.Bars[symbol] 
            
            midpoint_vwap_divergence_percent = self.get_midpoint_vwap_divergence_percent(bar, symbol, current_time)
            
            if self.is_after_hour(current_time, 18) and self.is_significant(midpoint_vwap_divergence_percent): 
                self.log(f"{symbol} meets the criteria with a divergence of {midpoint_vwap_divergence_percent}% at {self.time}")
            
                if midpoint_vwap_divergence_percent > 0: 
                    self.log(f"{symbol} direction long at {self.time}")
            
                    if self.previous_minute_close_over_ema9(symbol) and self.is_new_high(bar, symbol): 
                        self.log(f"enter long for symbol {symbol} at {self.time}")
                
                # TODO implement short
                # if midpoint_vwap_divergence_percent < 0: 
                #     #short 
                #     print("trade short")
            
            # update previous day / minute
            self.previous_minute_close[symbol] = bar.Close
            self.previous_minute_high[symbol] = bar.high

