# %% [markdown]
# ![QuantConnect Logo](https://cdn.quantconnect.com/web/i/icon.png)
# <hr>

# %%
from brain_sentiment_alpha_model import BrainSentimentAlphaModel

# %%
from unittest.mock import MagicMock


def alpha_model():
    return BrainSentimentAlphaModel()


def symbol():
    return Symbol.create("AAPL", SecurityType.EQUITY, Market.USA)


def trade_bar(open, high, low, close):
    return TradeBar(time(0, 0), symbol(), open, high, low, close, 0)


# %%
def test_check_entry_condition_ema_close_long(alpha_model):
    bar = FakeTradeBar(close=105, open=0, high=0, low=0)
    ema_20 = 100
    ema_50 = 95
    ema_200 = 90
    is_long = True

    result = alpha_model.check_entry_condition_ema_close(
        bar, ema_20, ema_50, ema_200, is_long
    )
    assert result == True


test_check_entry_condition_ema_close_long(alpha_model())


# %%
def test_check_entry_condition_ema_close_short(alpha_model):
    bar = FakeTradeBar(close=85, open=0, high=0, low=0)
    ema_20 = 90
    ema_50 = 95
    ema_200 = 100
    is_long = False

    result = alpha_model.check_entry_condition_ema_close(
        bar, ema_20, ema_50, ema_200, is_long
    )
    assert result == True


test_check_entry_condition_ema_close_short(alpha_model())


# %%
def test_check_entry_condition_ema_close_long_fail(alpha_model):
    bar = FakeTradeBar(close=85, open=0, high=0, low=0)
    ema_20 = 100
    ema_50 = 95
    ema_200 = 90
    is_long = True

    result = alpha_model.check_entry_condition_ema_close(
        bar, ema_20, ema_50, ema_200, is_long
    )
    assert result == False


test_check_entry_condition_ema_close_long_fail(alpha_model())


# %%
def test_check_entry_condition_ema_close_short_fail(alpha_model):
    bar = FakeTradeBar(close=105, open=0, high=0, low=0)
    ema_20 = 90
    ema_50 = 95
    ema_200 = 100
    is_long = False

    result = alpha_model.check_entry_condition_ema_close(
        bar, ema_20, ema_50, ema_200, is_long
    )
    assert result == False


test_check_entry_condition_ema_close_short_fail(alpha_model())


# %%
def test_check_entry_condition_open_ema_20_long(alpha_model):
    bar = FakeTradeBar(close=0, open=105, high=0, low=0)
    ema_20 = 100
    is_long = True

    result = alpha_model.check_entry_condition_open_ema_20(bar, ema_20, is_long)
    assert result == True


test_check_entry_condition_open_ema_20_long(alpha_model())


# %%
def test_check_entry_condition_open_ema_20_short(alpha_model):
    bar = FakeTradeBar(close=0, open=85, high=0, low=0)
    ema_20 = 90
    is_long = False

    result = alpha_model.check_entry_condition_open_ema_20(bar, ema_20, is_long)
    assert result == True


test_check_entry_condition_open_ema_20_short(alpha_model())


# %%
def test_check_entry_condition_open_ema_20_long_fail(alpha_model):
    bar = FakeTradeBar(close=0, open=85, high=0, low=0)
    ema_20 = 100
    is_long = True

    result = alpha_model.check_entry_condition_open_ema_20(bar, ema_20, is_long)
    assert result == False


test_check_entry_condition_open_ema_20_long_fail(alpha_model())


# %%
def test_check_entry_condition_open_ema_20_short_fail(alpha_model):
    bar = FakeTradeBar(close=0, open=105, high=0, low=0)
    ema_20 = 90
    is_long = False

    result = alpha_model.check_entry_condition_open_ema_20(bar, ema_20, is_long)
    assert result == False


test_check_entry_condition_open_ema_20_short_fail(alpha_model())


# %%
def test_check_previous_bar_long(alpha_model):
    bar_window_1 = RollingWindow[TradeBar](2)
    bar_window_2 = RollingWindow[TradeBar](2)
    is_long = True

    # window[0](latest candle) soll Entweder long aussenkerze, order short innenkerze sein
    # aussenkerze = high or low höher als vorherige
    # innenkerze: high and low both fully within range of previous candle
    for f in [
        trade_bar(open=0, high=8, low=5, close=0),
        trade_bar(open=8, high=10, low=5, close=10),
    ]:
        bar_window_1.add(f)  # long aussenkerze

    for f in [
        trade_bar(open=8, high=12, low=10, close=10),
        trade_bar(open=0, high=6, low=8, close=0),  # short, but not within previous
    ]:
        bar_window_2.add(f)  # short innenkerze

    assert alpha_model.check_previous_bar(bar_window_1, is_long) == True
    assert alpha_model.check_previous_bar(bar_window_2, is_long) == False


test_check_previous_bar_long(alpha_model())


# %%
def test_check_previous_bar_short(alpha_model):
    bar_window_1 = RollingWindow[TradeBar](2)
    bar_window_2 = RollingWindow[TradeBar](2)
    is_long = False
    # window[0](latest candle) soll Entweder short aussenkerze, order long innenkerze sein
    # aussenkerze = high or low höher als vorherige
    # innenkerze: high and low both fully within range of previous candle

    for f in [
        trade_bar(open=0, high=8, low=6, close=0),
        trade_bar(open=8, high=5, low=10, close=10),
    ]:
        bar_window_1.add(f)  # short aussenkerze

    for f in [
        trade_bar(open=0, high=10, low=7, close=0),
        trade_bar(open=8, high=8, low=6, close=10),
    ]:
        bar_window_2.add(f)  # long innenkerze

    for result in [
        alpha_model.check_previous_bar(bar_window_1, is_long),
        alpha_model.check_previous_bar(bar_window_2, is_long),
    ]:
        assert result == True

    # should also pass:

    for f in [
        trade_bar(open=0, high=8, low=6, close=0),
        trade_bar(open=8, high=9, low=10, close=10),
    ]:
        bar_window_1.add(f)  # short aussenkerze aber wo anders

    for f in [
        trade_bar(open=0, high=10, low=7, close=0),
        trade_bar(open=8, high=14, low=13, close=10),
    ]:
        bar_window_2.add(f)  # long innenkerze aber wo anders

    assert alpha_model.check_previous_bar(bar_window_1, is_long) == True
    assert alpha_model.check_previous_bar(bar_window_2, is_long) == False


test_check_previous_bar_long(alpha_model())


# %%
def test_close_cross_ema_200(alpha_model):
    bar_window_1 = RollingWindow[TradeBar](2)
    for t in [
        trade_bar(close=95, open=0, high=0, low=0),
        trade_bar(close=90, open=0, high=0, low=0),
    ]:
        bar_window_1.add(t)

    ema_200 = MagicMock()
    ema_200.is_ready = True
    ema_200.current.value = 100
    ema_200.previous.value = 90

    result = alpha_model.close_cross_ema_200(bar_window_1, ema_200)
    assert result == True


def test_close_cross_ema_200_fail(alpha_model):
    bar_window_1 = RollingWindow[TradeBar](2)
    for t in [
        trade_bar(close=95, open=0, high=0, low=0),
        trade_bar(close=90, open=0, high=0, low=0),
    ]:
        bar_window_1.add(t)

    ema_200 = MagicMock()
    ema_200.is_ready = True
    ema_200.current.value = 90
    ema_200.previous.value = 110

    result = alpha_model.close_cross_ema_200(bar_window_1, ema_200)
    assert result == False


test_close_cross_ema_200(alpha_model())
test_close_cross_ema_200_fail(alpha_model())


# %%
