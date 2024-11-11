# region imports
from AlgorithmImports import *
from symbol_data import SymbolData
from trailing_stop_risk import TrailingStopRiskManagementModel
from one_r_trailing_stop_loss_risk_management_model import (
    OneRTrailingStopRiskManagementModel,
)
from immediate_execution_model import ImmediateExecutionModel
from pytz import timezone
from day_of_week import DayOfWeek

# endregion


class OcODevisenStrategy(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2022, 1, 3)
        self.set_end_date(2024, 11, 10)

        self.set_cash(100000)
        self.default_order_properties.time_in_force = TimeInForce.DAY
        time_zone_id = "Europe/Berlin"
        self.berlin_tzinfo = timezone(time_zone_id)
        self.set_time_zone(time_zone_id)

        self.set_brokerage_model(
            brokerage=BrokerageName.INTERACTIVE_BROKERS_BROKERAGE,
            account_type=AccountType.MARGIN,
        )

        symbols: List[Symbol] = [
            self.add_forex(ticker=currency_pair, resolution=Resolution.MINUTE).symbol
            # for currency_pair in ["EURUSD", "GBPUSD", "EURGBP"]
            for currency_pair in ["EURUSD"]
        ]

        self.add_universe_selection(ManualUniverseSelectionModel(symbols))
        self.universe_settings.resolution = Resolution.MINUTE

        self.symbol_data: Mapping[Symbol, SymbolData] = {}

        self.pip = 0.0001  # TODO make this dependend on currency pair, this is not correct for Yen
        self.lot_size = 100000

        # self.add_risk_management(TrailingStopRiskManagementModel(0.006))
        self.add_risk_management(OneRTrailingStopRiskManagementModel(self.pip))
        self.set_execution(ImmediateExecutionModel())

        self.orders = {}

    def on_hourly_quote_bar(self, sender, quote_bar: QuoteBar):
        self.symbol_data[quote_bar.symbol].last_hour_quote_bar = quote_bar

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
            max_margin: float, risk_exposure: float, max_loss: float
        ) -> float:
            position_size = risk_exposure / max_loss
            desired_size = min(position_size, max_margin)
            return max(round(desired_size / self.lot_size), 1) * self.lot_size

        risk_exposure = self.portfolio.total_portfolio_value * 0.01

        # Calculate maximum potential loss for buy and sell
        maximum_loss_buy = get_maximum_loss(quote_bar.close, quote_bar.low)
        maximum_loss_sell = get_maximum_loss(quote_bar.high, quote_bar.close)

        # Calculate maximum allowable margin for this trade
        max_margin = calculate_max_margin()

        # Calculate buy and sell sizes, constrained by max margin
        buy_size = calculate_position_size(max_margin, risk_exposure, maximum_loss_buy)
        sell_size = calculate_position_size(
            max_margin, risk_exposure, maximum_loss_sell
        )

        return {"buy": buy_size, "sell": sell_size}

    def on_data(self, data: Slice):
        berlin_time = self.Time.astimezone(self.berlin_tzinfo)

        if berlin_time.weekday() == DayOfWeek.FRIDAY:
            return

        if berlin_time.time() == time(int(self.get_parameter("entry_time")), 0):
            for symbol, symbol_data in self.symbol_data.items():
                hour_bar = symbol_data.last_hour_quote_bar

                buy_stop_price = round(hour_bar.ask.high + self.pip * 2, 6)
                # entry tickets
                buy_stop_ticket = self.stop_market_order(
                    symbol=symbol,
                    quantity=self.get_quantity(hour_bar.ask)["buy"],
                    stop_price=buy_stop_price,
                )

                sell_stop_price = round(hour_bar.bid.low - self.pip * 2, 6)
                sell_stop_ticket = self.stop_market_order(
                    symbol, -self.get_quantity(hour_bar.bid)["sell"], sell_stop_price
                )
                self.register_oco_orders(buy_stop_ticket, sell_stop_ticket)

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
        self.log("order event: " + order_event.to_string())
        if order_event.status == OrderStatus.FILLED:
            if (order := self.orders.get(order_event.order_id)) is not None:  # exit
                self.transactions.cancel_order(order["oco_order_id"])

    def on_securities_changed(self, changes):
        for security in changes.AddedSecurities:
            if security.Symbol not in self.symbol_data:
                self.symbol_data[security.Symbol] = SymbolData(security.Symbol)
                consolidator = QuoteBarConsolidator(timedelta(hours=1))
                self.subscription_manager.add_consolidator(
                    security.Symbol, consolidator
                )
                consolidator.data_consolidated += self.on_hourly_quote_bar

        for security in changes.RemovedSecurities:
            symbol_data = self.symbol_data.pop(security.Symbol, None)
            # TODO remove consolidator

        return None
