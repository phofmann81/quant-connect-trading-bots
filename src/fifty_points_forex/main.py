# region imports
from AlgorithmImports import *
from symbol_data import SymbolData
from one_r_trailing_stop_loss_risk_management_model import (
    OneRTrailingStopRiskManagementModel,
)
from pytz import timezone
from day_of_week import DayOfWeek

# endregion


class OcODevisenStrategy(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2024, 9, 13)
        self.set_end_date(2024, 11, 13)

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
            # for currency_pair in ["GBPUSD",]
            for currency_pair in ["EURUSD", "GBPUSD", "EURGBP"]
        ]

        self.add_universe_selection(ManualUniverseSelectionModel(symbols))
        self.universe_settings.resolution = Resolution.MINUTE

        self.symbol_data: Mapping[Symbol, SymbolData] = {}

        self.pip = 0.0001  # TODO make this dependend on currency pair, this is not correct for Yen
        self.lot_size = 100000
        self.orders = {}
        self.risk_management_model = OneRTrailingStopRiskManagementModel(self)
        self.add_risk_management(self.risk_management_model)
        self.set_execution(ImmediateExecutionModel())

    def on_hourly_quote_bar(self, sender, quote_bar: QuoteBar):
        self.symbol_data[quote_bar.symbol].last_hour_quote_bar = quote_bar

    def get_quantity(self, quote_bar: QuoteBar) -> Mapping[str, float]:
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
            return min(position_size, max_margin, 20000)

        risk_exposure = self.portfolio.total_portfolio_value * 0.01

        # Calculate maximum allowable margin for this trade
        max_margin = calculate_max_margin()

        # Calculate buy and sell sizes, constrained by max margin
        position_size = calculate_position_size(
            max_margin,
            risk_exposure,
            self.get_trailing_stop_distance(quote_bar),
        )

        return position_size

    def on_data(self, data: Slice):

        if self.time.time() == time(int(self.get_parameter("entry_time")), 0):
            for symbol, symbol_data in self.symbol_data.items():
                hour_bar = symbol_data.last_hour_quote_bar

                buy_stop_price = round(hour_bar.ask.high + (self.pip * 3), 6)
                # entry tickets
                buy_stop_ticket = self.stop_market_order(
                    symbol=symbol,
                    quantity=self.get_quantity(hour_bar.ask),
                    stop_price=buy_stop_price,
                )
                sell_stop_price = round(hour_bar.bid.low - (self.pip * 3), 6)
                sell_stop_ticket = self.stop_market_order(
                    symbol, -self.get_quantity(hour_bar.bid), sell_stop_price
                )
                self.register_oco_orders(buy_stop_ticket, sell_stop_ticket)

                self.risk_management_model.set_trailing_stop_distance(
                    symbol,
                    self.get_trailing_stop_distance(symbol_data.last_hour_quote_bar),
                )

            if symbol in data.quote_bars and self.portfolio[symbol].invested:
                self.plot_price(symbol, data.quote_bars[symbol])

    def get_trailing_stop_distance(self, quote_bar: QuoteBar) -> float:
        return max(
            round(
                quote_bar.high - quote_bar.low,
                6,
            ),
            8 * self.pip,
        )

    def on_securities_changed(self, changes):
        for security in changes.AddedSecurities:
            if security.Symbol not in self.symbol_data:
                self.symbol_data[security.Symbol] = SymbolData(security.Symbol)
                consolidator = QuoteBarConsolidator(timedelta(hours=1))
                self.subscription_manager.add_consolidator(
                    security.Symbol, consolidator
                )
                consolidator.data_consolidated += self.on_hourly_quote_bar

                self.symbol_data[security.Symbol].atr = self.ATR(
                    security.Symbol, 60, Resolution.MINUTE
                )
                self.symbol_data[security.Symbol].rsi = self.RSI(
                    security.Symbol, 60, MovingAverageType.Wilders, Resolution.Minute
                )
                self.symbol_data[security.Symbol].adx = self.ADX(
                    security.Symbol, 60, Resolution.Minute
                )

                # charting
                chart_name = f"Trade Chart {security.Symbol.value}"
                chart = Chart(chart_name)
                chart.add_series(CandlestickSeries(name="Price", index=0))
                chart.add_series(Series("Stop Loss", SeriesType.Line, 0))
                chart.add_series(
                    Series(
                        name="Entry",
                        type=SeriesType.SCATTER,
                        unit="$",
                        color=Color.GREEN,
                        symbol=ScatterMarkerSymbol.TRIANGLE,
                    )
                )
                chart.add_series(
                    Series(
                        name="Exit",
                        type=SeriesType.SCATTER,
                        unit="$",
                        color=Color.RED,
                        symbol=ScatterMarkerSymbol.TRIANGLE_DOWN,
                    )
                )
                self.symbol_data[security.Symbol].chart = chart
                self.add_chart(chart)

        for security in changes.RemovedSecurities:
            symbol_data = self.symbol_data.pop(security.Symbol, None)
            # TODO remove all the things

        return None

    def register_oco_orders(self, one_ticket, other_ticket):
        self.orders[one_ticket.order_id] = {
            "oco_order_id": other_ticket.order_id,
            "type": "one",
        }
        self.orders[other_ticket.order_id] = {
            "oco_order_id": one_ticket.order_id,
            "type": "other",
        }

    def on_order_event(self, order_event: OrderEvent):
        self.log("order event: " + order_event.to_string())
        if order_event.status == OrderStatus.FILLED:
            if (order := self.orders.get(order_event.order_id)) is not None:  # exit
                self.transactions.cancel_order(order["oco_order_id"])

    def plot_price(self, symbol, quote_bar):
        self.plot(
            chart=self.symbol_data[symbol].chart.name,
            series="Price",
            open=quote_bar.open,
            high=quote_bar.high,
            low=quote_bar.low,
            close=quote_bar.close,
        )

    def plot_entry(self, symbol, entry_point):
        self.log("in plot entry")
        self.plot(
            chart=self.symbol_data[symbol].chart.name, series="Entry", value=entry_point
        )

    def plot_exit(self, symbol, exit_point):
        self.plot(
            chart=self.symbol_data[symbol].chart.name, series="Exit", value=exit_point
        )

    def plot_stop_loss(self, symbol, stop_loss):
        self.plot(
            chart=self.symbol_data[symbol].chart.name,
            series="Stop Loss",
            value=stop_loss,
        )
