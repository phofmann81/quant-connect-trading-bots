# region imports
from AlgorithmImports import *


class BrainSentimentUniverseSelectionModel:
    def __init__(self, fundamental_universe_ref):
        """
        Parameters:
        - fundamental_symbols_ref: A reference to the list of fundamental symbols from FundamentalUniverseSelectionModel.
        """
        self.fundamental_universe_ref = fundamental_universe_ref

    def universe_selection(
        self,
        data: List[BrainSentimentIndicatorUniverse],
    ) -> List[Symbol]:
        # Filter data with valid sentimental buzz
        data_with_buzz = [x for x in data if x.sentimental_buzz_volume_7_days]

        # Find intersection with fundamental symbols
        buzz_symbols = {d.symbol for d in data_with_buzz}
        intersection = buzz_symbols & set(
            self.fundamental_universe_ref.fundamental_symbols
        )

        # Filter intersected data
        intersected_buzz_data = [d for d in data_with_buzz if d.symbol in intersection]

        # Sort by sentiment and select the top 25
        top_25_buzz = sorted(
            intersected_buzz_data,
            key=lambda d: d.sentimental_buzz_volume_7_days,
            reverse=True,
        )[:25]

        # Return the selected symbols
        return [d.symbol for d in top_25_buzz]
