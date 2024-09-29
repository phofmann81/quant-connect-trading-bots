from AlgorithmImports import *


class FibonacciRetracementIndicator(PythonIndicator):
    def __init__(self, name):
        super().__init__()
        self.name = name

        self.current_high = None
        self.current_low = None
        self.current_day = None
        self._100 = FibonacciLevelIndicator(100)
        self._786 = FibonacciLevelIndicator(78.6)
        self._618 = FibonacciLevelIndicator(61.8)
        self._50 = FibonacciLevelIndicator(50)
        self._382 = FibonacciLevelIndicator(38.2)
        self._236 = FibonacciLevelIndicator(23.6)
        self._0 = FibonacciLevelIndicator(0)
        self.level_indicators = [
            self._100,
            self._786,
            self._618,
            self._50,
            self._382,
            self._236,
            self._0,
        ]

        self.value = None

    def __getitem__(self, index):
        # Forward index request to window object
        try:
            item = self.window[index]
            return item
        except Exception:
            return 0, 0

    def __setitem__(self, index, value):
        # Forward set request to window object
        self.window[index] = value

    def update(self, input):
        # Check if it's a new day
        if self.current_day != input.Time.date():
            self.current_day = input.Time.date()
            self.current_high = input.High
            self.current_low = input.Low
        else:
            # Update the high and low for the current day
            self.current_high = max(self.current_high, input.High)
            self.current_low = min(self.current_low, input.Low)

        if self.current_high == self.current_low:
            return False  # no fib if no diff

        diff = self.current_high - self.current_low
        low = self.current_low
        # Fibonacci levels (23.6%, 38.2%, 50%, 61.8%, 100%)

        for level in self.level_indicators:
            level.update(low, diff)

        # set 50er fib as value here as the interface demands. We'll only be using the level indicators anyway.
        self.value = self._50.current.value
        self.current.set_value(self.value)

        return bool(self.current_high and self.current_low)


class FibonacciLevelIndicator(PythonIndicator):
    def __init__(self, level: float):
        super().__init__()
        self.level = level
        self.name = str(f"level-{level}")
        self.value = None

    def __getitem__(self, index):
        # Forward index request to window object
        try:
            item = self.window[index]
            return item
        except Exception:
            return 0, 0

    def __setitem__(self, index, value):
        # Forward set request to window object
        self.window[index] = value

    def update(self, low, diff):
        self.value = low + ((self.level / 100) * diff)
        self.current.set_value(self.value)

        return bool(low and diff)
