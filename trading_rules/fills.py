
from dataclasses import dataclass

import pandas as pd
from enum import Enum


class FillAtEnum(Enum):
    CLOSE = 'close'
    OPEN = 'open'
    HIGH = 'high'
    LOW = 'low'


@dataclass
class SlippageParams:
    bps: float = 2.0 # persistent spread.
    atr_multiplier: float = 0.1 # what fraction of atr becomes slippage


class OrderFiller:
    """
    Converts an order on a given bar into the price it actually executes at:
    the bar's open or close (per fill_at) plus slippage, so buys fill higher
    and sells fill lower than the raw bar price.
    """
    def __init__(self, data: pd.DataFrame, slippage_params: SlippageParams,
                 fill_at: FillAtEnum = FillAtEnum.CLOSE):
        self.data = data
        self.slippage_params = slippage_params
        self.fill_at = fill_at

    def fill_price(self, i: int, action: int) -> float:
        """
        Price an order executes at on bar i.
        action: (int) +1 for buy, -1 for sell
        """
        bar = self.data.iloc[i]
        base_price = bar[self.fill_at.value]
        return base_price + get_slippage_cost(bar, action, self.slippage_params,
                                              base_price=base_price)

    def next_bar_fill(self, i: int, action: int) -> float | None:
        """
        Shifts fill of the order to the next bar: the signal is observed on
        bar i but the order executes on bar i + 1, avoiding lookahead bias.
        Returns None on the last bar, where no fill is possible.
        """
        if i + 1 >= len(self.data):
            return None
        return self.fill_price(i + 1, action)


def get_slippage_cost(price_bar: pd.Series, action: int, slippage_params: SlippageParams,
                      base_price: float | None = None) -> float:
    """
    price_bar: (pd.Series) containing price information and atr.
    action: (int) +1 for buy, -1 for sell
    base_price: (float) price the fixed-bps cost is taken from; defaults to close.
    Returns the signed per-share slippage cost: positive for buys, negative
    for sells, so adding it to the price always makes the fill worse.
    """
    if base_price is None:
        base_price = price_bar.close
    fixed_cost = base_price * (slippage_params.bps / 10_000.0)
    vol_cost = (price_bar.atr or 0.0) * slippage_params.atr_multiplier
    total_cost = fixed_cost + vol_cost
    return action * total_cost
