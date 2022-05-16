# cosl
Algorithmic trading strategies on Binance.

At the time I didn't know what a trailing stop loss was and Binance didn't have it so I coded one and called it a Continuous OCO Stop Loss (COSL).

This code does various things:
* Looks for tokens that declined a certain percentage, then buys and tracks a COSL order.
* A slightly different strategy buys a token without a stop loss, waits for the price to get 3% in the money, set a 2% stop loss and take 1% profit, then any time it was over 2% in the money it would take profit and reset the stop loss. So it was a kind of scalping on an up trend and also moving the stop loss up each time it took profits.
* Substitute a candle counting strategy. Specify a certain number of green or red candles identified by string patterns such as "ggg" (three green candles in a row) or "rrr" or "ggrgg" (2 green candles, 1 red, then 2 green). Then put in a buy order if the pattern was found.

It saves the results to HTML files (simple table grid layout) to review the orders it made and whether profits taken and how much in USD.
