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
        self.set_end_date(2024, 11, 15)
        self.set_cash(100000)
        self.set_time_zone("Europe/Berlin")
        self.universe_settings.resolution = Resolution.MINUTE
        fundamental_universe_selection = FundamentalUniverseSelectionModel()
        self.add_universe_selection(fundamental_universe_selection)
        sentiment_universe_selection = BrainSentimentUniverseSelectionModel(
            fundamental_universe_selection
        )
        self.add_universe(
            BrainSentimentIndicatorUniverse,
            sentiment_universe_selection.universe_selection,
        )
        # self.symbols = {}
        self.add_alpha(BrainSentimentAlphaModel())
        self.set_portfolio_construction(EqualWeightingPortfolioConstructionModel())
        self.add_risk_management(TrailingStopRiskManagementModel(0.03))
        self.set_execution(ImmediateExecutionModel())
        self.schedule.on(
            self.date_rules.every_day(), self.time_rules.at(21, 59), self.liquidate
        )

    # def on_securities_changed(self, changes):
    #     for added in changes.added_securities:
    #         self.symbols[added.symbol] = self.add_data(BrainSentimentIndicator7Day, added.symbol).symbol

    #     for removed in changes.removed_securities:
    #         self.remove_security(removed.symbol)
    #         self.remove_security(self.symbols[removed.symbol])
    #         self.symbols.pop(removed.symbol)

    # def on_data(self, slice):
    # self.debug("sentiments: \n -------------")
    # for dataset_symbol, data_point in slice.get(BrainSentimentIndicator7Day).items():
    #     self.debug(
    #         f"{dataset_symbol} sentiment at {slice.time}: {data_point.sentiment}"
    #     )
    # self.debug("fundamentals: \n ------------------")
    # for security in self.active_securities.values:
    #     self.debug(
    #         f"symbol: {security.symbol.value}\n"
    #         f"dollar volume: {security.fundamentals.dollar_volume}\n"
    #     )
