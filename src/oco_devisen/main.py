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
        self.bar_window = RollingWindow[QuoteBar](
            61
        )  # TODO learn how to use consolidator for this
        self._atr = self.atr(self._eur_usd_symbol, Resolution.Minute)

        self.pip_size = self._eur_usd.symbol_properties.minimum_price_variation * 10
        self.pip_size_breakout_padding = self.pip_size * 2
        self.lot_size = (
            int(1 / self._eur_usd.symbol_properties.minimum_price_variation) + 1
        )
        self.total_trades = 0
        self.winning_trades = 0
        self.traded_today = False

        self.schedule.on(
            self.date_rules.every_day(), self.time_rules.at(22, 59), self.liquidate
        )
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.at(23, 59),
            self.reset_traded_today,
        )

    def reset_traded_today(self):
        self.traded_today = False

    def pip_value(self, current_price):
        return (self.pip_size / current_price) * self.lot_size

    def is_place_order_time(self) -> bool:
        return time(9, 0) > self.time.time() > time(8, 00)

    # TODO guard against running out of margin
    def position_size(self, stop_loss_distance, bar):
        risk_per_trade = self.portfolio.total_portfolio_value * 0.01
        risk_of_pip_distance = stop_loss_distance * bar.close
        lots = risk_per_trade / risk_of_pip_distance
        return lots

    def stop_loss_distance(self, bar, direction: str):
        if direction == "long":
            return bar.close - self.stop_loss_price_long()
        if direction == "short":
            return self.stop_loss_price_short() - bar.close

    def stop_loss_price_long(self):
        return self.last_60_min_low() - self._atr.current.value

    def stop_loss_price_short(self):
        return self.last_60_min_high() + self._atr.current.value

    def take_profit_price_long(self, bar):
        return bar.close + (
            self.stop_loss_distance(bar, "long")
            * float(self.get_parameter("reward_factor"))
        )

    def take_profit_price_short(self, bar):
        return bar.close - (
            self.stop_loss_distance(bar, "short")
            * float(self.get_parameter("reward_factor"))
        )

    def last_60_min_low(self):
        return min(bar.low for bar in list(self.bar_window)[1:])

    def last_60_min_high(self):
        return max(bar.high for bar in list(self.bar_window)[1:])

    def break_out(self, direction: str) -> bool:
        if direction == "long":
            return (
                self.bar_window[0].close
                > self.last_60_min_high() + self.pip_size_breakout_padding
            )
        if direction == "short":
            return (
                self.bar_window[0].close
                < self.last_60_min_low() - self.pip_size_breakout_padding
            )

    def on_data(self, data: Slice):
        if self.traded_today or not data.contains_key(self._eur_usd_symbol):
            return

        bar = data[self._eur_usd_symbol]

        self.bar_window.add(bar)

        if not self.portfolio.invested and self.is_place_order_time():
            if self.break_out(direction="long"):
                self.market_order(
                    symbol=self._eur_usd_symbol,
                    quantity=self.position_size(
                        stop_loss_distance=self.stop_loss_distance(
                            bar=bar, direction="long"
                        ),
                        bar=bar,
                    ),
                )
                take_profit_ticket = self.LimitOrder(
                    self._eur_usd_symbol,
                    -self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.take_profit_price_long(bar=bar),
                )
                stop_loss_ticket = self.StopMarketOrder(
                    self._eur_usd_symbol,
                    -self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.stop_loss_price_long(),
                )
                self.register_oco_orders(take_profit_ticket, stop_loss_ticket)

            elif self.break_out(direction="short"):
                # TODO refactor into bracket order to remove duplication
                self.market_order(
                    symbol=self._eur_usd_symbol,
                    quantity=-self.position_size(
                        self.stop_loss_distance(bar=bar, direction="short"), bar=bar
                    ),
                )
                take_profit_ticket = self.LimitOrder(
                    self._eur_usd_symbol,
                    self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.take_profit_price_short(bar=bar),
                )
                stop_loss_ticket = self.StopMarketOrder(
                    self._eur_usd_symbol,
                    self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.stop_loss_price_short(),
                )
                self.register_oco_orders(take_profit_ticket, stop_loss_ticket)

    def register_oco_orders(self, take_profit_ticket, stop_loss_ticket):
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
            else:
                self.total_trades += 1
                self.traded_today = True

    def on_end_of_algorithm(self):
        if self.total_trades > 0:
            hit_rate = self.winning_trades / self.total_trades
            self.debug(f"Hit Rate: {hit_rate:.2%}")
