"""This is the util module

This module contains helper functions that are not strategy specific.
"""

#__example__ = ['a','b','c']

import os
import time
import math
import decimal
from datetime import date, datetime, timedelta # for today_str

import json
import pickle
import pprint # pretty print
import pandas as pd
from binance.enums import *
from IPython.display import HTML
from binance.client import Client

# Almost always shows decimals (not scientific notation) without
# trailing zeros
pd.set_option('display.float_format', lambda x: '%g' % x)
# always show 8 digits:
#pd.set_option('display.float_format', lambda x: '%.8f' % x)

def startup_binance_from_username(username):
    """
    Load API credentials and create a connection for Binance.
    """
    # def __init__(self, api_key=None, api_secret=None, requests_params=None, tld='us'):
    api_key = None
    api_secret = None
    tld = None
    client = None
    if (username == "binance-us"):
        api_key = ""
        api_secret = ""
        tld = "us"
    elif (username == "binance"):
        api_key = ""
        api_secret = ""
        tld = "com"
    elif (username == "binance2"):
        api_key = ""
        api_secret = ""
        tld = "com"
    elif (username == "binance3"):
        api_key = ""
        api_secret = ""
        tld = "com"
    else:
        print("No matching username.")
        return None;
    client = Client(api_key = api_key, api_secret = api_secret, tld = tld)
    return client;

# def startup_binance(tld = 'us'):
#     """
#     Load API credentials and create a connection for Binance.
#     """
#     # def __init__(self, api_key=None, api_secret=None, requests_params=None, tld='us'):
#     api_key = None
#     api_secret = None
#     if tld == 'us':
#         api_key = 'AwdvQ7VmmxjgmsRk9L7t4CcnQWj81kgFEPpzv9MaTJTMA8iA47lu0kMfiJ9Qufp1'
#         api_secret = 'Am3MgkixCvPJw4UdCS4mpXQ9kJ7ndnxEVu0c3fvk0wNpZqMoptOrX9FjGM0XOru7'
#     elif tld == 'com':
#         api_key = 'HsH15bESJIptz6Bg24KM9ts589e4ErVC3cFhM231sHGtTDmrCUTMwUcwHAW2U4z2'
#         api_secret = 'qQTfXt6iPi0nMki6bKFtbcixxvn2RG6W5DQUiVqXBmzo0vqcgiXsoQInVrn33ueJ'
#     client = Client(api_key = api_key, api_secret = api_secret, tld = tld)
#     return client;

# Save Python object to disk
def save(obj, file_name):
    with open(file_name, 'wb') as f:
        pickle.dump(obj, f)

# Load Python object from disk
def load(file_name):
    with open(file_name, 'rb') as f:
        obj = pickle.load(f)
    return obj

# Which API are we using? Get the type of this connection.
def get_cxn_type(cxn):
    cxn_type = None
    if (str(type(cxn)) != "<class 'binance.client.Client'>"):
        print("Connection type not supported: " + str(type(cxn)))
        return None
    else: cxn_type = "binance"
    return cxn_type

# binance returns precision in this format: '0.001'
# so translate this into an integer. Example: 3
def get_precision_as_int(float_string):
    counter = 1
    for i in float_string:
        if (i=='1'):
            # -1 means the step size is 1.0, so we'll round to 0 later
            # Will the step size ever be 10 or 100? I don't think so.
            return 0 if counter-2 < 0 else counter-2
        counter = counter+1
    return None

def set_price_precision(info, symbol, price):
    tick_size = get_precision_as_int(info['filters'][0]['tickSize'])
    txn_price = "{:0.0{}f}".format(round(price, tick_size), tick_size)
    return txn_price

def set_quantity_precision(info, symbol, quantity):
    precision = get_precision_as_int(info['filters'][2]['stepSize'])
    quantity = decimal.Decimal(quantity).quantize(decimal.Decimal(str(float(info['filters'][2]['stepSize']))), rounding=decimal.ROUND_DOWN)
    txn_quantity = "{:0.0{}f}".format(quantity, precision)
    return txn_quantity

# binance is particular about hwo many decimal places there are in the
# price & quantity it changes for each symbol, so retrieve it
def get_symbol_info(cxn, symbol):
    """
    Get the base and quote asset for a symbol. Get the quantity
    and price precisions.

    To Do:
    [ ] Rather than run cxn.get_symbol_info() every time against
    the API, save this data in a local .pkl and refresh it every
    morning. Then load that file from this function and use it
    to get the base and quote assets and precisions instead.
    """
    # base_asset
    # quote_asset
    # tick_size is the price precision
    # step_size is the quantity precision
    # quote_asset free balance
    if (get_cxn_type(cxn) == 'binance'):
        info = cxn.get_symbol_info(symbol)
    # Convert "0.00100000" to "0.001"
    tick_size_str = str(float(info['filters'][0]['tickSize'])) # price
    step_size_str = str(float(info['filters'][2]['stepSize'])) # quantity
    # Convert "0.00100000" to 3 (as in 3 decimal places).
    tick_size = get_precision_as_int(info['filters'][0]['tickSize']) # price
    step_size = get_precision_as_int(info['filters'][2]['stepSize']) # quant
    # get the symbol's base asset and quote asset
    base_asset = info['baseAsset']
    quote_asset = info['quoteAsset']
    return base_asset, quote_asset, tick_size, step_size, tick_size_str, step_size_str

# Clear the screen in the python interpreter
def clear(): os.system('clear')

# Get the current price of a symbol
def get_current_price(cxn, symbol):
    if (get_cxn_type(cxn) == 'binance'):
        trades = cxn.get_aggregate_trades(symbol=symbol)
    current_price = None
    current_price = pd.read_json(json.dumps(trades)).sort_values(by="T",ascending=False).iloc[0]["p"]
    return current_price

# def get_txn_cost(cxn, symbol, quote_cost){

def get_quantity_from_cost(quote_cost, current_price):
    # fee_pcts=.002
    # take the quote_cost and use the current price to turn it
    # into a quantity
    # In the future, if the quote is not USD like BTCBNB
    # but I want to be able to supply a USD amount
    # then maybe I can first get the BNBUSDT price as x
    # then get the BTCBNB price and calculate: quote_cost / x / current_price
    # e.g., (1000 USD / 250 BNBUSD = 4 BNB) / 212 BTCBNB = .01886 BTCBNB ???
    quantity = quote_cost / current_price
    # quantity with fee won't be calculated correctly if we don't round to precision first
    #quantity = round(quantity, quantity_decimals)
    #log['quantity'] = "{:0.0{}f}".format(quantity, precision)
    return quantity

def get_txn_value(value, value_decimals):
    """
    Convert a price or quantity to the string with correct decimal
    places for that symbol.
    """
    if (value_decimals == "1.0"):
        print("value_decimals(): decimal string is " + value_decimals)
        value_txn = math.floor(value)
    else:
        value_txn = str(decimal.Decimal(value).quantize(decimal.Decimal(value_decimals), rounding=decimal.ROUND_DOWN))
    return value_txn


def get_txn_quantity(quantity, quantity_decimals_str, fee_pcts=0):
    """
    Deprecated. Use get_txn_value.
    """
    # fee_pcts=.002
    quantity_plus_fee = quantity * (1 + fee_pcts)
    #quantity_txn = quantity_plus_fee
    if (quantity_decimals_str == "1.0"):
        print("get_txn_quantity(): decimal string is " + quantity_decimals_str)
        quantity_txn = math.floor(quantity_plus_fee)
    else:
        quantity_txn = str(decimal.Decimal(quantity_plus_fee).quantize(decimal.Decimal(quantity_decimals_str), rounding=decimal.ROUND_DOWN))
    # decimal.Decimal(quantity_plus_fee).quantize(decimal.Decimal(quantity_decimals_str), rounding=decimal.ROUND_DOWN)
    #quantity_txn = "{:0.0{}f}".format(quantity_txn, quantity_decimals)
    return quantity_txn

def get_free_balance(cxn, quote_asset):
    if (get_cxn_type(cxn) == 'binance'):
        balance = cxn.get_asset_balance(asset=quote_asset)
    free_balance = float("{:0.0{}f}".format(float(balance['free']),8))
    return free_balance

# Sell all of an asset at market price
# if I don't have any BNB in Binance, it might
# take a small cut of the base asset and tell me that
# I have insufficient funds to sell the exact amount in my current balance.
def market_sell(cxn, symbol, quote_cost, base_quantity=0, test=True):
    # base_asset,quote_asset,t,s = get_symbol_info(cxn, symbol)
    # get quantity of the base asset
    (base_asset,
        quote_asset,
        price_decimals,
        quantity_decimals,
        price_decimals_str,
        quantity_decimals_str) = get_symbol_info(cxn, symbol)
    if (quote_cost > 0):
        current_price = get_current_price(cxn, symbol)
        base_quantity = get_quantity_from_cost(quote_cost, current_price)
    elif (base_quantity != 'all'):
        None
    else: #base quantity = all
        base_quantity = get_free_balance(cxn, base_asset)
    # submit a market order to sell that much
    txn_quantity = get_txn_quantity(base_quantity, quantity_decimals_str)
    if (test==True):
        order = {'symbol':'test'}
    else:
        try:
            print("market_sell(): %s %s" % (txn_quantity, symbol))
            order = cxn.order_market_sell(symbol=symbol,quantity=txn_quantity)
        except Exception as e: # I tried to handle the Binance Exception but I got a name error. Not sure how to reference it.
            # This can happen if the quantity is way too low
            print({'symbol':symbol,'quantity':txn_quantity})
            print(str(e))
            order = {}
    return order

# quote asset amount to buy (e.g., If BTCUSDT then the amount of USDT to spend)
def market_buy(cxn, symbol, quote_cost, base_quantity=0, test=False):
    # Things I need to make a market buy:
    #   1) current price
    #   2) quantity (or quote cost, which I can use to get the quantity of symbol)
    #   3) The price and the quantity need to start as floats, but they will
    #      end up as strings and be truncated based on tick_size and step_size (aka
    #      precision, aka decimals). The final quantities will take into account
    #      exchange fees and buy slightly more to compensate.
    log = {}
    current_price = get_current_price(cxn, symbol)
    (base_asset,
        quote_asset,
        price_decimals,
        quantity_decimals,
        price_decimals_str,
        quantity_decimals_str) = get_symbol_info(cxn, symbol)
    # quote_cost was specified if it's > 0 so calculate the quantity from that
    if (quote_cost > 0):
        base_quantity = get_quantity_from_cost(quote_cost, current_price)
    # The formatted quantity, with fees included, for the order function
    txn_quantity = get_txn_quantity(base_quantity, quantity_decimals_str)
    # get the free balance of the quote asset
    free_balance = get_free_balance(cxn, quote_asset)
    # use this if i need to buy it first at market price:
    # if it's not a market buy and I already own it
    # then use the current price calculated above
    # stop if i don't have enough of the quote asset
    order = None
    if (float(txn_quantity) * current_price >= free_balance):
        balance_error = "Free balance of quote currency is too low for market buy ("+"{:0.0{}f}".format(free_balance,price_decimals)+" "+quote_asset+")"
        pprint.pprint({"txn_quantity":txn_quantity,"current_price":current_price,"free_balance":free_balance,"quote_asset":quote_asset})
        print(balance_error)
        log['error'] = balance_error
        return log
    try:
        if (test == True):
            print("Test mode, no market order executed.")
        else:
            order = cxn.order_market_buy(symbol=symbol,quantity=txn_quantity)
    except Exception as err:
        print(str(err))
        log['error_market_buy'] = str(err)
    return order

def get_binance_balances(cxns):
    today_str = date.today().strftime("%Y-%m-%d")
    last_ran_str = load('data/binance_balances_data/last_ran_str.pkl')
    if(last_ran_str == today_str):
        print("Already ran today.")
        return load('data/binance_balances_data/binance_balances.pkl')
    bal_binance = None
    counter = 1
    for cxn in cxns:
        bal_binance = get_balances(cxn) if counter == 1 else bal_binance.append(get_balances(cxn))
        counter = counter + 1
    # Today's data.
    bal_binance['date_time'] = pd.to_datetime(datetime.now())
    bal_binance.to_csv('data/binance_balances_data/binance_balances_'+today_str+'.csv')
    save(bal_binance, 'data/binance_balances_data/binance_balances_'+today_str+'.pkl')
    # All time.
    all_time = load('data/binance_balances_data/binance_balances.pkl')
    all_time = all_time.append(bal_binance)
    all_time.to_csv('data/binance_balances_data/binance_balances.csv')
    save(all_time, 'data/binance_balances_data/binance_balances.pkl')
    last_ran_str = today_str
    save(last_ran_str, 'data/binance_balances_data/last_ran_str.pkl')
    return bal_binance

# This works if the base assets have a symbol with any of these quote assets:
# USDT, BUSD, USDC, DAI, BTC
def get_balances(cxn, full=False):
    # import rpc_crypto as cryp
    #
    binance_connection = cxn
    #
    account_info = binance_connection.get_account() # all my acct details with balances
    #print(account_info)
    balances = pd.read_json(json.dumps(account_info['balances']))
    balances = balances.loc[(balances.free > 0) | (balances.locked > 0)] # where > 0
    balances.rename(columns = {'asset':'baseAsset'}, inplace = True)
    #print(balances)
    prices = binance_connection.get_all_tickers()
    exchange_info = binance_connection.get_exchange_info()
    symbols = pd.read_json(json.dumps(exchange_info['symbols']))
    symbols = symbols.loc[symbols.status=='TRADING'][['symbol', 'baseAsset','quoteAsset']]
    # Filter the ones I want ("USDT")
    # symbol, baseAsset, quoteAsset
    symbols_usd = symbols.loc[(symbols.quoteAsset == 'USD')]
    symbols_usdt = symbols.loc[(symbols.quoteAsset == 'USDT')]
    symbols_busd = symbols.loc[(symbols.quoteAsset == 'BUSD')]
    symbols_usdc = symbols.loc[(symbols.quoteAsset == 'USDC')]
    symbols_dai = symbols.loc[(symbols.quoteAsset == 'DAI')]
    symbols_btc = symbols.loc[(symbols.quoteAsset == 'BTC')]
    symbols_bnb = symbols.loc[(symbols.quoteAsset == 'BNB')]
    symbols_eth = symbols.loc[(symbols.quoteAsset == 'ETH')]
    # Get the base currency from the trading pair
    # symbols_usdt['baseAsset']
    prices_df = pd.DataFrame(prices) # price, symbol
    prices_df['price'] = prices_df['price'].astype(float)

    # Merge like this:
    # price            symbol        baseAsset  quoteAsset
    # 1.283100e+00     BAKEBUSD      BAKE       BUSD
    # and then trim table to just price and baseAsset.
    symbols_merged_usd = pd.merge(prices_df, symbols_usd, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_usdt = pd.merge(prices_df, symbols_usdt, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_busd = pd.merge(prices_df, symbols_busd, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_usdc = pd.merge(prices_df, symbols_usdc, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_dai = pd.merge(prices_df, symbols_dai, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_btc = pd.merge(prices_df, symbols_btc, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_bnb = pd.merge(prices_df, symbols_bnb, on='symbol', how='left')[['baseAsset','price']]
    symbols_merged_eth = pd.merge(prices_df, symbols_eth, on='symbol', how='left')[['baseAsset','price']]
    #symbols_merged = pd.merge(prices_df, symbols_usdt, on='symbol', how='left')

    # Rename each price column by it's quote asset
    symbols_merged_usd.rename(columns = {'price':'usd'}, inplace = True)
    symbols_merged_usdt.rename(columns = {'price':'usdt'}, inplace = True)
    symbols_merged_busd.rename(columns = {'price':'busd'}, inplace = True)
    symbols_merged_usdc.rename(columns = {'price':'usdc'}, inplace = True)
    symbols_merged_dai.rename(columns = {'price':'dai'}, inplace = True)
    symbols_merged_btc.rename(columns = {'price':'price_btc'}, inplace = True)
    symbols_merged_bnb.rename(columns = {'price':'price_bnb'}, inplace = True)
    symbols_merged_eth.rename(columns = {'price':'price_eth'}, inplace = True)

    # store the BTCUSD price for later
    btcusd = float(prices_df['price'].loc[(prices_df.symbol=='BTCUSDT')])
    bnbusd = float(prices_df['price'].loc[(prices_df.symbol=='BNBUSDT')])
    ethusd = float(prices_df['price'].loc[(prices_df.symbol=='ETHUSDT')])
    #print(btcusd)

    # Match the base currency to balances table
    # Show price next to quantity like this:
    # baseAsset price, symbol, quoteAsset
    balances_merged = balances
    balances_merged = pd.merge(balances_merged, symbols_merged_usd, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_usdt, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_busd, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_usdc, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_dai, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_btc, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_bnb, on='baseAsset', how='left')
    balances_merged = pd.merge(balances_merged, symbols_merged_eth, on='baseAsset', how='left')

    # Usually, assets without a USD-like quote asset have a BTC asset (in Binance anyway).
    # Use this when there is no USD-like quote asset.
    balances_merged['total_btc'] = (balances_merged["free"] + balances_merged["locked"]) * balances_merged["price_btc"]
    balances_merged['total_free_btc'] = balances_merged["free"] * balances_merged["price_btc"]
    balances_merged['total_locked_btc'] = balances_merged["locked"] * balances_merged["price_btc"]
    balances_merged['BTCUSD'] = btcusd
    balances_merged['total_usd_from_btc'] = balances_merged["total_btc"] * balances_merged['BTCUSD']
    balances_merged['total_free_usd_from_btc'] = balances_merged["total_free_btc"] * balances_merged['BTCUSD']
    balances_merged['total_locked_usd_from_btc'] = balances_merged["total_locked_btc"] * balances_merged['BTCUSD']

    balances_merged['total_bnb'] = (balances_merged["free"] + balances_merged["locked"]) * balances_merged["price_bnb"]
    balances_merged['total_free_bnb'] = balances_merged["free"] * balances_merged["price_bnb"]
    balances_merged['total_locked_bnb'] = balances_merged["locked"] * balances_merged["price_bnb"]
    balances_merged['BNBUSD'] = bnbusd
    balances_merged['total_usd_from_bnb'] = balances_merged["total_bnb"] * balances_merged['BNBUSD']
    balances_merged['total_free_usd_from_bnb'] = balances_merged["total_free_bnb"] * balances_merged['BNBUSD']
    balances_merged['total_locked_usd_from_bnb'] = balances_merged["total_locked_bnb"] * balances_merged['BNBUSD']

    balances_merged['total_eth'] = (balances_merged["free"] + balances_merged["locked"]) * balances_merged["price_eth"]
    balances_merged['total_free_eth'] = balances_merged["free"] * balances_merged["price_eth"]
    balances_merged['total_locked_eth'] = balances_merged["locked"] * balances_merged["price_eth"]
    balances_merged['ETHUSD'] = ethusd
    balances_merged['total_usd_from_eth'] = balances_merged["total_eth"] * balances_merged['ETHUSD']
    balances_merged['total_free_usd_from_eth'] = balances_merged["total_free_eth"] * balances_merged['ETHUSD']
    balances_merged['total_locked_usd_from_eth'] = balances_merged["total_locked_eth"] * balances_merged['ETHUSD']

    # average all the USD-like prices
    balances_merged["price_usd"] = balances_merged[['usd','usdt','busd','usdc','dai']].astype(float).mean(axis=1)

    # Multiply to get total value
    #balances_merged['price'] = balances_merged['price'].astype(float)
    balances_merged['combined_usd_total'] = (balances_merged["free"] + balances_merged["locked"]) * balances_merged["price_usd"]
    balances_merged['locked_usd_total'] = balances_merged["locked"] * balances_merged["price_usd"]
    balances_merged['free_usd_total'] = balances_merged["free"] * balances_merged["price_usd"]
    balances_merged['total_usd'] = balances_merged[[
        'combined_usd_total',
        'total_usd_from_btc',
        'total_usd_from_bnb',
        'total_usd_from_eth']].mean(axis=1)
    balances_merged['total_free_usd'] = balances_merged[[
        'free_usd_total',
        'total_free_usd_from_btc',
        'total_free_usd_from_bnb',
        'total_free_usd_from_eth']].mean(axis=1)
    balances_merged['total_locked_usd'] = balances_merged[[
        'locked_usd_total',
        'total_locked_usd_from_btc',
        'total_locked_usd_from_bnb',
        'total_locked_usd_from_eth']].mean(axis=1)
    # if it's already in USD-like currency then just use the free+ locked balances without any conversion
    balances_merged_usd_like = balances_merged.loc[balances_merged['baseAsset'].isin(['USDT','USDC','BUSD','DAI','USD'])]
    balances_merged.loc[balances_merged['baseAsset'].isin([
        'USDT','USDC','BUSD','DAI','USD']),
        ['total_usd']] = (balances_merged_usd_like['free']
            + balances_merged_usd_like['locked'])
    balances_merged.loc[balances_merged['baseAsset'].isin(['USDT','USDC','BUSD','DAI','USD']),['total_free_usd']] = balances_merged_usd_like['free']
    balances_merged.loc[balances_merged['baseAsset'].isin(['USDT','USDC','BUSD','DAI','USD']),['total_locked_usd']] = balances_merged_usd_like['locked']

    balances_merged['api_key'] = cxn.API_KEY[0:5]
    bal = balances_merged.sort_values(by=['total_usd'],inplace=False,ascending=False)
    # total balance for assets with USDT pair
    #bal = bal[['baseAsset','free','locked','price_btc','total_btc','BTCUSD','price_usd','total_usd','total_usd_from_btc','total2_usd']]
    bal_final = bal[['api_key','baseAsset','free','locked','price_btc','price_bnb','price_eth','price_usd','total_usd','total_free_usd','total_locked_usd']]
    print(cxn.API_KEY[0:5] + " balance in USD: " + '${:,.0f}'.format(sum(bal["total_usd"].fillna(0))))
    return bal_final if full==False else bal
    # problem: USDT doesn't match with USDT so it doesn't get counted
    # and HEGIC has BUSD pair but not USDT pair. So pull multiple columns:
    # USDT, BUSD, USD, etc. and then coalesce across the columns and then
    # sum the coalesced column.

def get_usd_price_of_symbol(cxn,symbol):
    print('test')
    # GO does not have a USD trading pair.
    # First, get the trading pairs available for GO

    # Is one of them USDT,USD,USDC, or DAI?
    # Yes: convert it and return it
    # No: Now that we know it trades GOBTC, get the GOBTC price.
    # This would be a good function to make recursive.

    # Now that we know the BTC price of GO is 0.00000073 BTC,
    # check the trading pairs for BTC

    # Now that we know BTC trades with USDT (one of the 4 we're interested in)
    # Get the BTC/USDT price

    # Now that we know the BTC/USDT price is 59651.02, get the GO price
    # in USDT:
    # GOUSDT price = 0.00000073 * 59651.02 = 0.0435452446

    # recursive logic:
        # find a trading pair and get the price
        # if the quote is USDT then exit
        # if the quote is not USDT then call the function again
        # with the new trading pair/price.


# This needs to be modified. I had 10,000 GO/BTC that was worth $450 but my
# script said it was worth $1218.
def save_exchange_prices(cxn):
    # https://python-binance.readthedocs.io/en/latest/general.html
    if (get_cxn_type(cxn) == 'binance'):
        prices = cxn.get_all_tickers() # symbol prices
        info = cxn.get_account() # all my acct details with balances
        exchange_info = cxn.get_exchange_info() # for base asset and quote asset

    balances = pd.read_json(json.dumps(info['balances']))
    balances = balances.loc[(balances.free > 0) | (balances.locked > 0)] # where > 0
    balances.rename(columns = {'asset':'baseAsset'}, inplace = True)

    symbols = pd.read_json(json.dumps(exchange_info['symbols']))
        #symbols.to_csv("data/binance_balances_data/binance_symbols.csv")
    symbols = symbols[['symbol', 'baseAsset','quoteAsset']]
        # Filter the ones I want ("USDT")
    symbols_usdt = symbols.loc[(symbols.quoteAsset == 'USDT')]
        # Get the base currency from the trading pair
        # symbols_usdt['baseAsset']
        # Match the base currency to balances table

    prices_df = pd.DataFrame(prices)
    # merge the symbols with the prices
    symbols_merged_all = pd.merge(prices_df, symbols, on='symbol', how='left')
    # create a table to join on with the common field swapped
    symbols_merged_all_swapped = symbols_merged_all.rename(
        columns = {
            'baseAsset':'quoteAsset',
            'quoteAsset':'baseAsset',
            'price':'price_2nd'},
        inplace = False)
    # list all the symbols together so you can go from any base to any quote
    exchange_rates = pd.merge(symbols_merged_all, symbols_merged_all_swapped, on='quoteAsset', how='inner')
    # clean up the table by removing and renaming columns
    # add the price value between baseAsset_x and baseAsset_y
    exchange_rates['symbol_derived'] = exchange_rates['baseAsset_x'] + exchange_rates['baseAsset_y']
    exchange_rates['price_preferred'] = (
          pd.to_numeric(exchange_rates['price'])
        * pd.to_numeric(exchange_rates['price_2nd']))
    exchange_rates.rename(
        columns = {
            'baseAsset_x':'baseAsset',
            'quoteAsset':'linkAsset',
            'baseAsset_y':'quoteAsset',
            'price':'base_price',
            'price_2nd':'quote_price',
            'price_preferred':'price'},
        inplace = True)
    exchange_rates = exchange_rates[['symbol_derived','baseAsset','linkAsset','quoteAsset','base_price','quote_price','price']]
    # use this table to get a price quote in your preferred asset.
    # We got outlier prices when we did this for BTC, and it'll probably work with others.
    # So group by symbol_derived, quoteAsset, and take the median of "price". Choose
    # the quote Asset that you want.
    exchange_rates_final = exchange_rates
    gk = exchange_rates_final.loc[(exchange_rates_final.quoteAsset=='USDT')].groupby('baseAsset').median()
    # gk = exchange_rates_final.loc[(exchange_rates_final.quoteAsset=='BTC')].groupby('baseAsset').median()
    # This fixes the problem from earlier. Now this returns USD prices for my whole
    # portfolio. But it could return BTC prices, or any other currrency instead:
    #   Show price next to quantity
    balances_merged = pd.merge(balances, gk, on='baseAsset', how='left')
    #   Multiply to get total value
    #   balances_merged['price'] = balances_merged['price'].astype(float)
    balances_merged['total'] = balances_merged["price"] * balances_merged["free"]
    return balances_merged.sort_values(by=['total'],inplace=False,ascending=False)
    # This works really well for USDT but it's not complete for any other currency.
    # Some currencies will probably need 3 or more hops until they can get to any
    # other currency. This sounds like a graphing problem. I may not care to solve
    # it at the moment. This data is probably easily accessible somewhere else.

def get_last_x_candles(cxn, symbol, candle_span = 15, candle_count = 10):
    candles = None
    candle_span_constant = Client.KLINE_INTERVAL_15MINUTE
    #threshold = 0.82 # 83.333% (5/6) for 15 minute candles
    if (candle_span == 5):
        candle_span_constant = Client.KLINE_INTERVAL_5MINUTE
    elif (candle_span == 60):
        candle_span_constant = Client.KLINE_INTERVAL_1HOUR
    elif (candle_span == 1440):
        candle_span_constant = Client.KLINE_INTERVAL_1DAY
        #threshold = 0.79 # 80% for 8/10 for 5 minute candles
    if (get_cxn_type(cxn) == 'binance'):
        candles = cxn.get_klines(symbol=symbol, interval=candle_span_constant)
    df_candles = pd.DataFrame(candles)
    df_candles.rename(columns = {
            0:'open_time',
            1:'open',
            2:'high',
            3:'low',
            4:'close',
            5:'volume',
            6:'close_time',
            7:'quote_asset_volume',
            8:'trade_count',
            9:'taker_buy_base_volume',
            10:'taker_buy_quote_volume',
            11:'ignore'},
        inplace=True)

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
    # sort by time descending
    df_candles = df_candles.sort_values(by=['open_time'], ascending=False)
    # df_candles[12] = pd.to_datetime(round(df_candles[0]/1000,0), unit='s').dt.strftime("%Y-%m-%d %H:%M:%S")
    # candle is red if close is lower than open, green otherwise
    # red candle: pd.to_numeric(df_candles[4])-pd.to_numeric(df_candles[1])
    # how many of the last 5 candles are red?
    df_candles['change'] = pd.to_numeric(df_candles['close'])-pd.to_numeric(df_candles['open'])
    df_candles_last_5 = pd.DataFrame(df_candles.head(candle_count))
    df_candles_last_5['symbol'] = symbol
    return df_candles_last_5

# use the result of get_last_x_candles as a parameter
def find_red_candles(candles, threshold):
    # threshold - what % of the candles should be red

    # df_candle_vector = df_candles_last_5[0]
    # df_candle_vector['change'] = pd.to_numeric(df_candles_last_5[4])-pd.to_numeric(df_candles_last_5[1])
    # 80% of the last candle_count candles must be all below 0.
    # A downward trend that we will recover from
    # print(df_candle_vector[(df_candle_vector<0)].count())
    # print(candle_count)
    # print(df_candle_vector[(df_candle_vector<0)].count() / candle_count)
    # print(threshold)
    # candles are mostly red or mostly green
    # AND...
    # the open price is < the last open price on each candle (red candles)
    # the open price is > the last open price on each candle (green candles)
    # the volume is a certain amount (frequent trading volume -> smaller spread -> more likely
    # my stop loss orders won't get skipped.
    #return df_candle_vector[(df_candle_vector<0)].count()
    #/ candle_count >= threshold or df_candle_vector[(df_candle_vector>0)].count()
    #/ candle_count >= threshold
    df_candle_vector = pd.to_numeric(candles['close'])-pd.to_numeric(candles['open'])
    return {'red_count':df_candle_vector[(df_candle_vector<0)].count(), # red
    'green_count':df_candle_vector[(df_candle_vector>0)].count(), # green
    'candle_count':len(df_candle_vector),
    'threshold':threshold}

# pattern in the format: 'rrggzz' for red,red,green,green,zero,zero
# pattern is in the order you want them to appear chronologically
def has_pattern(candles, pattern): # based on red or green
    pattern = pattern[::-1] # reverse the string so it goes back in time
    # because that's how the iterator is moving through time.
    validate = ''
    for index,candle in candles.iterrows():
        if candle['change'] < 0:
            validate = validate + 'r'
        elif candle['change'] > 0:
            validate = validate + 'g'
        else:
            validate = validate + 'z'
    if (len(pattern) != len(validate)):
        raise ValueError("pattern length does not match number of candles")
    return {'result':pattern == validate}

# loop through every asset and see and check the last 6 candles
# write a cron to run this program every 15 minutes.
def red_candles(cxn):
    print(test)
    # pull all of the symbols
    # filter on a certain volume
    # make sure that they're trading
    # filter out any I already have a balance > $10 on
    # from the rest, run get_last_5_candles and if it's True then buy it with an oco order.
    # repeat this until my free usdt, usd, busd, btc, eth, bnb are all < $500 in value

# has a drop of a certain % amount within 4-6 candles.
# a function to analyze # of candles, and biggest percentage drop
# from the first to the last. The last x candles.
def pct_change(candles):
    # print('has a drop of a certain % amount within 4-6 candles.')
    # pass some candles to this function
    # take the high/low avg of the first candle
    # and the high/low avg of the last candle
    # get the % change.
    # the function will return the pct change for this set of candles.
    # candles are returned from the above function sorted with the
    # most recent (the last candle) at the top.
    open_start = float(candles.iloc[len(candles)-1]['open'])
    close_start = float(candles.iloc[len(candles)-1]['close'])
    avg_start = float((open_start+close_start)/2)

    open_end = float(candles.iloc[0]['open'])
    close_end = float(candles.iloc[0]['close'])
    avg_end = float((open_end+close_end)/2)

    pct = (avg_end - avg_start) / avg_start
    # Print the symbol and its pct change
    print("{:0.0{}f}".format(pct,4)+"\t"+candles['symbol'].iloc[0])
    return {'pct_change':pct}

def get_all_symbols_from_base_asset(cxn,base_asset):
    prices = cxn.get_all_tickers()
    exchange_info = cxn.get_exchange_info()
    symbols = pd.read_json(json.dumps(exchange_info['symbols']))
    symbols = symbols.loc[symbols.status=='TRADING'][['symbol', 'baseAsset','quoteAsset']]
    prices_df = pd.DataFrame(prices) # price, symbol
    prices_df['price'] = prices_df['price'].astype(float)
    # merge the symbols and price info
    symbols_prices = symbols.merge(prices_df, on='symbol', how='inner')
    # filter the symbols table to just those associated with this base asset
    symbols_prices_base_asset = pd.DataFrame(symbols_prices.loc[symbols_prices['baseAsset']==base_asset])
    return symbols_prices_base_asset

def get_symbol_from_base_asset(cxn, base_asset):
    all_symbols = get_all_symbols_from_base_asset(cxn, base_asset)
    quotes_ranked = pd.DataFrame([
        {'quoteAsset':'USD' ,'rank':1},
        {'quoteAsset':'USDT','rank':2},
        {'quoteAsset':'BUSD','rank':3},
        {'quoteAsset':'USDC','rank':4},
        {'quoteAsset':'BNB' ,'rank':5},
        {'quoteAsset':'ETH' ,'rank':6},
        {'quoteAsset':'BTC' ,'rank':7}
    ])
    symbols_ranked = all_symbols.merge(quotes_ranked, on='quoteAsset', how='inner')
    ranking = symbols_ranked.groupby('baseAsset')['rank'].rank(method='min')
    ranking_df = pd.DataFrame(ranking)
    symbol = pd.DataFrame(symbols_ranked.loc[ranking_df['rank']==1])
    symbol = symbol.reset_index(drop=True)
    return symbol

def stop_loss_limit(cxn,symbol,quantity,price,stop_price=None):
    # ORDER_TYPE_STOP_LOSS sells at market price
    # ORDER_TYPE_STOP_LOSS_LIMIT sells at a price you determine
    if (stop_price == None):
        stop_price = price
    order = cxn.create_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_STOP_LOSS_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=quantity,
        stopPrice=price,
        price=price
    )

def create_or_adjust_buy_side_stop_loss_order(cxn, symbol, base_asset, current_price, profit_pct, loss_pct, quote_cost):
    print("")
    print("************************************")
    print("Inside create_or_adjust_buy_side_stop_loss_order...")
    print("************************************")
    print("Current Price: " + str(current_price))
    side = "BUY"
    market_price = None
    buy_order = None
    # Is None if there are no open buy side stop loss orders
    current_stop_loss_price = get_price_of_open_stop_loss_order(cxn, symbol, side=side)

    # Since I'm returning these, we need to have them in case
    # the if statement is not met.
    log_cancel = None
    market_price = None
    buy_order = None

    # If there are no current orders,
    # or if there are but the price has gone down since it was placed,
    # then create a buy limit order based on the current price.
    if (current_stop_loss_price == None
        or (current_stop_loss_price != None
            and current_price * (1 + loss_pct) < current_stop_loss_price
        )
    ):
        log_cancel = cancel_all_existing_orders(cxn, base_asset, side=side)
        market_price, buy_order = oco_buy_from_current_price(cxn, symbol, profit_pct, loss_pct, quote_cost, current_price=current_price)
    return (log_cancel, market_price, buy_order)

def get_symbols_not_held(cxn, quote_asset_to_filter_on='USD'):
    # get all assets on the exchange with a USD equivalent
    info = cxn.get_exchange_info()
    df_info = pd.DataFrame(info['symbols'])
    df_info_trading = df_info[['symbol','baseAsset','quoteAsset']].loc[(df_info['status']=='TRADING')]
    df_info2_wo_stablecoins = df_info_trading.loc[(~df_info_trading['baseAsset'].isin(['USD','USDC','DAI','USDT','BUSD']))]
    df_info2_usd = df_info2_wo_stablecoins.loc[(df_info2_wo_stablecoins['quoteAsset'] == quote_asset_to_filter_on)]

    # Which of the exchange's assets do I already have a position in?
    # Remove them from my list of possible buys.
    # I only want to own 1 stake in an asset at a time, and each asset
    # should have the same amount ($100 right now)
    # Remove BNB which I #use for paying fees and remove stablecoins
    # that don't change in value. Remove others as needed. and make sure
    # they're currently tradeable.
    oco_bal = get_balances(cxn)
    # to me, dust is less than $10
    oco_bal_wo_dust = oco_bal.loc[oco_bal['total_usd']>=10].sort_values(by=['total_usd'],ascending=False)
    oco_bal_wo_specific_currencies = oco_bal_wo_dust.loc[~oco_bal_wo_dust['baseAsset'].isin(['BNB','USDT','USDC','BUSD','USD','BTC','DAI'])]
    #oco_merged = df_info2_usd.merge(oco_bal_wo_dust, on='baseAsset',how='left')
    oco_merged = df_info2_usd.merge(oco_bal_wo_specific_currencies, on='baseAsset',how='left')
    # assets I do not have a position in right now:
    oco_no_position = oco_merged.loc[oco_merged['total_usd'].fillna(0) == 0][['symbol','baseAsset']] #,'baseAsset','quoteAsset']]
    return oco_no_position


def adjust_existing_buy_side_stop_loss_orders(cxn, symbol_prices, all_open_orders):
    """
    Run this step every time continuous_oco_stop_loss runs.
    Run it after the script buys and sells assets.
    """
    # Binance will return all open orders without a symbol but
    # this API doesn't support it. Ideally I would adjust the
    # function myself but it will be faster for me to just
    # code iterating through every USD asset I don't own.

    print("adjust_existing_buy_side_stop_loss_orders(cxn)...")

    side = "BUY"
    profit_pct = 0.20
    loss_pct = 0.02
    quote_cost = 250

    # pull symbols I am not holding
    symbols_not_held = get_symbols_not_held(cxn)

    # pull assets I have buy side stop loss orders on
    # for each one, create or adjust a buy side stop loss order
    if (len(all_open_orders) > 0):
        for index, row in symbols_not_held.iterrows():
            symbol = row['symbol']
            base_asset = row['baseAsset']
            # will return a series object even if there's only one item
            # because the conditional *could* return multiple items...
            #current_price = symbol_prices.loc[symbol_prices['symbol']==symbol,'price']
            # ...whereas a specific index must be unique so this returns
            # the raw value
            symbol_prices_indexed = symbol_prices.set_index('symbol')
            current_price = float(symbol_prices_indexed.loc[symbol,'price'])

            print("")
            print("Inside adjust_existing_buy_side_stop_loss_orders()...")
            print("============================")
            print("symbol: " + symbol)
            print("current_price: " + str(current_price))
            # Get open orders
            #Old way:
            #open_orders = pd.DataFrame(cxn.get_open_orders(symbol=symbol))
            open_orders = all_open_orders.loc[all_open_orders['symbol']==symbol]
            if (len(open_orders) > 0):
                orders_filtered = open_orders.loc[(
                    open_orders['side']==side)
                    & (open_orders['status']=='NEW')
                    & (open_orders['type']=='STOP_LOSS_LIMIT')]
                # print("orders_filtered:")
                # print(orders_filtered)
                # doesn't matter how many orders there are, I just want
                # the symbol name and I'll let the function I'm calling
                # handle the rest.

                # If there are open orders on this symbol, then call
                # the function to adjust them
                if (len(orders_filtered)>0):
                    log_cancel, market_price, buy_order = create_or_adjust_buy_side_stop_loss_order(cxn, symbol, base_asset, current_price, profit_pct, loss_pct, quote_cost)
                    # print("log_cancel:")
                    # print(log_cancel)
                    # print("market_price:")
                    # print(market_price)
                    # print("buy_order:")
                    # print(buy_order)
                else:
                    print("No open stop loss orders on the %s side for %s" % (side, symbol))
            else:
                print("No open orders on the %s side for %s" % (side, symbol))
    else:
        print("No open orders in this account.")


def oco_buy_from_current_price(
    cxn,
    symbol,
    profit_pct,
    loss_pct,
    quote_cost,
    stop_pct=.998,
    current_price=None
    ):
    """
    Returns the current price, and the OCO buy order from Binance API.
    """
    print("")
    print("####################################")
    print("Inside oco_buy_from_current_price...")
    print("####################################")
    # we have to use the current_price from earlier, when the decision
    # to cancel the order was made, otherwise the price fluctuates
    # between the time the order was canceled and the time this new
    # order is sent.
    print("current_price (before if...): " + str(current_price))
    if (current_price == None):
        current_price = get_current_price(cxn, symbol)

    print("current_price: " + str(current_price))
    price_dict = get_prices_for_oco_buy(current_price, profit_pct, loss_pct)
    (market_price_at_buy, buy_order) = oco_buy(cxn, symbol, price_dict, quote_cost, test=False)
    #print("Market price at buy: " + market_price_at_buy)
    #pprint.pprint(buy_order)
    return (current_price, buy_order)

# start_price will usually be the asset's current price.
def get_prices_for_oco_buy(current_price, profit_pct, loss_pct, stop_pct=.998):
    """
    Take the current price, profit %, and loss % and return 3 values:
    - price
    - limit price
    - stop price
    """
    limit_price = current_price * (1 + loss_pct)
    stop_price = limit_price * stop_pct
    price = current_price * (1 - profit_pct)
    return {
        'current_price':current_price,
        'price':price,
        'stop_price':stop_price,
        'limit_price':limit_price
    }

def oco_buy(cxn, symbol, prices, quote_cost=0, quantity=0, test=False):
    """
    Submit a buy OCO order.

    The funny thing about setting a quote cost on the buy side is that
    it sets the quantity before the order goes in which means my $1,000
    buy will actually be an $800 buy if it goes in at the maker price
    and $1,025 at the limit price. I've decided to make the quantity
    align with the limit price since I'm writing this function at the
    same time that I'm writing the script that chases the price down
    and resets the OCO order each time and the maker price is irrelevant.
    """
    params = {
        'symbol':symbol,
        'quote_cost':quote_cost,
        'quantity':quantity
#        'test':test
    }

    print("------------------------------------------")
    print("Entering order_oco_buy...")
    print("------------------------------------------")
    print("Parameters passed...")
    print(pd.DataFrame([params]))
    print(pd.DataFrame([prices]))
    current_price = prices['current_price']
    price = prices['price']
    stop_price = prices['stop_price']
    limit_price = prices['limit_price']
    order = None

    (base_asset,
        quote_asset,
        price_decimals,
        quantity_decimals,
        price_decimals_str,
        quantity_decimals_str) = get_symbol_info(cxn, symbol)

    if (quote_cost > 0):
        # Don't use the current price, use the limit price.
        # (See docstring)
        quantity = get_quantity_from_cost(quote_cost, limit_price)

    quantity_txn = get_txn_value(quantity, quantity_decimals_str)
    price_txn = get_txn_value(price, price_decimals_str)
    stop_price_txn = get_txn_value(stop_price, price_decimals_str)
    limit_price_txn = get_txn_value(limit_price, price_decimals_str)

    if (test == True):
        # just for testing
        ts = round(time.time()*1000)
        order = {
            'contingencyType': 'OCO',
            'listClientOrderId': 'TEST_ORDER',
            'listOrderStatus': 'EXECUTING',
            'listStatusType': 'EXEC_STARTED',
            'orderListId': 00000,
            'orderReports': [{'clientOrderId': 'xxxxxxxxxxxxxxxxxxxxxx',
                               'cummulativeQuoteQty': '0.0000',
                               'executedQty': '0.00000000',
                               'orderId': 0000000,
                               'orderListId': 00000,
                               'origQty': quantity_txn,
                               'price': limit_price_txn,
                               'side': 'BUY',
                               'status': 'NEW',
                               'stopPrice': stop_price_txn,
                               'symbol': symbol,
                               'timeInForce': 'GTC',
                               'transactTime': ts,
                               'type': 'STOP_LOSS_LIMIT'},
                              {'clientOrderId': 'zzzzzzzzzzzzzzzzzzzzzz',
                               'cummulativeQuoteQty': '0.0000',
                               'executedQty': '0.00000000',
                               'orderId': 9999999,
                               'orderListId': 99999,
                               'origQty': quantity_txn,
                               'price': price_txn,
                               'side': 'BUY',
                               'status': 'NEW',
                               'symbol': symbol,
                               'timeInForce': 'GTC',
                               'transactTime': ts,
                               'type': 'LIMIT_MAKER'}],
            'orders': [{'clientOrderId': 'xxxxxxxxxxxxxxxxxxxxxx',
                         'orderId': 0000000,
                         'symbol': symbol},
                        {'clientOrderId': 'zzzzzzzzzzzzzzzzzzzzzz',
                         'orderId': 9999999,
                         'symbol': symbol}],
            'symbol': symbol,
            'transactionTime': ts
         }

    else:
        # SINCE THE PURPOSE IS TO SET STOP SELL ORDERS, MAYBE DO THAT
        # INSTEAD OF OCO ORDERS SINCE THE TAKE PROFIT QUANTITY ISN'T
        # REALLY WHAT YOU WOULD WANT IT TO BE ANYWAY. OR JUST LEAVE IT
        # BECAUSE IT'S A STOP GAP IN CASE THE SCRIPT FAILS.
        print("Prior to cxn.order_oco_buy...")
        to_print = {
            'symbol' : symbol,
            'quantity' : quantity_txn,
            'price' : price_txn,
            'stopPrice' : stop_price_txn,
            'stopLimitPrice' : limit_price_txn,
            'stopLimitTimeInForce' : 'GTC'
        }
        print(pd.DataFrame([to_print]))
        try:
            order = cxn.order_oco_buy(
                symbol = symbol,
                quantity = quantity_txn,
                price = price_txn,
                stopPrice = stop_price_txn,
                stopLimitPrice = limit_price_txn,
                stopLimitTimeInForce = 'GTC')
            # GTC - try to fill the order at this price, leave partial
            #       orders remaining if not filled.
            # IOC - try to fill the order partially at exactly this price
            #       and cancel remaining partial orders.
            # FOK - fill the order at exactly this price in one shot or
            #       do nothing
        except Exception as e:
            print(str(e))

    print("")
    return (current_price, order)


def get_price_of_open_stop_loss_order(cxn, symbol, side):
    """
    get_asset's_current_lowest_buy_side_stop_loss_price()
    """
    highest_stop_loss_price = None
    asc = False
    if (side=="BUY"):
        asc = True

    orders = pd.DataFrame(cxn.get_all_orders(symbol=symbol, limit=10))

    if(len(orders)>0):
        orders_filtered = orders.loc[(
            orders['side']==side)
            & (orders['status']=='NEW')
            & (orders['type']=='STOP_LOSS_LIMIT')]
        if (len(orders_filtered)>0):
            orders_sorted = orders_filtered.sort_values(by='price', ascending=False)
            # iloc[0] will take the first row now matter what the indexes
            # are or how it's sorted so don't change this.
            order_to_cancel = orders_sorted.iloc[0]
            order_id_to_cancel = order_to_cancel.orderId
            highest_stop_loss_price = float(order_to_cancel.price)

    return highest_stop_loss_price


# def get_price_of_open_stop_loss_order(side='buy'):
#     """
#     """
#     return None

def cancel_all_existing_orders(cxn, base_asset, side=None):
    # Set up a log for the order result.
    log_cancel = pd.DataFrame()
    symbols = get_all_symbols_from_base_asset(cxn,base_asset)
        #orders_all = None
    for index,row in symbols.iterrows():
        # Get the orders for this symbol, e.g., 'BNBUSDT'
        symbol = row['symbol']
        orders = pd.DataFrame(cxn.get_all_orders(symbol=symbol, limit=10))
        print ("")
        print("Cancel all existing orders of %s. Found %s orders:" % (symbol, len(orders)))
        print(orders)
        orders.to_csv('log_related/cancel_all_existing_orders-orders.csv')
        # If a side is specified, only cancel orders on that side
        if (side != None and len(orders)>0):
            orders = orders.loc[orders['side']==side.upper()]
        # Only new (unfilled) orders.
        if (len(orders)>0):
            orders_new = orders.loc[orders['status']=='NEW']
            # New (unfilled) orders exist so let's cancel them.
            for index,row in orders_new.iterrows():
                order_id = row['orderId']
                print(order_id)
                result="No results"
                try:
                    result = cxn.cancel_order(symbol=symbol,orderId=order_id)
                    log_cancel = log_cancel.append(pd.DataFrame([result]))
                except Exception as e: # I tried to handle the Binance Exception but I got a name error. Not sure how to reference it.
                    # Usually this just happens because an OCO cancel
                    # resulted in another OCO cancel that I'm not building
                    # logic around avoiding trying to cancel an already canceled order
                    # because canceling one cancels the other automatically and then it no longer exists.
                    # No harm no foul though. Just print what happened. But it messes up the
                    # log_cancel dataframe... I think.
                    print(str(e))
    print(log_cancel)
    return log_cancel

# This is the price I would need the asset to be (in USD) in order to get
# 900 for the quantity.
def get_stop_loss_price_in_usd_from_usd_quote(cxn, quote_asset, quantity, start_usd):
    usd_assets = ['USD','USDT','BUSD','USDC','DAI']
    if (quote_asset in usd_assets):
        limit_price = start_usd / quantity
    else:
        quote_asset_symbol_df = get_symbol_from_base_asset(cxn, quote_asset)
        quote_asset_of_quote_asset = quote_asset_symbol_df['quoteAsset'][0]
        quote_asset_symbol = quote_asset_symbol_df['symbol'][0]
        if (not quote_asset_of_quote_asset in usd_assets):
            print("The High/Low asset "+base_asset+" has a quote asset \
                ("+quote_asset+") with no USD-like trading pair and so we \
                can't figure out what price to set the $"+start_usd+" USD \
                equivalent stop loss order to.")
        else:
            quote_asset_symbol_price = get_current_price(cxn, quote_asset_symbol)
            # E.g., if the symbol is FETBTC then this is the price at which to sell FETBTC to stop loss at $1,000.
            # (1000 USD / 57652 USD) / 16227 FET where 57652 USD is the current price of BTC ==> 0.00001062 BTC per FET
            limit_price = (start_usd / quote_asset_symbol_price) / quantity
    return limit_price


def collect_proceeds(
    cxn,
    pct_to_keep = 0.025,
    threshold = 0.025,
    pct_of_portfolio = 0.015,
    start_amount = 1000,
    path_to_log='data/highlow_updown/highlow_updown.pkl',
    path_to_html='data/highlow_updown/highlow_updown.html'):
    # cxn = startup_binance_from_username('binance')
    # pct_to_keep = 0.025
    # threshold = 0.025
    # pct_of_portfolio = 0.015
    # start_amount = 1000
    # path_to_log='data/highlow_updown/highlow_updown.pkl'
    # path_to_html='data/highlow_updown/highlow_updown.html'

    proceeds_pct_to_keep = pct_to_keep
    proceeds_threshold = threshold
    highlow = cxn
    log_path = path_to_log
    start_amount_usd = start_amount

    # #################################################
    # Variables
    # #################################################
    # -----------------------------------
    # Current date and time for logs
    # -----------------------------------
    now = datetime.now()
    dt_string = now.strftime("%a, %b %d, %Y %H:%M:%S")
    dt_string_filename = now.strftime("%Y-%m-%d_%H%M.%S")

    print(" -------------------------------------------------------------------------------")
    print(" Continuous High/Low " + dt_string)
    print(" -------------------------------------------------------------------------------")

    # -------------------------------------------------
    # pct_to_keep = 0.025
    # -------------------------------------------------
    # Always keep extra proceeds, say $25, when selling to account for price dips

    # -------------------------------------------------
    # threshold = 0.025
    # -------------------------------------------------
    # The script might sell 10 cents of an asset if the gains are $25.10
    # so set a threshold for $25 to use later on when
    # filtering the "balances_gain" table.

    # -------------------------------------------------
    # pct_of_portfolio = 0.015
    # -------------------------------------------------
    # Capture 1.5% of the portfolio each time we sell. Only applies
    # to selling anything that sums to 1.5% of the
    # portfolio's total value.

    # -------------------------------------------------
    # start_amount_usd = 1000
    # -------------------------------------------------
    # USD spent on purchase

    # -------------------------------------------------
    # Log some key numbers:
    # -------------------------------------------------
    # 1) What time this ran.
    # 2) Total Portfolio balance in USD
    # 3) The "message" variable
    # 4) Each asset over start_amount_usd
    # 5) The amount over start_amount_usd
    # -------------------------------------------------
    log = pd.DataFrame() #columns=['time','portfolio_bal','portfolio_gain','message','base_asset','gain','proceeds'])
    # Try loading the log file now rather than finding
    # out it doesn't exist at the end of the script.
    try:
        load(log_path)
    except Exception as err:
        #save(log, log_path)
        print("log file does not exist")
    log_saved = log

    # -----------------------------------
    # Download data
    # -----------------------------------
    # Get current balances & portfolio total USD
    balances = get_balances(highlow)
    total_portfolio_usd = sum(balances['total_usd'].fillna(0))

    # Save to "balances_gain": assets above $1,000 & not a USD currency
    # "gain" stores the total gain (proceeds/profit) at this moment
    balances['start_usd'] = start_amount_usd
    # Exclude BTC because if I sell something at a loss to BTC and it pushes
    # BTC over $1000 then it sells it as proceeds which is inaccurate.
    balances_gain = balances.loc[(balances['total_usd']>balances['start_usd']) & ~balances['baseAsset'].isin(['BNB','USDT','USDC','BUSD','BTC','ETH'])]
    balances_gain = pd.DataFrame(balances_gain)
    balances_gain['pct_gain'] = (balances_gain['total_usd']-balances_gain['start_usd'])/balances_gain['start_usd']
    balances_gain = balances_gain.fillna(0)
    gain = sum(balances_gain['total_usd']-balances_gain['start_usd'])
    log['portfolio_gain'] = gain

    # Gain as a percent of the portfolio's total value
    pct_gain_total = gain / sum(balances['total_usd'].fillna(0))

    # -----------------------------------
    # Check every 5 minutes to see if the
    # asset value is more than 5% ($50)
    # over $1,000. If yes, leave $25 and
    # take the rest. Then set a stop loss
    # for $1,000.
    # -----------------------------------
    # Print a message summarizing the gain.
    more_less = "more" if pct_gain_total >= pct_of_portfolio else "less"
    message = "The total gain is "+f'{gain:0.2f}'+" ("+f'{pct_gain_total*100:0.1f}'+"%), which is "+more_less+ \
        " than the "+f'{pct_of_portfolio*total_portfolio_usd:0.2f}'+" ("+f'{pct_of_portfolio*100:0.1f}'+"%) needed for taking profit."
    print(message)

    # If no asset is above $1,000, make it known
    print(" No proceeds to collect." if pct_gain_total <= pct_of_portfolio else "")

    # -----------------------------------
    # Collect proceeds and set a stop loss.
    # -----------------------------------
    # This is the central part of the script.
    #
    # 1) Run through every asset with a gain
    # 2) Cancel any existing orders that might lock up funds
    # 3) Sell the gain (minus $25)
    # 4) Set a stop loss on the remaining $1025 to sell at $1,000
    #    (but hopefully capturing a few more gains before that happens)
    # -----------------------------------

    # Calculate how much of each asset to sell.
    # E.g., we have 100 FET and it has gained 5% value.
    # Sell 5%-2.5% = 2.5% * (free + locked quantity of FET)
    # ( total_usd - start_usd * 1.025 ) / total_usd * total_quantity_of_asset # where 1.025 is 1 + threshold
    balances_gain['quantity_sell'] = (
            (
                (   balances_gain['total_usd']
                    - (balances_gain['start_usd'] * (1 + threshold))
                )
                / balances_gain['total_usd']
            )
            * (balances_gain['free'] + balances_gain['locked'])
    )
    # Sometimes we only earned a small amount so filter those assets out.
    # balances_gain = $1,000 x 2.5% = $25 minimum gain
    balances_gain['usd_gain'] = balances_gain['total_usd'] - balances_gain['start_usd']
    balances_gain['usd_keep'] = balances_gain['start_usd'] * proceeds_pct_to_keep
    balances_gain['usd_threshold'] = balances_gain['start_usd'] * proceeds_threshold
    balances_gain['usd_proceeds'] = balances_gain['usd_gain'] - balances_gain['usd_threshold']
    # alternative further down: balances_gain['usd_proceeds'] = balances_gain['quantity_sell'] - balances_gain['price_usd']

    #----
    # a bit of a hack just to get the HTML to show me assets that have a gain, but no proceeds.
    # later, use the line "if (quantity_sell>0)" below to do this more simply after passing "balances_gain_no_proceeds" to the for loop
    balances_gain_no_proceeds = balances_gain.loc[
          (balances_gain['usd_gain'] > 0)
        & (balances_gain['usd_gain'] < start_amount_usd * (proceeds_pct_to_keep + proceeds_threshold))
    ]
    # if there's nothing to sell, still show what the gains are per asset.
    for index,row in balances_gain_no_proceeds.iterrows():
        log = log.append(pd.DataFrame([{
            'time':now,
            'portfolio_bal':total_portfolio_usd,
            'portfolio_gain':gain,
            'message':message,
            'base_asset':row['baseAsset'],
            'gain':row['usd_gain'],'proceeds':0}]))

    # the real dataframe with proceeds
    balances_gain = balances_gain.loc[balances_gain['usd_gain'] > start_amount_usd * (proceeds_pct_to_keep + proceeds_threshold)]

    # Loop through the assets that have gains
    for index,row in balances_gain.iterrows():
        # row = balances_gain.squeeze() to turn the dataframe into a
        # series during testing.
        # here's how to change the value in a dataframe:
        # df.loc[100,'proceeds'] = '28 USDT' # row, column
        quantity_sell = row['quantity_sell'] # amount of base asset to sell
        usd_keep = row['usd_keep'] # amount of base asset to sell
        print({'usd_keep':usd_keep})

        # Only proceed if we have something to sell.
        # Probably unnecessary to check this but keep it for now.
        if (quantity_sell>0):
            # We can collect proceeds in any currency. Find which are available
            # and pick a symbol based on a hard coded priority (USD, USDT, etc.)
            symbol_df = get_symbol_from_base_asset(highlow, row['baseAsset']).reset_index(drop=True)
            symbol = symbol_df['symbol'].iloc[0]
            base_asset = symbol_df['baseAsset'].iloc[0]
            quote_asset = symbol_df['quoteAsset'].iloc[0]
            start_usd = row['start_usd']
            total_usd = row['total_usd']
            quantity_base_asset = row['free']+row['locked']
            proceeds_usd = row['usd_proceeds']

            # Check for existing orders on this symbol before placing a market
            # order. Then cancel any that we find.
            canceled_orders = cancel_all_existing_orders(highlow, base_asset)

            # market sell of proceeds
            print(" ...Market sell order for "+f'{quantity_sell:0.6f}'+" of "+symbol+" ("+base_asset+"/"+quote_asset+")")
            mkt_sell_order = market_sell(highlow, symbol, quote_cost=0, base_quantity=quantity_sell, test=False)
            # proceeds = mkt_sell_order['cummulativeQuoteQty']+" "+base_asset

            # place stop loss order in USD or best possible symbol
            quantity_for_stop = (quantity_base_asset - quantity_sell)
            limit_price = get_stop_loss_price_in_usd_from_usd_quote(highlow, quote_asset, quantity_for_stop, start_usd)

            # Get proper format for quantity and price
            info = highlow.get_symbol_info(symbol)
            txn_quantity = set_quantity_precision(info, symbol, quantity_for_stop)
            txn_price = set_price_precision(info, symbol, limit_price)
            txn_stop_price = set_price_precision(info, symbol, limit_price * 1.001)
            print(" ...Stop limit order for $"+str(start_usd)+" of "+symbol+": "+str(quantity_for_stop)+" @ "+str(limit_price))

            # Place the order
            result_stop = stop_loss_limit(highlow,symbol,txn_quantity,txn_price,stop_price=txn_stop_price)

            # Set up the log
            proceeds_amount = float("{:0.0{}f}".format(quantity_sell * symbol_df['price'].iloc[0],5))
            proceeds = str(proceeds_amount) # quantity for market sell order x current price
            proceeds_quote = str(quote_asset) # sold to this quote currency
            gain_amount = round(row['total_usd']-row['start_usd'],2)
            log = log.append(pd.DataFrame([{
                'time':now,
                'portfolio_bal':total_portfolio_usd,
                'portfolio_gain':gain,
                'message':message,
                'base_asset':row['baseAsset'],
                'gain':gain_amount,
                'proceeds':proceeds,
                'proceeds_quote_asset':proceeds_quote,
                'proceeds_usd':proceeds_usd}]))

    # -----------------------------------
    # Logging and recordkeeping. Not critical.
    # -----------------------------------
    if (len(balances_gain_no_proceeds)==0):
        # This is the log entry for no gains.
        log = log.append(pd.DataFrame([{
            'time':now,
            'portfolio_bal':total_portfolio_usd,
            'portfolio_gain':gain,
            'message':message,
            'base_asset':'',
            'gain':0,
            'proceeds':0,
            'proceeds_quote_asset':'',
            'proceeds_usd':0}]))

    # Save the log to a file
    log_saved = load(log_path)
    log_saved = log_saved.append(log)
    log_saved_sorted = log_saved.sort_values(by=['time','gain'],ascending=True)
    log_saved_sorted = log_saved_sorted.reset_index(drop=True) # not sure why, but the index was 0 in every row. This fixes it.
    log_saved_sorted = log_saved_sorted.sort_values(by=['time','gain'],ascending=False)
    save(log_saved_sorted, log_path)
    # Rather than fix why there are NaNs, I just remove them.
    # This is so it displays in the HTML cleaner.
    log_saved_sorted = log_saved_sorted.fillna('')
    # remove the "message" from the log before printing to HTML
    log_saved_sorted = log_saved_sorted.drop(['message'], axis=1)
    log_saved_sorted_through_yesterday = log_saved_sorted.loc[log_saved_sorted['time'] < pd.to_datetime(datetime.now().date())]
    yesterday = pd.to_datetime(date.today() - timedelta(days=1)) #.strftime("%Y-%m-%d")
    log_saved_sorted_yesterday_only = log_saved_sorted.loc[(log_saved_sorted['time'] < pd.to_datetime(datetime.now().date())) & (log_saved_sorted['time'] > yesterday)]

    # Summarize the earnings that are in the log file
    #earnings_summary = load('data/highlow_continuous/highlow_continuous.pkl')
    earnings_summary = log_saved_sorted
    earnings_summary['date'] = earnings_summary['time'].dt.strftime('%Y-%m-%d')
    #earnings_summary[['proceeds','proceeds_quote_asset']] = earnings_summary['proceeds'].str.split(' ',expand=True)
    #log_saved[['proceeds','proceeds_quote_asset']] = log_saved['proceeds'].str.split(' ',expand=True)
    #earnings_summary[['proceeds_amt','proceeds_currency']] = earnings_summary['proceeds'].str.split(' ',expand=True)
    #earnings_summary['proceeds'] = pd.to_numeric(earnings_summary.proceeds)
    earnings_summary['proceeds_usd'] = round(pd.to_numeric(earnings_summary.proceeds_usd))
    earnings_summary = earnings_summary[['date','proceeds_usd']].fillna(0).groupby('date').sum()
    earnings_summary = earnings_summary.sort_values(by='date', ascending=False)
    #earnings_summary_through_yesterday = earnings_summary['date',] < pd.to_datetime(datetime.now().date())]
    earnings_summary_through_yesterday = earnings_summary[pd.to_datetime(earnings_summary.index) < pd.to_datetime(datetime.now().date())]
    #log_saved[log_saved['proceeds'].isnull()==False]
    # log_saved = load(log_path)
    # log_saved = log_saved[log_saved.index != 4287]
    # save(log_saved, log_path)
    #earnings_summary_through_yesterday = earnings_summary

    # Print to HTML
    html_header = "<html><body>"
    html_footer = "</body></html>"
    html_text = "<p><b>High/Low Summary</b></p><p>Here is the HighLow summary for "+dt_string+"</p><br><br>"
    # print the 7 day rolling average
    html_text = str(earnings_summary.head(7)['proceeds_usd'].mean())+"<br><br>"
    html_table_earnings_summary = str(earnings_summary_through_yesterday.to_html(classes='table table-striped'))
    # Yesterday and earlier
    #html_table_log = str(log_saved_sorted_through_yesterday.to_html(classes='table table-striped'))
    # Yesterday only
    html_table_log = str(log_saved_sorted_yesterday_only.to_html(classes='table table-striped'))
    text_file = open(path_to_html, "w")
    # With historical earnings for each time the script ran
    text_file.write(html_header+html_text+html_table_earnings_summary+"<br>"+html_table_log+html_footer)
    # Just the daily summary:
    #text_file.write(html_header+html_text+html_table_earnings_summary+html_footer)
    text_file.close()
    print(" -------------------------------------------------------------------------------")


# Stand-alone script part
# if __name__ == '__main__':
#     print("Run as standalone script.")
    # this is for unit tests, for example.
