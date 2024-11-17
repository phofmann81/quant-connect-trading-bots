# region imports
from AlgorithmImports import *
from QuantConnect.DataSource import *
from symbol_data import SymbolData

# endregion


# Your New Python File
class BrainSentimentAlphaModel(AlphaModel):

    symbol_data_by_symbol = {}

    def update(self, algorithm: QCAlgorithm, slice: Slice) -> List[Insight]:
        insights = []

        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            # Update trade direction based on updated data
            if (
                slice.contains_key(symbol_data.dataset_symbol)
                and slice[symbol_data.dataset_symbol] is not None
            ):
                sentiment = slice[symbol_data.dataset_symbol].sentiment
                symbol_data.update(sentiment)

            # Ensure we have security data in the current slice to avoid stale fill
            if not (slice.contains_key(symbol) and slice[symbol] is not None):
                continue

            # Buy if sentiment increase, liquidate otherwise to ride on the popularity of the equity
            if (
                symbol_data.target_direction
                in [InsightDirection.UP, InsightDirection.DOWN]
                and not algorithm.portfolio[symbol].invested
                and algorithm.time.time() == time(21, 0)
            ):
                insights.append(
                    Insight.price(
                        symbol, timedelta(hours=1), symbol_data.target_direction
                    )
                )
        return insights

    def on_securities_changed(
        self, algorithm: QCAlgorithm, changes: SecurityChanges
    ) -> None:
        for security in changes.added_securities:
            symbol = security.symbol
            self.symbol_data_by_symbol[symbol] = SymbolData(algorithm, symbol)

        for security in changes.removed_securities:
            symbol_data = self.symbol_data_by_symbol.pop(security.symbol, None)
            if symbol_data:
                symbol_data.dispose()
