from enum import Enum

class TimeframesEnum(Enum):
    ONE_MINUTE = '1Min'
    FIVE_MINUTES = '5Min'
    FIFTEEN_MINUTES = '15Min'
    THIRTY_MINUTES = '30Min'
    ONE_HOUR = '1H'
    FOUR_HOURS = '4H'
    DAILY = '1D'
    WEEKLY = '1W'
    MONTHLY = '1M'