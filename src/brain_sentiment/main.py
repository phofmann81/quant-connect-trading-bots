from AlgorithmImports import *
from QuantConnect.DataSource import *
from brain_sentiment_alpha_model import BrainSentimentAlphaModel
from fundamental_universe_selection_model import FundamentalUniverseSelectionModel
from brain_sentiment_universe_selection_model import (
    BrainSentimentUniverseSelectionModel,
)


class DeterminedOrangeSalmon(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2024, 10, 15)
        self.set_cash(100000)
        self.set_time_zone("Europe/Berlin")
        self.universe_settings.resolution = Resolution.MINUTE
        fundamental_universe_selection = FundamentalUniverseSelectionModel()
        self.add_universe_selection(fundamental_universe_selection)
        sentiment_universe_selection = BrainSentimentUniverseSelectionModel(
            fundamental_universe_selection, self
        )
        self.add_universe(
            BrainSentimentIndicatorUniverse,
            sentiment_universe_selection.universe_selection,
        )
        self.add_alpha(BrainSentimentAlphaModel())
        self.set_portfolio_construction(
            AccumulativeInsightPortfolioConstructionModel(
                rebalance=None, portfolioBias=PortfolioBias.LONG_SHORT, percent=0.1
            )
        )
        # self.add_risk_management(TrailingStopRiskManagementModel(0.02))
        self.add_risk_management(NullRiskManagementModel())
        self.set_execution(ImmediateExecutionModel())
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.at(21, 59),
            self.liquidate_at_end_of_day,
        )

    def liquidate_at_end_of_day(self):
        self.insights.cancel(self.insights)
        self.liquidate()
