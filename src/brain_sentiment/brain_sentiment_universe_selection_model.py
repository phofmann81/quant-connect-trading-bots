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
        data_with_buzz_and_sentiment = [
            x for x in data if x.sentimental_buzz_volume_7_days and x.sentiment_7_days
        ]
        # Find intersection with fundamental symbols
        buzz_symbols = {d.symbol for d in data_with_buzz_and_sentiment}
        intersection = buzz_symbols & set(
            self.fundamental_universe_ref.fundamental_symbols
        )

        # compute impact score: sentiment_7_days * sentimental_buzz_volume_7_days
        impact_list = []
        for d in data_with_buzz_and_sentiment:
            if d.symbol in intersection:
                impact_score = (
                    abs(d.sentiment_7_days) * d.sentimental_buzz_volume_7_days
                )
                impact_list.append((d.symbol, impact_score))

        top_25_impact = nlargest(25, impact_list, key=lambda x: x[1])

        return [symbol for symbol, _ in top_25_impact]

        # # Prepare heaps for top positive and negative sentiments
        # top_positive = []
        # top_negative = []

        # for d in data_with_buzz:
        #     if d.symbol in intersection:
        #         if abs(d.sentiment_7_days) > 0.4:
        #             top_positive.append((d.sentiment_7_days, d))
        #         elif d.sentiment_7_days < 0:
        #             top_negative.append((d.sentiment_7_days, d))

        # # Select top 25 from each category
        # top_25_positive = nlargest(25, top_positive, key=lambda x: x[0])
        # top_25_negative = nlargest(25, top_negative, key=lambda x: x[0])

        # # Extract symbols from the top selections
        # selected_symbols = [d.symbol for _, d in top_25_positive + top_25_negative]

        # return selected_symbols
        # TODO filter by something, we're returning too many, too many data points to process.
        # return list(intersection)
