# HighVolumeUniverseSelectionModel.py
from AlgorithmImports import *
from Selection.FundamentalUniverseSelectionModel import (
    FundamentalUniverseSelectionModel,
)


class HighVolumeUniverseSelectionModel(FundamentalUniverseSelectionModel):
    def __init__(self, period=14, volume_threshold=1000000, top_n=20):
        """Initialize with the parameters for the volume filter"""
        super().__init__(filterFineData=False)
        self.period = period
        self.volume_threshold = volume_threshold
        self.top_n = top_n
        self.filtered_symbols = []

    def select_coarse(
        self, algorithm: QCAlgorithm, fundamental: list[Fundamental]
    ) -> list[Symbol]:
        """Custom universe selection based on volume filtering criteria"""
        # Filter coarse data by price and HasFundamentalData, then limit to top N by dollar volume
        filtered = [x for x in fundamental if x.HasFundamentalData and x.Price > 10]
        symbols = [x.Symbol for x in filtered[: self.top_n]]

        valid_symbols = []
        for symbol in symbols:
            history = algorithm.History(symbol, self.period, Resolution.Minute)

            if history.empty or not "volume" in history:
                continue

            # Extract volume data from historical bars
            volumes = history["volume"].tolist()

            avg_volume = sum(volumes) / len(volumes)
            min_volume = min(volumes)
            has_gap = any(v == 0 for v in volumes)

            # Only include symbols that pass the criteria
            if (
                avg_volume > self.volume_threshold
                and min_volume > self.volume_threshold
                and not has_gap
            ):
                valid_symbols.append(symbol)

        # Store filtered symbols for later use
        self.filtered_symbols = valid_symbols
        return valid_symbols
