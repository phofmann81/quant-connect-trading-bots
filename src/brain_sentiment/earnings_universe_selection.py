# region imports
from AlgorithmImports import *

# endregion


# Your New Python File
class EarningsUniverseSelection:
    def __init__(self, algorithm, fundamental_universe_ref):
        self.algorithm = algorithm
        self.fundamental_universe_ref = fundamental_universe_ref

    def universe_selection_filter(
        self, earnings: List[EODHDUpcomingEarnings]
    ) -> List[Symbol]:
        symbols = []

        return [
            d.symbol
            for d in earnings
            if d.symbol in self.fundamental_universe_ref.fundamental_symbols
            and self.algorithm.time
            <= d.report_date
            <= self.algorithm.time + timedelta(1)
            and d.estimate
            and d.estimate > 0
        ]
