# region imports
from AlgorithmImports import *
from QuantConnect.DataSource import *
from brain_sentiment_alpha_model import BrainSentimentAlphaModel
import statistics as s
# endregion

class DeterminedOrangeSalmon(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2024, 1, 1)
        self.set_cash(100000)
        self.universe_settings.resolution = Resolution.DAILY
        self._universe = self.add_universe(BrainSentimentIndicatorUniverse, self.universe_selection)
        self.add_alpha(BrainSentimentAlphaModel())
        self.set_portfolio_construction(EqualWeightingPortfolioConstructionModel())
        self.add_risk_management(TrailingStopRiskManagementModel(0.05))
        self.set_execution(ImmediateExecutionModel())

    def universe_selection(self, alt_coarse: List[BrainSentimentIndicatorUniverse]) -> List[Symbol]:
        # Extract and sort symbols based on sentimental_buzz_volume_7_days
        
        top_25_buzz = sorted(
            [(d.symbol, d.sentimental_buzz_volume_7_days) for d in price_filtered if d.sentimental_buzz_volume_7_days],
            key=lambda x: x[1],  # Sort by buzz volume
            reverse=True
        )[:25]
        
        selected = [t[0] for t in top_25_buzz]
        self.debug(selected)
        return selected 



