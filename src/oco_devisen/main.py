# region imports
from AlgorithmImports import *

# endregion


class OcODevisenStrategy(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2023, 4, 14)
        self.set_cash(100000)
        berlin_time_zone_utc_plus_2 = "Europe/Berlin"
        self.set_time_zone(berlin_time_zone_utc_plus_2)
        self._eur_usd = self.add_forex(ticker="EURUSD", resolution=Resolution.MINUTE)
        self._eur_usd_symbol = self._eur_usd.symbol
        self.orders = {}
        self.pip_size_breakout_padding = 0.2
        self.stop_loss_pip_size = 5  # could be related to atr TODO parameterize
        self.bar_window = RollingWindow[TradeBar](
            61
        )  # TODO learn how to use consolidator for this
        self._atr = self.atr(self._eur_usd_symbol, Resolution.Minute)

        self.pip_size = (
            self._eur_usd.symbol_properties.minimum_price_variation
        )  # 1e-05 for eur-usd
        self.lot_size = int(1 / self.pip_size) + 1
        print("stop here")

    def pip_value(self, current_price):
        (self.pip_size / current_price) * self.lot_size

    def is_place_order_time(self) -> bool:
        return time(9, 0) > self.time.time() > time(8, 00)

    # TODO check if this works the same way for forex
    # need to convert the pip distance into lot
    # if you want to risk 100 euro
    # and one lot is 100.000 euro -> 0.001 lot
    def position_size(self, stop_loss_distance):
        risk_per_trade = self.portfolio.total_portfolio_value * 0.01
        pip_size = stop_loss_distance
        pip_risk = pip_size * self.pip_value(self._eur_usd_symbol.current_price)
        lots = risk_per_trade / pip_risk
        return lots

    def stop_loss_distance(self, bar):
        return bar.close - self.stop_loss_price_long()

    def stop_loss_price_long(self):
        return min(bar.low for bar in self.bar_window[:-1]) - self._atr.current.value

    def stop_loss_price_short(self, bar):
        return bar.close + stop_loss_distance(bar)

    def take_profit_price_long(self, bar):
        return bar.close + stop_loss_distance * float(parameters.get("reward_factor"))

    def take_profit_price_short(self, bar):
        return bar.close - (
            self.stop_loss_distance(bar) * float(parameters.get("reward_factor"))
        )

    def break_out(self, direction: str) -> bool:
        if direction == "long":
            return (
                self.bar_window[0].close
                > max(bar.high for bar in self.bar_window[:-1])
                + self.pip_size_breakout_padding
            )
        if direction == "short":
            return (
                self.bar_window[0].close
                < min(bar.low for bar in self.bar_window[:-1])
                - self.pip_size_breakout_padding
            )

    def on_data(self, data: Slice):
        if not self._eur_usd_symbol in data.bars:
            return

        bar = data.bars[self._eur_usd_symbol]

        self.bar_window.add(bar)
        if not self.portfolio.invested and self.is_place_order_time():
            if self.break_out(direction="long"):
                self.market_order(
                    symbol=self._eur_usd_symbol,
                    quantity=self.position_size(self.stop_loss_distance(bar=bar)),
                )  # enter with market order with 1% portfolio
                # TODO self.traded_today = True
                # register take profit
                take_profit_ticket = self.LimitOrder(
                    self._eur_usd_symbol,
                    -self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.take_profit_price_long(bar=bar),
                )
                # register stop loss
                stop_loss_ticket = self.StopMarketOrder(
                    symbol,
                    -self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.stop_loss_price_long(bar=data),
                )
                self.register_oco_orders(take_profit_ticket, stop_loss_ticket)

            elif self.breakout(direction="short"):
                # TODO refactor into bracket order to remove duplication
                self.market_order(
                    symbol=self._eur_usd_symbol,
                    quantity=-self.position_size(self.stop_loss_distance(bar=data)),
                )  # enter with market order with 1% portfolio
                # TODO self.traded_today = True
                # register take profit
                take_profit_ticket = self.LimitOrder(
                    self._eur_usd_symbol,
                    self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.take_profit_price_long(bar=data),
                )
                # register stop loss
                stop_loss_ticket = self.StopMarketOrder(
                    symbol,
                    self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.stop_loss_price_long(bar=data),
                )
                self.register_oco_orders(take_profit_ticket, stop_loss_ticket)

    def register_oco_orders(self, take_profit_ticket, stop_loss_ticket):
        # set up order index so we can cancel the opposite once filled
        self.orders[stop_loss_ticket.order_id] = {
            "oco_order_id": take_profit_ticket.order_id,
            "type": "stop_loss",
        }
        self.orders[take_profit_ticket.order_id] = {
            "oco_order_id": stop_loss_ticket.order_id,
            "type": "take_profit",
        }
        return None

    def on_order_event(self, order_event: OrderEvent):
        if order_event.status == OrderStatus.FILLED:
            if (order := self.orders.get(order_event.order_id)) is not None:  # exit
                self.transactions.cancel_order(order["oco_order_id"])
                if order["type"] == "take_profit":
                    self.winning_trades += 1
            else:  # plot entry
                self.total_trades += 1
