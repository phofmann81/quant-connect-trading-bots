from AlgorithmImports import *
from pytz import timezone
from operator import sub, add, gt, lt, ge, le


class OneRTrailingStopRiskManagementModel(RiskManagementModel):
    def __init__(self):
        self.highest_profit_price = {}  # Track highest price reached for each symbol
        self.current_trailing_stop = {}  # Track current trailing stop for each symbol
        time_zone_id = "Europe/Berlin"
        self.berlin_tzinfo = timezone(time_zone_id)
        self.trailing_stop_distance = {}
        self.opposite_order_triggered = {}

    def ManageRisk(
        self, algorithm: QCAlgorithm, targets: List[PortfolioTarget]
    ) -> List[PortfolioTarget]:
        risk_adjusted_targets = []

        for kvp in algorithm.Securities:
            symbol = kvp.Key
            security = kvp.Value

            if not security.Invested:
                # Reset tracking when not invested
                self.highest_profit_price.pop(symbol, None)
                self.current_trailing_stop.pop(symbol, None)
                self.opposite_order_triggered.pop(symbol, None)
                continue

            holding = security.Holdings
            current_value = holding.absolute_holdings_value / abs(holding.quantity)
            berlin_time = algorithm.Time.astimezone(self.berlin_tzinfo).time()

            if symbol not in self.highest_profit_price:
                self.initialize_holding(symbol, holding)

            self.update_high_profit_price(holding.IsLong, symbol, current_value)

            self.adjust_trailing_stop(holding.IsLong, symbol, holding, algorithm)

            risk_adjusted_targets = self.check_trailing_stop(
                holding, symbol, current_value, algorithm, risk_adjusted_targets
            )

            # liquidate all open positions at 2pm berlin time
            entry_time = int(algorithm.get_parameter("entry_time")) + 6
            if entry_time > 24:
                entry_time = entry_time - 24
            if berlin_time == time(entry_time, 0):
                risk_adjusted_targets.append(PortfolioTarget(symbol, 0))

        return risk_adjusted_targets

    def initialize_holding(self, symbol, holding):
        op = sub if holding.IsLong else add
        self.highest_profit_price[symbol] = holding.absolute_holdings_cost / abs(
            holding.quantity
        )
        self.current_trailing_stop[symbol] = op(
            self.highest_profit_price[symbol], self.trailing_stop_distance[symbol]
        )

    def update_high_profit_price(self, is_long: bool, symbol, current_value):
        comp = gt if is_long else lt

        if comp(current_value, self.highest_profit_price[symbol]):
            self.highest_profit_price[symbol] = current_value

    def adjust_trailing_stop(self, is_long: bool, symbol, holding, algorithm):
        op = add if is_long else sub

        if (
            holding.unrealized_profit / abs(holding.quantity)
            >= float(algorithm.get_parameter("stop_distance_factor"))
            * self.trailing_stop_distance[symbol]
        ):

            self.current_trailing_stop[symbol] = op(
                self.highest_profit_price[symbol],
                (float(algorithm.get_parameter("stop_distance_factor")) - 1)
                * self.trailing_stop_distance[symbol],
            )

            algorithm.Debug(
                f"Adjusted trailing stop for {symbol} to {self.current_trailing_stop[symbol]}"
            )

    def check_trailing_stop(
        self,
        holding,
        symbol,
        current_value,
        algorithm,
        risk_adjusted_targets: List[PortfolioTarget],
    ) -> List[PortfolioTarget]:
        op = le if holding.IsLong else ge

        # Check if the trailing stop has been hit
        if op(current_value, self.current_trailing_stop[symbol]):
            algorithm.Debug(
                f"Trailing stop loss triggered for {symbol} at {self.current_trailing_stop[symbol]}"
            )
            if holding.unrealized_profit > 0:
                risk_adjusted_targets.append(PortfolioTarget(symbol, 0))
            else:
                if not symbol in self.opposite_order_triggered:
                    risk_adjusted_targets.append(
                        PortfolioTarget(symbol, -1 * holding.quantity)
                    )
                    self.opposite_order_triggered[symbol] = True
                    algorithm.Debug(
                        f"Opposite order issued for {symbol} at {self.current_trailing_stop[symbol]}"
                    )
        return risk_adjusted_targets
