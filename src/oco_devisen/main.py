# region imports
from AlgorithmImports import *

# endregion


class OcODevisenStrategy(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2023, 4, 14)
        self.set_cash(100000)
        self._eur_usd_symbol = self.add_forex(
            ticker="EURUSD", resolution=Resolution.MINUTE
        ).symbol
        self.orders = {}
        self.pip_size = 0.00001

    def is_place_order_time(self) -> bool:
        return self.time.time() == time(7, 59)

    # TODO check if this works the same way for forex
    def get_position_size(self, stop_loss_distance):
        risk_per_trade = self.portfolio.total_portfolio_value * 0.01
        risk_per_share = stop_loss_distance
        position_size = risk_per_trade / risk_per_share
        return int(position_size)

    def stop_loss_distance(self, bar):
        return (bar.high + self.pip_size) - (bar.low - self.pip_size)

    def get_take_profit_price_long(self, bar):
        return bar.close + (self.stop_loss_distance(bar) * 1, 5)  # TODO parameterize

    def get_stop_loss_price_long(self, bar):
        return bar.close - self.stop_loss_distance(bar)

    def get_take_profit_price_short(self, bar):
        return bar.close - (self.stop_loss_distance(bar) * 1, 5)  # TODO parameterize

    def break_out_long(self, bar):
        pass

    def on_data(self, data: Slice):
        if not self.portfolio.invested and self.is_place_order_time():
            if self.break_out_long(data.Bar):  # TODO implement
                self.market_order(
                    symbol=self._eur_usd_symbol,
                    quantity=self.get_position_size(
                        self.stop_loss_distance(bar=data.Bar)
                    ),
                )  # enter with market order with 1% portfolio
                # TODO self.traded_today = True
                # register take profit
                take_profit_ticket = self.LimitOrder(
                    self._eur_usd_symbol,
                    -self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.get_take_profit_price_long(bar=data.Bar),
                )
                # register stop loss
                stop_loss_ticket = self.StopMarketOrder(
                    symbol,
                    -self.Portfolio[self._eur_usd_symbol].Quantity,
                    self.get_stop_loss_price_long(bar=data.Bar),
                )
                self.register_oco_orders(take_profit_ticket, stop_loss_ticket)
        else:
            pass

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
