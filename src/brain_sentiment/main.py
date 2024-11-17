# region imports
from AlgorithmImports import *
from QuantConnect.DataSource import *
from brain_sentiment_alpha_model import BrainSentimentAlphaModel
import statistics as s

# endregion


class DeterminedOrangeSalmon(QCAlgorithm):

    _fundamental = []

    def initialize(self):
        self.set_start_date(2024, 1, 1)
        self.set_cash(100000)
        self.universe_settings.resolution = Resolution.DAILY
        self.add_universe(self.fundamental_universe_selection)
        self.add_universe(
            BrainSentimentIndicatorUniverse, self.sentiment_universe_selection
        )
        self.add_alpha(BrainSentimentAlphaModel())
        self.set_portfolio_construction(EqualWeightingPortfolioConstructionModel())
        self.add_risk_management(TrailingStopRiskManagementModel(0.05))
        self.set_execution(ImmediateExecutionModel())

    def fundamental_universe_selection(
        self, fundamental: List[Fundamental]
    ) -> List[Symbol]:
        sorted_by_dollar_volume = sorted(
            fundamental, key=lambda x: x.dollar_volume, reverse=True
        )
        self._fundamental = [c.symbol for c in sorted_by_dollar_volume[:100]]
        return Universe.UNCHANGED

    def sentiment_universe_selection(
        self, alt_coarse: List[BrainSentimentIndicatorUniverse]
    ) -> List[Symbol]:
        # Extract and sort symbols based on sentimental_buzz_volume_7_days

        data_with_buzz = list(
            filter(lambda x: x.sentimental_buzz_volume_7_days, alt_coarse)
        )

        buzz_symbols = [d.symbol for d in data_with_buzz]

        intersection = set(self._fundamental) & set(buzz_symbols)

        intersected_buzz_data = list(
            filter(lambda x: x.symbol in intersection, data_with_buzz)
        )

        top_25_buzz = sorted(
            [
                (d.symbol, d.sentimental_buzz_volume_7_days)
                for d in intersected_buzz_data
                if d.sentimental_buzz_volume_7_days
            ],
            key=lambda x: x[1],  # Sort by buzz volume
            reverse=True,
        )[:25]

        selected = [t[0] for t in top_25_buzz]
        self.debug(selected)
        return selected

    def on_securities_changed(self, changes):
        for added in changes.added_securities:
            self.add_data(BrainSentimentIndicator7Day, added.symbol)

    def on_data(self, data):
        for dataset_symbol, data_point in data.get(BrainSentimentIndicator7Day).items():
            self.debug(
                f"{dataset_symbol} sentiment at {data.time}: {data_point.sentiment}"
            )
