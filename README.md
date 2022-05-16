# cosl
Algorithmic trading strategies on Binance.

At the time I didn't know what a trailing stop loss was and Binance didn't have it so I coded one and called it a Continuous OCO Stop Loss (COSL).

This code does various things:
* Looks for tokens that declined a certain percentage, then buys and tracks a COSL order.
* A slightly different strategy was to buy a token without a stop loss, wait for it the price to get 3% in the money, set a 2% stop loss and take 1% profit, then any time it was over 2% in the money it would take profit and reset the stop loss.
* Substitute a candle counting strategy (a certain number of green or red candles identified by string patterns such as "ggg" (three green candles in a row) or "rrr" or "ggrgg" (2 green candles, 1 red, then 2 green).
