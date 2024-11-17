# region imports
from AlgorithmImports import *
from QuantConnect.DataSource import *
from brain_sentiment_alpha_model import BrainSentimentAlphaModel
import statistics as s
from fundamental_universe_selection_model import FundamentalUniverseSelectionModel
from brain_sentiment_universe_selection_model import (
    BrainSentimentUniverseSelectionModel,
)

# endregion


# TODO move universe selection into framework model


# TODO add filter for strong negative or positive sentiment
class DeterminedOrangeSalmon(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2024, 1, 1)
        self.set_cash(100000)

        self.universe_settings.resolution = Resolution.DAILY
        fundamental_universe_selection = FundamentalUniverseSelectionModel()
        self.add_universe_selection(fundamental_universe_selection)
        sentiment_universe_selection = BrainSentimentUniverseSelectionModel(
            fundamental_universe_selection
        )
        self.add_universe(
            BrainSentimentIndicatorUniverse,
            sentiment_universe_selection.universe_selection,
        )

        self.add_alpha(BrainSentimentAlphaModel())
        self.set_portfolio_construction(EqualWeightingPortfolioConstructionModel())
        self.add_risk_management(TrailingStopRiskManagementModel(0.05))
        self.set_execution(ImmediateExecutionModel())

    def on_securities_changed(self, changes):
        for added in changes.added_securities:
            self.add_data(BrainSentimentIndicator7Day, added.symbol)

    def on_data(self, data):
        for dataset_symbol, data_point in data.get(BrainSentimentIndicator7Day).items():
            self.debug(
                f"{dataset_symbol} sentiment at {data.time}: {data_point.sentiment}"
            )
