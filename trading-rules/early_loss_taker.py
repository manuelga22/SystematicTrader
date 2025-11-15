from trading_strategy import TradingStrategy

class EarlyLossTaker(TradingStrategy):
    
    def __init__(self):
        pass

    def generate_signal(self, market_data, positions_data):
        return super().generate_signal(market_data, positions_data)
       

    def should_exit_trade(self, entry_price: float, current_price: float) -> bool:
        """
        Determine whether to exit the trade based on the current price and entry price.

        :param entry_price: The price at which the trade was entered.
        :param current_price: The current market price of the asset.
        :return: True if the trade should be exited, False otherwise.
        """
        loss = (entry_price - current_price) / entry_price
        return loss >= self.loss_threshold