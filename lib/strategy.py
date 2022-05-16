"""This is the strategy module

This module contains functions for specific trading strategies.
"""

#__example__ = ['a','b','c']

import sys
import math
import time
import random
import decimal
import traceback # exception handling
import statistics
from datetime import date, datetime, timezone # for unix timestamp conversion

import json
import pickle
import numpy as np
import pandas as pd
from binance.enums import *

import lib.util as util

# Run through my entire HOLDING portfolio and create stop loss orders based on
# the current price of each asset.
#   Create a normal limit order in Binance
#   Get a list of all my assets in Binance, amounts, and current asset
#   Loop through each asset
#   Get the asset's current price and amount
#   Execute a test limit order for each asset and print()
#   Test with 1 asset (by setting a counter and stopping at 2)
#   Test with all assets
# Next:
#   Create a new function that monitors these orders. If any of them execute,
#   set a stop BUY order for 0.5% above the executed price or current price.
def stop_loss_all(cxn):
    # Get a list of my assets in this connection
    if (util.get_cxn_type(cxn) == 'binance'):
        info = cxn.get_symbol_info(symbol)
    cxn.get_account()

def my_positions_in_usd(cxn):
    if (util.get_cxn_type(cxn) == 'binance'):
        account_info = cxn.get_account() # all my acct details with balances
    balances = pd.read_json(json.dumps(account_info['balances']))
    balances = balances.loc[(balances.free > 0) | (balances.locked > 0)] # where > 0
    balances.rename(columns = {'asset':'baseAsset'}, inplace = True)
    prices = cxn.get_all_tickers()
    exchange_info = cxn.get_exchange_info()
    symbols = pd.read_json(json.dumps(exchange_info['symbols']))
    symbols = symbols[['symbol', 'baseAsset','quoteAsset']]
    # Filter the ones I want ("USDT")
    # symbol, baseAsset, quoteAsset
    symbols_usdt = symbols.loc[(symbols.quoteAsset == 'USDT')]
    symbols_busd = symbols.loc[(symbols.quoteAsset == 'BUSD')]
    symbols_usdc = symbols.loc[(symbols.quoteAsset == 'USDC')]
    symbols_dai = symbols.loc[(symbols.quoteAsset == 'DAI')]
    # Get the base currency from the trading pair
    # symbols_usdt['baseAsset']
    prices_df = pd.DataFrame(prices) # price, symbol
    prices_df['price'] = prices_df['price'].astype(float)
    # Merge like this:
    # price            symbol        baseAsset  quoteAsset
    # 1.283100e+00     BAKEBUSD      BAKE       BUSD
    # and then trim table to just price and baseAsset.
    symbols_merged_usdt = pd.merge(prices_df, symbols_usdt, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_busd = pd.merge(prices_df, symbols_busd, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_usdc = pd.merge(prices_df, symbols_usdc, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_dai = pd.merge(prices_df, symbols_dai, on='symbol', how='left')[['baseAsset','price']]
    #symbols_merged = pd.merge(prices_df, symbols_usdt, on='symbol', how='left')

    # Rename each price column by it's quote asset
    symbols_merged_usdt.rename(columns = {'price':'usdt'}, inplace = True)
    symbols_merged_busd.rename(columns = {'price':'busd'}, inplace = True)
    symbols_merged_usdc.rename(columns = {'price':'usdc'}, inplace = True)
    symbols_merged_dai.rename(columns = {'price':'dai'}, inplace = True)

    # Match the base currency to balances table
    # Show price next to quantity like this:
    # baseAsset price, symbol, quoteAsset
    balances_merged = balances
    balances_merged = pd.merge(balances_merged, symbols_merged_usdt, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_busd, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_usdc, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_dai, on='baseAsset', how='left')
    # average all the USD-like prices
    balances_merged["price_usd"] = balances_merged[['usdt','busd','usdc','dai']].astype(float).mean(axis=1)
    # Multiply to get total value
    #balances_merged['price'] = balances_merged['price'].astype(float)
    balances_merged['total'] = (balances_merged["free"] + balances_merged["locked"]) * balances_merged["price_usd"]
    bal = balances_merged.sort_values(by=['total'],inplace=False,ascending=False)
    # total balance for assets with USDT pair
    bal = bal[['baseAsset','free','locked','price_usd','total']].fillna(0)
    print("Binance USD Balance: " + '${:,.0f}'.format(sum(bal["total"])))
    return bal
    # problem: USDT doesn't match with USDT so it doesn't get counted
    # and HEGIC has BUSD pair but not USDT pair. So pull multiple columns:
    # USDT, BUSD, USD, etc. and then coalesce across the columns and then
    # sum the coalesced column.



#Trade_OCO:
# run this script every 15 minutes (or every hour) throughout the day. do a shorter test.
# we don't want to buy ALGOUSD, ALGOUSDT, and ALGOUSDC. So just pick the first one where the US-like balance
# is the highest. Use a group by to shrink the dataframe a bit. But actually, the way we have it sorted
# now below this isn't likely to happen too often. It will though so we should code it.
# .group_by('symbol' and where red_count is highest and where total_free_usd is highest).
# sort candles_free by red
# candles_group = candles_free.groupby(['baseAsset'])...?
def simple_trade_oco(cxn, oco_list, quote_amount_usd, profit=0.06, loss=0.03, actually_trade=False, market_buy=True):
    orders = []
    for index, row in oco_list.iterrows():
        order = None
        quote_amount = None
        quote_amount = 1
        if (row['quoteAsset'] in ('USD','USDT','USDC','BUSD')):
          quote_amount = 1
        else:
          quote_amount = util.get_current_price(cxn,row['quoteAsset']+'USD')

        quote_amount = quote_amount_usd / quote_amount
        if (actually_trade == False):
            print("strat.oco( \
                cxn, \
                quote_amount="+str(quote_amount)+", \
                profit = "+str(profit)+", \
                loss = "+str(loss)+", \
                symbol='"+row['symbol']+"')"
            )
        else:
            orders.append(oco(cxn, quote_amount=quote_amount, profit=profit, loss=loss, symbol=row['symbol'], market_buy=market_buy))
    return orders


def simple_trade_oco_buy(cxn, oco_list, quote_amount_usd, profit=0.04, loss=0.04, actually_trade=False, market_buy=True, symbol_prices = None):
    """
    Replaces simple_trade_oco as we move toward making buy stop loss
    orders instead of market buying assets outright.
    """
    print("")
    print("-=-=-=-==--=-=-=-=-=-=-=-=-=-=-=")
    print("inside simple_trade_oco_buy()...")
    print("-=-=-=-==--=-=-=-=-=-=-=-=-=-=-=")
    orders = []
    # this could generate an error if it returns empty
    symbol_prices_indexed = symbol_prices.set_index('symbol')
    for index, row in oco_list.iterrows():
        #print("symbol_prices value: ")
        #print(symbol_prices.loc[symbol_prices['symbol']==symbol])
        #print(symbol_prices_indexed.loc[['symbol']==symbol])
        order = None
        quote_amount = None
        quote_amount = 1
        if (row['quoteAsset'] in ('USD','USDT','USDC','BUSD')):
            quote_amount = 1
        else:
            if (symbol_prices == None):
                quote_amount = util.get_current_price(cxn,row['quoteAsset']+'USD')
            else:
                quote_amount = float(symbol_prices_indexed.loc[row['quoteAsset']+'USD','price'])

        quote_amount_calc = quote_amount_usd / quote_amount

        print("from symbol_prices_indexed: " + (symbol_prices_indexed.loc[row['baseAsset']+'USD','price']))
        #print("from symbol_priced_indexed: " + symbol_prices_indexed.loc['VTHOUSD','price'])
        print("quote_amount_usd: "+str(quote_amount_usd))
        print("quote_amount: "+row['baseAsset']+" "+str(quote_amount))
        print("quote_amount_calc: "+row['baseAsset']+" "+str(quote_amount_calc))

        if (actually_trade == False):
            print("strat.oco( \
                cxn, \
                quote_amount="+str(quote_amount)+", \
                quote_amount_calc="+str(quote_amount_calc)+", \
                profit = "+str(profit)+", \
                loss = "+str(loss)+", \
                symbol='"+row['symbol']+"')"
            )
        else:
            #orders.append(oco(cxn, quote_amount=quote_amount, profit=profit, loss=loss, symbol=row['symbol'], market_buy=market_buy))
            #cxn, symbol, base_asset, current_price, profit_pct, loss_pct, quote_cost
            log_cancel, market_price, buy_order = util.create_or_adjust_buy_side_stop_loss_order(
                cxn,
                row['symbol'],
                row['baseAsset'],
                float(symbol_prices_indexed.loc[row['baseAsset']+'USD','price']), # current_price
                profit,
                loss,
                quote_amount_calc # quote_cost
            )
            orders.append(buy_order)
    return orders

def trade_oco(cxn, oco_list, trade_amount, actually_trade=False):
    # this can be used to find out if we own any of the base asset already
    # and ignore the oco recommendation for that asset
    balances_base = util.get_balances(cxn)
    # same as above but rename "baseAsset" to "quoteAsset" as we are first
    # interested in whether or not we have the spending money.
    balances_quote = balances_base.rename(columns={'baseAsset':'quoteAsset'}, inplace=False)
    # How much USD is free to spend?
    total_free_usd = sum(balances_quote['total_free_usd'].fillna(0))
    possible_trades = int(round(total_free_usd/trade_amount,0))
    # filter the list so that it only shows the highest candle count for the base asset - pick whichever
    # Get the oco sorted list with total free usd alongside. To determine how much spending money we have.
    candles_free = pd.merge(oco_list, balances_quote[['quoteAsset','total_free_usd']], on='quoteAsset', how='inner')
    candles_free.sort_values(by=['red_count','total_free_usd'], ascending = False, inplace=True)
    # filter the list by the ones with the highest ratio of red candles
    # note: remove -0.13 - that's just there because my threshold is off. rare to see more than 8 red candles in
    # a row so threshold should be something 0.69 rather than 0.82
    candles_trade_filtered = candles_free.loc[(
        candles_free['red_count']/candles_free['candle_count']
        > candles_free['threshold']-0.13) & (candles_free['total_free_usd']>=trade_amount)]
    candles_trade = candles_free.loc[(candles_free['total_free_usd']>=trade_amount)]
    candles_trade = candles_free
    orders = []
    if (actually_trade == False):
        return candles_trade
    for index, row in candles_trade.iterrows():
        free_balance = util.get_free_balance(bus,row['quoteAsset'])
        print("trade "+ row['symbol']+ " using " + str(free_balance)) #str(row['total_free_usd']))
        print("free balance of " + row['quoteAsset'] + ": " + str(free_balance))
        time.sleep(3)
        if (free_balance > trade_amount):
            order = oco(cxn, row['symbol'], quote_cost, profit = profit, loss = loss)
            print(order)
            orders.append(order)
        else:
            print("balance not high enough")
        time.sleep(3)
    return orders


    # Simpler version for now. More complicated version below in the comments.
    #for asset in candles_free:
    #    print("trade "+ symbol + " using " + total_free_usd
    #    ... what next?
    #
    # Evaluate 1 by 1 from the top
    # for i in candles_free:
    #   price_dict = {i[['baseAsset']]:i[['total_free_usd']]}
    #   if free_usd = 500 then trade the symbol with oco() function
    #   if the trade was successful, then price_dict[i[['baseAsset']]] = i[['total_free_usd']] - order.fillAmount
    # ... if it was not successful, was it for lack of funds?
    # ... if yes, then move funds from another US currency to this one
    # re-pull balances
    # if free_usd



# Pull all Binance Market coins
# Put them in random order
# Iterate through the list, pulling 1 minute candles or recent trades
# If the last 1,2, or 3 candles were increasing then proceed
# (or if over 85% of trades occurring in the last minute were buys then proceed)
# ... buy create an OCO order with this asset.
def choose_oco(cxn, candle_span = 15, candle_count = 10, pattern = None, method = None, test = False, info = None):
    # ignore candle_count if a pattern was specified because the length of pattern
    # is the number of candles we're interested in.
    if (pattern != None):
        candle_count = len(pattern)
    # get assets and randomize
    if (info == None):
        info = cxn.get_exchange_info()
    df_info = pd.DataFrame(info['symbols'])
    # some, like XRP are not currently tradeable
    df_info = df_info[['symbol','baseAsset','quoteAsset']].loc[(df_info['status']=='TRADING')]

    # tickers = cxn.get_ticker()
    tickers = cxn.get_ticker()
    #df_tickers = pd.DataFrame(tickers)
    ticker_symbols = []
    for i in tickers:
        ticker_symbols.append(i['symbol'])
    random.shuffle(ticker_symbols)

    # merge tickers with info to separate base and quote asset


    # don't buy what I already have again
    # balance = cxn.get_asset_balance(asset=quoteAsset)

    if (test == True):
        ticker_symbols = ticker_symbols[0:8] # just 2 to test out the code
        # otherwise it takes too long to fetch all 90 symbols.
    symbols_with_candle_counts = []
    for symbol in ticker_symbols:
        # get the baseAsset and current price
        # and if this:
        # balance = cxn.get_asset_balance(asset=quoteAsset)
        # multiplied by the price is hundreds or thousands
        # then don't buy it. I already have it.
        # if (symbol.endswith('USDT')
        #    & symbol.startswith('BUSD') == False
        #    & symbol.startswith('USDC') == False
        #    & symbol.startswith('USDT') == False
        # ):
        if (symbol.startswith('BUSD') == False &
            symbol.startswith('USDC') == False &
            symbol.startswith('USDT') == False &
            symbol.startswith('DAI') == False
        ):
            # pull 15 minute candles going back 3 hours
            # for every symbol. sort this list by # of red candles
            a = {'symbol':symbol}
            # a = {'symbol':'BTCBUSD'}
            last_x_candles = util.get_last_x_candles(cxn, symbol, candle_span = candle_span, candle_count = candle_count)
            # b = util.get_last_x_candles(cxn, 'BTCBUSD', candle_span = 15, candle_count = 6)
            # These are different strategies I'm building out:
            b = None
            if (pattern == None and method == None):
                # some % of the last x candles need to be red.
                b = util.find_red_candles(last_x_candles, 0.7) # .70 = 7 of the last 10 are red
            elif (pattern != None or method == 'pattern'):
                # candles following a pattern chronologically. E.g.,
                # rrgg means 2 reds happened then 2 greens happened
                # it will only look at the last 4 candles.
                b = util.has_pattern(last_x_candles, pattern)
            elif (method == 'pct_change'):
                b = util.pct_change(last_x_candles)

            a.update(b)
            symbols_with_candle_counts.append(a)

            #return symbol
#    return pd.DataFrame(symbols_with_candle_counts).sort_values(by=['red_count'], ascending = False)

    symbols_candles = pd.DataFrame(symbols_with_candle_counts)
    symbols_merged = pd.merge(df_info, symbols_candles, on='symbol', how='inner')
    if (pattern == None and method == None):
        symbols_merged.sort_values(by=['red_count'], ascending = False, inplace=True)
    elif (pattern != None or method == 'pattern'):
        symbols_merged.sort_values(by=['result'], ascending = False, inplace=True)
    elif (method == 'pct_change'):
        symbols_merged.sort_values(by=['pct_change'], ascending = True, inplace=True)

    # if (balances != None):
    #     candles_free = pd.merge(symbols_merged, bus_bal[['baseAsset','total_free_usd']], on='baseAsset', how='inner')
    #     candles_free.sort_values(by=['red_count'], ascending = False)
    return symbols_merged

    # picking this up again:
    # I'm not sure any of these strategies are really going to work.
    # the data seems very noisy.
    # for now, just choose 3 at random and put the oco orders in. Then wait 24 hours.

    # pull the tickers data (below)
    # and cut out the lower volume symbols
    # then choose at random from the rest (or choose ones that had a negative 24 hr change)
    # then get historical klines for the last few mintues, or the last few sets of 5 minutes
    # if the klines are all red but getting smaller (open-close is/was positive and decreasing or becoming negative)
    #   AND if count is increasing at the same time.
    # then consider buying it.



    # pd.read_json(json.dumps(tickers))
    # df.sort_values(by='count')

    # iterate through them one by one until we find
    # the criteria we're looking for, then stop at 3 and return them.
#    for symbol in symbols:
        # pull this symbol's candles or trades
#        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "3 min ago UTC")
        # if number of trades is increasing
        # and if close is higher than low for the last 3 klines
        #   or, if open - close is decreasing and approaching zero


    #return symbols

    # 1499040000000,      // Open time
    # "0.01634790",       // Open
    # "0.80000000",       // High
    # "0.01575800",       // Low
    # "0.01577100",       // Close
    # "148976.11427815",  // Volume
    # 1499644799999,      // Close time
    # "2434.19055334",    // Quote asset volume
    # 308,                // Number of trades
    # "1756.87402397",    // Taker buy base asset volume
    # "28.46694368",      // Taker buy quote asset volume
    # "17928899.62484339" // Ignore.

# to add:
# check that I have enough of the quote currency first:
#    pull
def oco(
    cxn, # exchange connection object
    symbol, # symbol to trade
    quote_amount, # amount to purchase/sell in quote currency
    market_buy = True, # true if asset needs to be purchased first
    quantity = 0, # quantity (in base asset)
    side = 'sell', # buy or sell
    profit = .025, # 2.5% profit for limit maker
    loss = .01, # 1.0% loss for stop limit
    stop_limit_price_param = 0, # set my own stop limit price
    verbose = False, # true to print out lots of messages
    test = False # true to do everything except actually send the order
):
    # If I try to make 1% then I lose 20% of my earnings to Binance.
    # With Binance and taxes and network transfer fees I probably keep
    # $30 for every $100 I make. But before taxes and network fees it's
    # about $56. The major problem with this is that I also
    # lose $20 when my stop loss order executes. So if I have 1 loss and 1
    # win then ultimately I've only earned $36 and if I lose twice it's $10,
    # of which $7 minus network transfer and withdrawal fees is actually mine.
    #
    # So it helps to earn more. Rather than 1%
    # gains, shoot for higher gains and accept bigger losses. E.g., rather
    # than a 1% take profit and a 0.1% stop loss, set a 10% profit and a 1%
    # stop loss.
    #
    # This is a good start. It just highlights the importance of choosing well
    # from the start. So, checking to see if this is on the rise, if the orders
    # are mostly buys right now, etc.
    #
    # Next: figure out how to use the info() function data to stop getting
    # errors. For example, to set the # of places after the decimal on the
    # price and to address the LOT_SIZE error I get with HARDBUSD.
    #
    # Is this connection type supported in this function?
    # Currently Binance.com and Binance.us only - 3/11/2021
    cxn_type = None
    if (str(type(cxn)) != "<class 'binance.client.Client'>"):
        print("Connection type not supported: " + str(type(cxn)))
        return None
    else: cxn_type = 'binance'
    # sell only supported right now
    if (side != 'sell'):
        print('Sell only supported right now.')
        return None
    log = {}
    log['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log['symbol'] = symbol
    log['quantity'] = quantity
    log['make_market_buy'] = market_buy
    log['profit_pct'] = profit
    log['loss_pct'] = loss
    # fix: the price accuracy
    #quantity plus buy and sell fee together
    #buy_quantity_pre = .05
    #log["buy_quantity_pre"]=buy_quantity_pre
    # get and use some basic info about this symbol
    if (cxn_type == 'binance'):
        info = cxn.get_symbol_info(symbol)
    tick_size = util.get_precision_as_int(info['filters'][0]['tickSize'])
    precision = util.get_precision_as_int(info['filters'][2]['stepSize'])
    # if I already own it, the fee will be .001
    # find out what the current price is
    current_price = None
    trades = cxn.get_aggregate_trades(symbol=symbol)
    current_price = pd.read_json(json.dumps(trades)).sort_values(by="T",ascending=False).iloc[0]["p"]
    # when placing a market order first, some is taken for
    # fee, so in order to limit sell for the specified amount we need to pad
    # with the fee first.
    # assume 0.1% each for the buy and the sell
    if (quote_amount > 0):
        # take the quote_amount and use the current price to turn it
        # into a quantity
        quantity = quote_amount / current_price
        # In the future, if the quote is not USD like BTCBNB
        # but I want to be able to supply a USD amount
        # then maybe I can first get the BNBUSDT price as x
        # then get the BTCBNB price and calculate: quote_amount / x / current_price
        # e.g., (1000 USD / 250 BNBUSD = 4 BNB) / 212 BTCBNB = .01886 BTCBNB ???
    elif (quantity <= 0):
        print("No quantity. Both quote_amount and quantity parameters are 0")
        return log
    # quantity with fee won't be calculated correctly if we don't round to precision first.
    # quantity = round(quantity,precision)
    log['quantity'] = "{:0.0{}f}".format(quantity, precision)
    buy_quantity_plus_fee = quantity #* 1.002 # maybe try to make up fees on the maker sell instead?
    # This quantize function eliminates the need for my function:
    # get_precision_as_int. Rounding down is important here.
    if (precision == 0):
        buy_quantity_plus_fee = math.floor(buy_quantity_plus_fee)
    else:
        buy_quantity_plus_fee = decimal.Decimal(
            buy_quantity_plus_fee).quantize(decimal.Decimal(
                str(float(info['filters'][2]['stepSize']))), rounding=decimal.ROUND_DOWN)
    buy_quantity = "{:0.0{}f}".format(buy_quantity_plus_fee, precision)
    log['buy_quantity'] = buy_quantity
    # check if I have enough of the quote asset to proceed
    quoteAsset = info['quoteAsset']
    balance = cxn.get_asset_balance(asset=quoteAsset)
    free = float(balance['free'])
    if (market_buy == True):
        # use this if i need to buy it first at market price:
        # if it's not a market buy and I already own it
        # then use the current price calculated above
        # stop if i don't have enough of the quote asset
        if (float(buy_quantity) * current_price >= free):
            print("Free balance of quote currency is too low for market buy ("+str(round(free,precision))+" "+quoteAsset+")")
            return log
        try:
            if (test == True):
                print("Test mode, no market order executed.")
            else:
                order = cxn.order_market_buy(symbol=symbol,quantity=buy_quantity)
        except Exception as err:
            print(str(err))
            log['error_market_buy'] = str(err)
        current_price = float(order["fills"][0]["price"])
    #str(round(
    #print("market purchase price:" current_price)
    log['current_price'] = current_price
    buy_price = current_price

    # VTHO is special because its price is so low and it doesn't have enough decimals (.0421) so s
    # small change gets rounded and it's not behaving the way the code expects it to.
    # if (symbol=='VTHOUSD' or symbol=='VTHOUSDT'):
    #     loss=0.03
    #     profit=0.06
    #     log['profit_pct'] = profit
    #     log['loss_pct'] = loss

    price = None
    stop_limit_price_pre = None
    if (stop_limit_price_param > 0):
        # if i passed a stop limit price then the
        # maker price should be the stop_limit_price * (1+(profit+loss))
        price = "{:0.0{}f}".format(round(
            # stop_limit_price_param * (1 + profit + loss), # APR10 April 10
            # e.g.: current price is 20 and stop limit price is 10 then (10 / (1-0.5) * (1+.10) = 22
            stop_limit_price_param / (1 - loss) * (1 + profit), # APR10 April 10
            tick_size), tick_size)
        stop_limit_price_pre = stop_limit_price_param
    else:
        #new_quantity = quantity
        price = "{:0.0{}f}".format(round(buy_price * (1 + profit),tick_size), tick_size)
        # I was buying a low priced asset with 4 decimal places and the buy price rounded
        # to the same as the stop price, so this adjustment should help in those cases:
        if (round(buy_price,tick_size) == round(buy_price - (buy_price * (loss * .95)),tick_size)):
          buy_price = buy_price*.995
        # .02 is the amount above the limit that I want the stop to be
        stop_limit_price_pre = round(buy_price - (buy_price * loss), tick_size)

    stop_limit_price = "{:0.0{}f}".format(stop_limit_price_pre, tick_size)
    # The stop price should be based on the stop limit price, especially
    # since this function can take stop limit price as a parameter.
    # Only works this way for SELL orders:
    stop_price_pre = stop_limit_price_pre * (1 + .0005) # $1.00 of $1,000
    stop_price = "{:0.0{}f}".format(stop_price_pre, tick_size)
    log['limit_maker_price'] = price
    log['stop_price'] = stop_price
    log['stop_limit_price'] = stop_limit_price
    #runs.append({'buy_price'
    # create an OCO limit order
    # parameters: symbol, current price, percentage below, percentage above
    #time.sleep(1)
    print("In oco() function, right before order = cxn.order_oco_sell...")
    print("buy_quantity, price, stop_price, stop_limit_price:")
    print((buy_quantity, price, stop_price, stop_limit_price))
    try:
        if (test == True):
            print("Test mode, no OCO order executed.")
            print(pd.DataFrame([{
                'symbol':symbol,
                'quantity':buy_quantity,
                'price':price,
                'stopPrice':stop_price,
                'stopLimitPrice':stop_limit_price,
            }]))
            print("current price + profit: " + str(float(current_price*(1+profit))))
            print("current price + profit + loss: " + str(float(current_price*(1+(profit+loss)))))
        else:
            order = cxn.order_oco_sell(
                symbol= symbol,
                quantity= buy_quantity,
                price= price,
                stopPrice= stop_price,
                stopLimitPrice= stop_limit_price,
                stopLimitTimeInForce= 'GTC')
                # GTC - try to fill the order at this price, leave partial orders remaining if not filled.
                # IOC - try to fill the order partially at exactly this price and cancel remaining partial orders.
                # FOK - fill the order at exactly this price in one shot or do nothing
    except Exception as err:
            print(str(err))
            log['erroro_oco'] = str(err)
    return log

# Binance US
def high_low(cxn):
    today_str = date.today().strftime("%Y-%m-%d")
    binance_connection = cxn # startup_binance(tld = 'com')
    # Download all of the daily closing prices for each asset by day
    tickers = binance_connection.get_ticker()
    # Get stats for the last 24 hours, all symbols
    tickers = binance_connection.get_ticker()
    df = pd.read_json(json.dumps(tickers))
    # symbol, highPrice, lastPrice, lowPrice, openPrice, prevClosePrice,
    # priceChange, priceChangePercent, volume, weightedAvgPrice
    df2 = df[['symbol',
        'closeTime',
        'highPrice',
        'lastPrice',
        'lowPrice',
        'openPrice',
        'prevClosePrice',
        'priceChange',
        'priceChangePercent',
        'volume',
        'weightedAvgPrice']]
    df_winners = df2.sort_values(by=['priceChangePercent'],ascending=False).head(50)
    df_losers = df2.sort_values(by=['priceChangePercent'],ascending=True).head(50)
    #df_merged = pd.merge(df_winners, df_losers, on='symbol', how='outer')
    # cartesian product with the difference between the winner and loser for ranking
    df_winners['key'] = 1
    df_losers['key'] = 1
    df_merged = pd.merge(df_winners, df_losers, on='key')[['symbol_x',
        'symbol_y',
        'priceChangePercent_x',
        'priceChangePercent_y',
        'closeTime_x']]
    df_merged2 = df_merged.rename(columns={
        'symbol_x':'symbol_winner',
        'priceChangePercent_x':'priceChangeWinner',
        'symbol_y':'symbol_loser',
        'priceChangePercent_y':'priceChangeLoser',
        'closeTime_x':'closeTime'
        }, inplace = False)
    df_merged2['difference'] = df_merged2['priceChangeWinner'] - df_merged2['priceChangeLoser']
    df_merged2['closeTime'] = df_merged2['closeTime'] #datetime.fromtimestamp(round(int(df_merged2['closeTime']),10))
    df_merged2['closeTime'] = round(df_merged2['closeTime']/1000,10)
    #df_merged2['closeDate'] = format('%Y-%m-%dT%H:%M:%S', df_merged2['closeTime'])
    #os.environ['TZ'] = 'America/Los_Angeles'
    #time.tzset()
    #pd.to_datetime(df_merged2['closeTime'], unit='s').dt.strftime('%Y-%m-%d')
    # time zone is UTC I think - don't know how to fix it. Tried the above. Doesn't matter that much.
    df_merged2['closeDate'] = pd.to_datetime(df_merged2['closeTime'], unit='s').dt.strftime('%Y-%m-%d')
    pairs_full = df_merged2
    util.save(pairs_full,"data/highlow_data/pairs_full_"+today_str+".pkl")
    pairs_full_all = util.load("data/highlow_data/pairs_full_all.pkl")
    pairs_full_all = pairs_full_all.append(pairs_full)
    util.save(pairs_full,"data/highlow_data/pairs_full_all.pkl")
    # sort by the highest counts of date (highest # of days where this pair showed up in the top 50 and bottom 50 respectively).
    # add the dataframes to each other and count unique dates and then sort to find out how many times these
    # pairs show up together.
    pairs = pairs_full[['closeDate','symbol_winner','symbol_loser','difference']]
    util.save(pairs,"data/highlow_data/pairs_"+today_str+".pkl")
    pairs_all = util.load("data/highlow_data/pairs_all.pkl")
    pairs_all = pairs_all.append(pairs)
    util.save(pairs_all, "data/highlow_data/pairs_all.pkl")
    #
    pairs_count = pairs_all.groupby(['symbol_winner','symbol_loser']).count() #.sort_values(by='closeDate',ascending=False)
    pairs_count = pairs_count.rename(columns = {'closeDate':'count_of_date'}, inplace = False)
    pairs_mean = pairs_all.groupby(['symbol_winner','symbol_loser']).mean() #.sort_values(by='difference',ascending=False)
    pairs_mean = pairs_mean.rename(columns = {'difference':'mean_of_difference'}, inplace = False)
    pairs_merged = pd.merge(pairs_count, pairs_mean, on=['symbol_winner','symbol_loser'])[['count_of_date','mean_of_difference']]
    # Sort the list of pairs first by the # of days they appear together, then by the average disparity between them
    pairs_merged.sort_values(by=['count_of_date','mean_of_difference'],ascending=False)
    #pairs_merged.set_index(['symbol_winner','symbol_loser'])
    #
    # This is good. It tells me how many times AUDIOBUSD was up and ONGBTC was down as a pair and to what degree.
    # It's also critical to know if ONGBTC is ever up. Is ONGBTC ever among the Top 50 winners?
    # Mapped out how to do this on paper...
    pairs_merged = pairs_merged.reset_index()
    pairs_merged_reversed = pairs_merged.rename(columns = {'symbol_winner':'symbol_loser',
        'symbol_loser':'symbol_winner'
        }, inplace = False)
    pm_1 = pd.merge(pairs_merged, pairs_merged_reversed, on=['symbol_winner','symbol_loser'], how='left')
    # with multiindex (and not resetting the index) you have to rename the indexes a different way than you
    # rename columns. And to filter you can use something like this to filter:
    # df[np.in1d(df.index.get_level_values(1), ['Lake', 'River', 'Upland'])]
    # df[df.index.get_level_values('PBL_AWI').isin(['Lake', 'River', 'Upland'])]
    # or, you can just reset the index and use loc:
    #df = pm_1.reset_index()
    #df.loc[(df.symbol_winner=='AUDIOBUSD')]

    # Here's what we have now. We can read this as:
    # AUDIOBUSD was a winner 1 time and on average is 74 points higher than ONGBTC. ONGBTC was never in the winner column
    # so it appears as NaN. If it did ever appear in the winner column and AUDIOBUSD appeared in the loser column then
    # we'd see how many times and what the mean difference/disparity was. In my ideal scenario, the winner pair
    # ONGBTC/AUDIOBUSD would appear about as many tiems as AUDIOBUSD/ONGBTC (they'd be on the same row in this dataframe)
    # and the disparity would be about the same - or at leaset they'd both be above my minimum requirement of, say, 8 (or 16?)
    # points.
    #      symbol_winner   symbol_loser  count_of_date_x  mean_of_difference_x  count_of_date_y  mean_of_difference_y
    # 1566     AUDIOBUSD    YFIDOWNUSDT                1                73.469              NaN                   NaN
    # 1582     AUDIOBUSD       WINGUSDT                1                64.195              NaN                   NaN
    # 1583     AUDIOBUSD       WINGBUSD                1                63.185              NaN                   NaN
    # 1584     AUDIOBUSD        WINGBTC                1                65.489              NaN                   NaN
    # 1585     AUDIOBUSD        WINGBNB                1                65.547              NaN                   NaN
    # 1586     AUDIOBUSD         ONEBNB                1                63.244              NaN                   NaN
    # 1587     AUDIOBUSD         ONEBTC                1                64.407              NaN                   NaN
    # 1588     AUDIOBUSD        ONEBUSD                1                60.379              NaN                   NaN
    # 1589     AUDIOBUSD        ONEUSDT                1                64.953              NaN                   NaN
    # 1590     AUDIOBUSD         ONGBTC                1                74.217              NaN                   NaN


    # Notes:
    # pm_2 = pm_1.count occurences where this happened
    # sort by occurences descending
    # ratio = pm_2.count/pm_2.count # the closer to .5 the better. AND the higher the avg disparity the better.
    # pm_2.disparity - pm_2.disparity # the closer to 0 the better

    # Beginning attempt:
    # Identify all of the pairs that appeared winners/losers on more than one day.
    pm_1_2 = pm_1.loc[(pm_1.count_of_date_x==2)]
    # ... sort them by also showing how many had the exact opposite pairing (meaning I can bounce funds between
    # the two buying low and selling high).
    return pm_1_2.sort_values(by=['count_of_date_x','count_of_date_y', 'mean_of_difference_x'],ascending=False)
