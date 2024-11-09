# region imports
from AlgorithmImports import *
from breakout_alpha_model import BreakoutAlphaModel
from symbol_data import SymbolData

# endregion


class OcODevisenStrategy(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2024, 10, 17)

        self.set_cash(100000)

        berlin_time_zone_utc_plus_2 = "Europe/Berlin"
        self.set_time_zone(berlin_time_zone_utc_plus_2)

        self.set_brokerage_model(
            brokerage=BrokerageName.INTERACTIVE_BROKERS_BROKERAGE,
            account_type=AccountType.MARGIN,
        )

        symbols: List[Symbol] = [
            self.add_forex(ticker=currency_pair).symbol
            for currency_pair in ["EURUSD", "GBPUSD", "EURGBP"]
        ]

        self.add_universe_selection(ManualUniverseSelectionModel(symbols))
        self.universe_settings.resolution = Resolution.HOUR

        self.symbol_data: Mapping[Symbol, SymbolData] = {}

        self.pip = 0.0001  # TODO make this dependend on currency pair, this is not correct for Yen

        self.set_risk_management(TrailingStopRiskManagementModel())

        self.orders = {}
        # self.bar_window = RollingWindow[QuoteBar](
        #     61
        # )  # TODO learn how to use consolidator for this

        # self.pip_size = (
        #     self._eur_usd.symbol_properties.minimum_price_variation * 10
        # )
        # self.pip_size_breakout_padding = self.pip_size * 2
        # self.lot_size = (
        #     int(1 / self._eur_usd.symbol_properties.minimum_price_variation) + 1

    #     # )
    #     self.total_trades = 0
    #     self.winning_trades = 0
    #     self.traded_today = False

    #     #     self.schedule.on(
    #     #         self.date_rules.every_day(), self.time_rules.at(22, 59), self.liquidate
    #     #     )
    #     self.schedule.on(
    #         self.date_rules.every_day(),
    #         self.time_rules.at(23, 59),
    #         self.reset_traded_today,
    #     )

    # def reset_traded_today(self):
    #     self.traded_today = False

    # def pip_value(self, current_price):
    #     return (self.pip_size / current_price) * self.lot_size

    # def is_place_order_time(self) -> bool:
    #     return time(9, 0) > self.time.time() > time(8, 00)

    # # TODO guard against running out of margin
    # def position_size(self, stop_loss_distance, bar):
    #     risk_per_trade = self.portfolio.total_portfolio_value * 0.01
    #     risk_of_pip_distance = stop_loss_distance * bar.close
    #     lots = risk_per_trade / risk_of_pip_distance
    #     return lots

    # def stop_loss_distance(self, bar, direction: str):
    #     if direction == "long":
    #         return bar.close - self.stop_loss_price_long()
    #     if direction == "short":
    #         return self.stop_loss_price_short() - bar.close

    # def stop_loss_price_long(self):
    #     return self.last_60_min_low() - self._atr.current.value

    # def stop_loss_price_short(self):
    #     return self.last_60_min_high() + self._atr.current.value

    # def take_profit_price_long(self, bar):
    #     return bar.close + (
    #         self.stop_loss_distance(bar, "long") * float(self.get_parameter("reward_factor"))
    #     )

    # def take_profit_price_short(self, bar):
    #     return bar.close - (
    #         self.stop_loss_distance(bar, "short") * float(self.get_parameter("reward_factor"))
    #     )

    # def last_60_min_low(self):
    #     return min(bar.low for bar in list(self.bar_window)[1:])

    # def last_60_min_high(self):
    #     return max(bar.high for bar in list(self.bar_window)[1:])

    # def break_out(self, direction: str) -> bool:
    #     if direction == "long":
    #         return (
    #             self.bar_window[0].close
    #             > self.last_60_min_high() + self.pip_size_breakout_padding
    #         )
    #     if direction == "short":
    #         return (
    #             self.bar_window[0].close
    #             < self.last_60_min_low() - self.pip_size_breakout_padding
    #         )

    def get_quantity(self, quote_bar: QuoteBar) -> Mapping[str, float]:
        def get_maximum_loss(price1: float, price2: float) -> float:
            maximum_loss = round(price1 - price2, 6)
            return maximum_loss if maximum_loss != 0 else 6 * self.pip

        def calculate_max_margin() -> float:
            available_margin = self.portfolio.margin_remaining
            invested_count = sum(
                1 if self.portfolio[symbol].invested else 0
                for symbol in self.symbol_data
            )

            # Calculate margin ratio based on current investments
            margin_ratio = max(3 - invested_count, 1)
            return available_margin / margin_ratio

        def calculate_position_size(
            max_margin: float, risk_exposure: float, max_loss: float, close_price: float
        ) -> float:
            position_size = risk_exposure / (max_loss * close_price)
            return min(position_size, max_margin)

        risk_exposure = self.portfolio.total_portfolio_value * 0.01

        # Calculate maximum potential loss for buy and sell
        maximum_loss_buy = get_maximum_loss(quote_bar.close, quote_bar.low)
        maximum_loss_sell = get_maximum_loss(quote_bar.high, quote_bar.close)

        # Calculate maximum allowable margin for this trade
        max_margin = calculate_max_margin()

        # Calculate buy and sell sizes, constrained by max margin
        buy_size = calculate_position_size(
            max_margin, risk_exposure, maximum_loss_buy, quote_bar.close
        )
        sell_size = calculate_position_size(
            max_margin, risk_exposure, maximum_loss_sell, quote_bar.close
        )

        return {"buy": buy_size, "sell": sell_size}

    def on_data(self, data: Slice):

        if self.time.hour == 8:
            for symbol, symbol_data in self.symbol_data.items():
                bar = data[symbol]

                # entry tickets
                buy_stop_ticket = self.stop_market_order(
                    symbol, self.get_quantity(bar)["buy"], bar.close + self.pip * 2
                )
                sell_stop_ticket = self.stop_market_order(
                    symbol, self.get_quantity(bar)["sell"], bar.close - self.pip * 2
                )
                self.register_oco_orders(buy_stop_ticket, sell_stop_ticket)

                # stop loss tickets
                buy_stop_loss_ticket = self.stop_market_order(
                    symbol, -self.portfolio[symbol].quantity, bar.low
                )
                sell_stop_loss_ticket = self.stop_market_order(
                    symbol, -self.portfolio[symbol].quantity, bar.high
                )
                self.register_oco_orders(buy_stop_loss_ticket, sell_stop_loss_ticket)

        # self.bar_window.add(bar)

        # if not self.portfolio.invested and self.is_place_order_time():
        #     if self.break_out(direction="long"):
        #         self.market_order(
        #             symbol=self._eur_usd_symbol,
        #             quantity=self.position_size(
        #                 stop_loss_distance=self.stop_loss_distance(bar=bar, direction="long"), bar=bar
        #             ),
        #         )
        #         take_profit_ticket = self.LimitOrder(
        #             self._eur_usd_symbol,
        #             -self.Portfolio[self._eur_usd_symbol].Quantity,
        #             self.take_profit_price_long(bar=bar),
        #         )
        #         stop_loss_ticket = self.StopMarketOrder(
        #             self._eur_usd_symbol,
        #             -self.Portfolio[self._eur_usd_symbol].Quantity,
        #             self.stop_loss_price_long(),
        #         )
        #         self.register_oco_orders(take_profit_ticket, stop_loss_ticket)

        #     elif self.break_out(direction="short"):
        #         # TODO refactor into bracket order to remove duplication
        #         self.market_order(
        #             symbol=self._eur_usd_symbol,
        #             quantity=-self.position_size(
        #                 self.stop_loss_distance(bar=bar, direction="short"), bar=bar
        #             ),
        #         )
        #         take_profit_ticket = self.LimitOrder(
        #             self._eur_usd_symbol,
        #             -self.Portfolio[self._eur_usd_symbol].Quantity,
        #             self.take_profit_price_short(bar=bar),
        #         )
        #         stop_loss_ticket = self.StopMarketOrder(
        #             self._eur_usd_symbol,
        #             -self.Portfolio[self._eur_usd_symbol].Quantity,
        #             self.stop_loss_price_short(),
        #         )
        #         self.register_oco_orders(take_profit_ticket, stop_loss_ticket)

    def register_oco_orders(self, one_ticket, other_ticket):
        self.orders[one_ticket.order_id] = {
            "oco_order_id": other_ticket.order_id,
            "type": "one",
        }
        self.orders[other_ticket.order_id] = {
            "oco_order_id": one_ticket.order_id,
            "type": "other",
        }
        return None

    def on_order_event(self, order_event: OrderEvent):
        if order_event.status == OrderStatus.FILLED:
            if (order := self.orders.get(order_event.order_id)) is not None:  # exit
                self.transactions.cancel_order(order["oco_order_id"])

    # def on_end_of_algorithm(self):
    #     if self.total_trades > 0:
    #         hit_rate = self.winning_trades / self.total_trades
    #         self.debug(f"Hit Rate: {hit_rate:.2%}")

    def on_securities_changed(self, changes):
        for security in changes.AddedSecurities:
            if security.Symbol not in self.symbol_data:
                self.symbol_data[security.Symbol] = SymbolData(security.Symbol)

        for security in changes.RemovedSecurities:
            symbol_data = self.symbol_data.pop(security.Symbol, None)

        return None
