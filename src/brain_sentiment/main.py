# region imports
from AlgorithmImports import *
from QuantConnect.DataSource import *
from brain_sentiment_alpha_model import BrainSentimentAlphaModel
import statistics as s
from news_fundamental_universe_selection_model import (
    NewsFundamentalUniverseSelectionModel,
)
from brain_sentiment_universe_selection_model import (
    BrainSentimentUniverseSelectionModel,
)

# from watch_list_11_19 import symbols
from us_indices import us_indices_symbols
from earnings_universe_selection import EarningsUniverseSelection

# endregion


# TODO move universe selection into framework model


# TODO add filter for strong negative or positive sentiment
class DeterminedOrangeSalmon(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2024, 11, 18)
        # self.set_end_date(2024,11, 19)
        self.set_cash(100000)
        self.set_time_zone(
            "America/New_York"
        )  # trigger universe selection 7am/8am new york time for price movements over night
        self.universe_settings.resolution = Resolution.MINUTE

        # ensure market close/open gaps are properly computed
        news_fundamental_universe_selection = NewsFundamentalUniverseSelectionModel(
            self
        )
        self.add_universe_selection(news_fundamental_universe_selection)

        sentiment_universe_selection = BrainSentimentUniverseSelectionModel(
            news_fundamental_universe_selection, self
        )
        self.add_universe(
            BrainSentimentIndicatorUniverse,
            sentiment_universe_selection.universe_selection,
        )
        self.add_universe_selection(ManualUniverseSelectionModel(us_indices_symbols))
        self.add_universe(
            EODHDUpcomingEarnings,
            EarningsUniverseSelection(
                self, news_fundamental_universe_selection
            ).universe_selection_filter,
        )
        self.add_alpha(BrainSentimentAlphaModel())
        self.set_portfolio_construction(
            AccumulativeInsightPortfolioConstructionModel(
                rebalance=None, portfolioBias=PortfolioBias.LONG_SHORT, percent=0.1
            )
        )
        self.add_risk_management(TrailingStopRiskManagementModel(0.03))
        # self.add_risk_management(NullRiskManagementModel())
        self.set_execution(ImmediateExecutionModel())
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.at(15, 59),
            self.liquidate_at_end_of_day,
        )

    def liquidate_at_end_of_day(self):
        self.insights.cancel(self.insights)
        self.liquidate()
