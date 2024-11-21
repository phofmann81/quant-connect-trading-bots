from AlgorithmImports import *

idx = [
    "QQQ",
    "SPY",
    "DIA",
]

us_indices_symbols = [
    Symbol.create(ticker, SecurityType.EQUITY, Market.USA) for ticker in idx
]
