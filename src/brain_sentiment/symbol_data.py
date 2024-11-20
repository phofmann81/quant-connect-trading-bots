# region imports
from AlgorithmImports import *

# endregion


# Your New Python File
class SymbolData:

    def __init__(self, algorithm: QCAlgorithm, symbol: Symbol) -> None:
        self.algorithm = algorithm
        self.ema_20 = algorithm.EMA(symbol=symbol, period=20)
        self.ema_50 = algorithm.EMA(symbol=symbol, period=50)
        self.ema_200 = algorithm.EMA(symbol=symbol, period=200)
        self.true_range = algorithm.tr(symbol=symbol, resolution=Resolution.Hour)
        self.bar_window = RollingWindow[TradeBar](3)

    def dispose(self, symbol) -> None:
        self.algorithm.remove_security(symbol)

    def update_bar(self, bar):
        self.bar_window.add(bar)
