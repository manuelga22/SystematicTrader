import pandas as pd

def take_profit():
    pass

def stop_loss():
    pass

def time_exit(max_bars: int) -> callable:
    def rule(pos, price, data, i):
        if i - pos["entry_idx"] >= max_bars:
            return True
        return False
    
    return rule

