from dataclasses import dataclass
from enum import Enum


class FeeModel(Enum):
    POLYMARKET = 'polymarket'
    BPS = 'bps'
    FREE = 'free'


@dataclass
class FeeParams:
    """Parameters for taker fee calculation.

    rate is expressed in basis points (e.g. 100 = 1%) for every model,
    matching the feeRateBps field on Polymarket CLOB orders.
    """
    model: FeeModel = FeeModel.FREE
    rate_bps: float = 0.0            # fee rate in bps
    min_fee_dollars: float = 0.0         # floor applied to any nonzero fee, in dollars
    rebate_share: float = 0.0    # fraction of the fee rebated back (0..1)


def taker_fees(shares: float, price: float, fee_params: FeeParams) -> float:
    """Dollar fee paid to take liquidity on a fill of `shares` at `price`.

    - FREE: always 0.
    - BPS: rate applied to notional -> rate/10000 * shares * price.
    - POLYMARKET: rate/10000 * price * (1-price) * shares, per
      https://docs.polymarket.com/trading/fees (fee = C * feeRate * p * (1-p)).
      Symmetric in price, so buying YES at p costs the same as selling NO
      at 1-p; fees peak at p=0.5 and vanish near 0 and 1. The docs quote
      feeRate as a decimal (crypto 0.07, sports 0.03), so pass it in bps
      (700, 300). Rounded to 5 decimals like the docs, so dust fees are free.

    The result is floored at min_fee, then reduced by rebate_share.
    """
    if shares <= 0.0 or fee_params.rate_bps <= 0.0:
        return 0.0

    if fee_params.model == FeeModel.FREE:
        return 0.0

    # convert from bps to a decimal multiplier number (10 bps = 0.001)
    rate = fee_params.rate_bps / 10_000

    if fee_params.model == FeeModel.POLYMARKET:

        if price > 1 or price < 0:
            return 0.0
        
        # https://docs.polymarket.com/trading/fees: fee = C * feeRate * p * (1-p),
        # in USDC, rounded to 5 decimals (sub-0.00001 fees round to zero).
        fee = shares * rate * price * (1 - price)
        fee = round(fee, 5)

    elif fee_params.model == FeeModel.BPS:
        
        fee = rate * shares * price

    fee = max(fee, fee_params.min_fee)
    return fee * (1 - fee_params.rebate_share)




