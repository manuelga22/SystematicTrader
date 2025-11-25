from enum import Enum

class TradingSignalEnum(Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    NONE = "NONE"

    def __str__(self):
        return self.name
    
class TradingSignal:
    def __init__(self, signal: TradingSignalEnum):
        self.signal = signal
        self.timestamp = None  # Placeholder for timestamp, can be set when signal is generated
        self.allocation_percentage = None  # Placeholder for allocation percentage

