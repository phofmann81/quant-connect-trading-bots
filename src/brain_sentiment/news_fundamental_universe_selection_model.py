from AlgorithmImports import *


class NewsFundamentalUniverseSelectionModel(UniverseSelectionModel):
    def __init__(self, algorithm):
        super().__init__()
        self.fundamental_symbols = []
        self.previous_closes = {}
        self.algorithm = algorithm

    def CreateUniverses(self, algorithm):
        def fundamental_universe_selection(
            fundamental: List[Fundamental],
        ) -> List[Symbol]:
            # Sort by dollar volume and select top 100
            sorted_by_dollar_volume = sorted(
                fundamental, key=lambda x: x.dollar_volume, reverse=True
            )

            high_volume = [c for c in sorted_by_dollar_volume[:500]]

            selected_symbols = []
            for stock in high_volume:
                symbol = stock.Symbol

                # Check if we have a previous close price
                if symbol in self.previous_closes:
                    previous_close = self.previous_closes[symbol]
                    if previous_close > 0:
                        movement = abs((stock.price - previous_close) / previous_close)
                        if movement >= 0.03:  # At least 3% movement
                            selected_symbols.append(symbol)

                # Update previous close price
                self.previous_closes[symbol] = stock.price
            self.fundamental_symbols = selected_symbols
            return Universe.UNCHANGED

        return [
            CoarseFundamentalUniverse(
                algorithm.universe_settings, fundamental_universe_selection
            )
        ]
