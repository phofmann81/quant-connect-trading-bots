from AlgorithmImports import *


class FundamentalUniverseSelectionModel(UniverseSelectionModel):
    def __init__(self):
        super().__init__()
        self.fundamental_symbols = []

    def CreateUniverses(self, algorithm):
        def fundamental_universe_selection(
            fundamental: List[Fundamental],
        ) -> List[Symbol]:
            # Sort by dollar volume and select top 100
            sorted_by_dollar_volume = sorted(
                fundamental, key=lambda x: x.dollar_volume, reverse=True
            )
            self.fundamental_symbols = [c.symbol for c in sorted_by_dollar_volume[:100]]
            return Universe.UNCHANGED

        return [
            CoarseFundamentalUniverse(
                algorithm.universe_settings, fundamental_universe_selection
            )
        ]
