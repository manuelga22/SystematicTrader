import pandas as pd
from trading_rules import early_loss_taker, early_profit_taker,\
                         mean_reversal, market_data, position_data,\
                         loss_profit_taker
from trading_rules.signals import TradingSignalEnum

print('hello')
if __name__ == "__main__":
    print("This is a trading rules tester module.")
    
    #############################
    ### TESTING POSITION DATA ###
    #############################

    cash_position = 5000

    positions = position_data.Positions(cash=cash_position)
    positions.add_position("AAPL", 50, 100)
    positions.show_positions()
    assert positions.get_available_cash() == 0

    positions.add_position("AAPL", 1, 100) 
    positions.show_positions()

    apple_position = positions.show_positions()[0]
    assert apple_position.get_entry_price() == 100
    assert apple_position.symbol == "AAPL"
    assert apple_position.quantity == 50

    assert positions.are_we_holding_positions() is True

    positions.remove_position("AAPL")
    assert positions.are_we_holding_positions() is False

    positions.show_positions()
    assert positions.show_positions() == []
    
    ###########################
    ### TESTING MARKET DATA ###
    ###########################

    apple_data = pd.DataFrame()
    apple_data['price'] = [50, 100, 95, 100, 105]
    market = market_data.MarketData(apple_data)

    assert market.get_latest_price() == 105
    assert market.get_mean(5) == 90.0  # Mean of all prices

    ##################################
    ### TESTING EARLY PROFIT TAKER ###
    ##################################

    early_profit = early_profit_taker.EarlyProfitTaker(profit_threshold=0.02)

    # Here we are holding an apple position of 50 shares at entry price of 100
    positions = position_data.Positions(cash=cash_position)
    positions.add_position(symbol="AAPL", quantity=50, entry_price=100)

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 102]
    market = market_data.MarketData(apple_data)
    
    assert early_profit.generate_signal(market, positions).value == TradingSignalEnum.SELL.value

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 90]
    market = market_data.MarketData(apple_data)
    
    assert early_profit.generate_signal(market, positions).value == TradingSignalEnum.NONE.value


    ##################################
    ### TESTING EARLY LOSS TAKER   ###
    ##################################

    early_loss = early_loss_taker.EarlyLossTaker(loss_threshold=0.02)

    # Here we are holding an apple position of 50 shares at entry price of 100
    positions = position_data.Positions(cash=cash_position)
    positions.add_position(symbol="AAPL", quantity=50, entry_price=100)

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 80]
    market = market_data.MarketData(apple_data)
    
    assert early_loss.generate_signal(market, positions).value == TradingSignalEnum.SELL.value

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 100]
    market = market_data.MarketData(apple_data)
    
    assert early_loss.generate_signal(market, positions).value == TradingSignalEnum.NONE.value


    ################################
    ### TESTING LOSS PROFIT TAKER ##
    ################################
    loss_profit = loss_profit_taker.LossProfitTaker(loss_threshold=0.02, won_threshold=0.02)

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 102]
    market = market_data.MarketData(apple_data)
    assert loss_profit.generate_signal(market, positions).value == TradingSignalEnum.SELL.value

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 98]
    market = market_data.MarketData(apple_data)
    assert loss_profit.generate_signal(market, positions).value == TradingSignalEnum.SELL.value

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 99]
    market = market_data.MarketData(apple_data)
    assert loss_profit.generate_signal(market, positions).value == TradingSignalEnum.NONE.value

    ################################
    ### TESTING MEAN REVERSAL    ###
    ################################

    mean_rev = mean_reversal.MeanReversal(short_window=2, long_window=5)
    
    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 100, 100, 100, 50] # Short mean (75) < Long mean (90) -> BUY signal
    market = market_data.MarketData(apple_data)
    
    assert mean_rev.generate_signal(market, position_data.Positions(cash=cash_position)).value == TradingSignalEnum.BUY.value

    apple_data = pd.DataFrame()
    apple_data['price'] = [100, 100, 100, 100, 100] # Short mean (100) < Long mean (100) -> No Signal
    market = market_data.MarketData(apple_data)   

    assert mean_rev.generate_signal(market, position_data.Positions(cash=cash_position)).value == TradingSignalEnum.NONE.value