import pandas as pd

def take_profit():
    pass

def stop_loss():
    pass

def time_exit(max_bars: int) -> callable:
    def rule(pos, price, data, i):
        if  data.iloc[i]['close'] - data.iloc[pos["entry_idx"]]['close'] >= max_bars:
            return True
        return False
    
    return rule

