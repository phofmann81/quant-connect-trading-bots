from src.aron20.main import Aron20

def test_conditions():
	aron = Aron20()
	symbol = "AAPL"
	aron.previous_minutes_close_over_ema9(symbol=symbol)