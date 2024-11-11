from AlgorithmImports import *
from pytz import timezone


class OneRTrailingStopRiskManagementModel(RiskManagementModel):
    def __init__(self, pip_size: float):
        self.pip_size = pip_size
        self.trailing_stop_distance = round(6 * self.pip_size, 6)
        self.highest_profit_price = {}  # Track highest price reached for each symbol
        self.initial_stop_price = {}  # Track initial stop loss price for each symbol
        self.current_trailing_stop = {}  # Track current trailing stop for each symbol
        time_zone_id = "Europe/Berlin"
        self.berlin_tzinfo = timezone(time_zone_id)

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
                self.initial_stop_price.pop(symbol, None)
                self.current_trailing_stop.pop(symbol, None)
                continue

            holding = security.Holdings
            current_value = holding.absolute_holdings_value / holding.quantity
            berlin_time = algorithm.Time.astimezone(self.berlin_tzinfo).time()

            # Set initial stop loss and take profit if just invested
            if symbol not in self.highest_profit_price:
                self.highest_profit_price[symbol] = (
                    holding.absolute_holdings_cost / holding.quantity
                )
                self.initial_stop_price[symbol] = (
                    self.highest_profit_price[symbol] - self.trailing_stop_distance
                    if holding.IsLong
                    else self.highest_profit_price[symbol] + self.trailing_stop_distance
                )
                self.current_trailing_stop[symbol] = self.initial_stop_price[symbol]

            # Update the highest profit price based on current price if it's favorable
            if holding.IsLong:
                if current_value > self.highest_profit_price[symbol]:
                    self.highest_profit_price[symbol] = current_value

                # Adjust trailing stop by 1R each time unrealized profits increase by 1R
                if (
                    self.current_trailing_stop[symbol]
                    <= self.highest_profit_price[symbol]
                    - 2 * self.trailing_stop_distance
                ):
                    self.current_trailing_stop[symbol] = (
                        self.highest_profit_price[symbol] - self.trailing_stop_distance
                    )

                    algorithm.Debug(
                        f"Adjusted trailing stop for {symbol} to {self.current_trailing_stop[symbol]}"
                    )

                # Check if the trailing stop has been hit
                if current_value <= self.current_trailing_stop[symbol]:
                    risk_adjusted_targets.append(PortfolioTarget(symbol, 0))
                    algorithm.Debug(
                        f"Trailing stop loss triggered for {symbol} at {self.current_trailing_stop[symbol]}"
                    )

            else:  # Short position
                if current_value < self.highest_profit_price[symbol]:
                    self.highest_profit_price[symbol] = current_value

                # Adjust trailing stop by 1R each time unrealized profits increase by 1R for shorts
                if (
                    self.current_trailing_stop[symbol]
                    >= self.highest_profit_price[symbol]
                    + 2 * self.trailing_stop_distance
                ):
                    self.current_trailing_stop[symbol] = (
                        self.highest_profit_price[symbol] + self.trailing_stop_distance
                    )
                    algorithm.Debug(
                        f"Adjusted trailing stop for {symbol} to {self.current_trailing_stop[symbol]}"
                    )

                # Check if the trailing stop has been hit
                if current_value >= self.current_trailing_stop[symbol]:
                    risk_adjusted_targets.append(PortfolioTarget(symbol, 0))
                    algorithm.Debug(
                        f"Trailing stop loss triggered for {symbol} at {self.current_trailing_stop[symbol]}"
                    )

                # liquidate all open positions at 2pm berlin time
            if berlin_time == time(14, 00):
                risk_adjusted_targets.append(PortfolioTarget(symbol, 0))

        return risk_adjusted_targets
