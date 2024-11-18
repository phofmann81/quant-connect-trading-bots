# region imports
from AlgorithmImports import *
from heapq import nlargest


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
        data_with_buzz = [
            x
            for x in data
            if x.sentimental_buzz_volume_7_days and x.sentimental_buzz_volume_7_days > 1
        ]
        # Find intersection with fundamental symbols
        buzz_symbols = {d.symbol for d in data_with_buzz}
        intersection = buzz_symbols & set(
            self.fundamental_universe_ref.fundamental_symbols
        )

        # # Prepare heaps for top positive and negative sentiments
        # top_positive = []
        # top_negative = []

        # for d in data_with_buzz:
        #     if d.symbol in intersection:
        #         if d.sentiment_7_days > 0:
        #             top_positive.append((d.sentiment_7_days, d))
        #         elif d.sentiment_7_days < 0:
        #             top_negative.append((d.sentiment_7_days, d))

        # # Select top 25 from each category
        # top_25_positive = nlargest(25, top_positive, key=lambda x: x[0])
        # top_25_negative = nlargest(25, top_negative, key=lambda x: x[0])

        # # Extract symbols from the top selections
        # selected_symbols = [d.symbol for _, d in top_25_positive + top_25_negative]

        # return selected_symbols
        return list(intersection)
