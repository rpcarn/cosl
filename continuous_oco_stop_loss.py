import lib.util as util
import lib.strategy as strat
import pprint
import pandas as pd
from importlib import reload
from datetime import datetime
from IPython.display import HTML
import random

# current date and time
now = datetime.now()
dt_string = now.strftime("%a, %b %d, %Y %H:%M:%S")
dt_string_filename = now.strftime("%Y-%m-%d_%H%M.%S")

# OCO amount of USD to spend
quote_amount_usd = 250
profit = 0.10 # 10%
loss_sell_side = .5 #0.125 # on volatile days 0.1 seems too low
loss = 0.02   #  2%
number_of_coins = 1 # how many to purchase every 15 minutes, if available.
quote_asset_to_filter_on = 'USD'
log_cancel = pd.DataFrame()
orders_placed = pd.DataFrame()
ocos = pd.DataFrame()
html_ocos_to_buy = 'The string variable "html_ocos_to_buy" is empty!'
highest_stop_loss_price = None

# Connect to Binance
oco = util.startup_binance_from_username('binance-us')

# get all open orders
all_open_orders = pd.DataFrame(oco.get_open_orders())

# ######################################################################
# Identify Assets to Buy
# ######################################################################
# Get all assets on the exchange with a USD quote, and other assets.
# Filter on assets that are tradeable and remove stable coins that
# don't fluctuate in price, and any problematic coins based on experience.
info = oco.get_exchange_info()
df_info = pd.DataFrame(info['symbols'])
df_info = df_info[['symbol','baseAsset','quoteAsset']].loc[(df_info['status']=='TRADING')]
# Remove other assets that I don't want to be trading like BNB.
# Removed VTHO on Apr 2 2021 because the script buys it more than any other asset and overall I lose
# money on it. I think part of the problem is that it's very low priced, with low
# decimals so my orders are not precise and trigger when they wouldn't normally with more
# precision.
# Excluding REP because it just seems to always lose money and also it's a gambling token.
# (Kind of a "Do Not Buy" list).
df_info2 = df_info.loc[(~df_info['baseAsset'].isin(['BNB','USD','USDC','DAI','USDT','BUSD','VTHO','REP']))]
df_info2_usd = df_info2.loc[(df_info2['quoteAsset'] == quote_asset_to_filter_on)]

# Which of the exchange's assets do I already have a position in? Remove them from my list of possible buys.
# I only want to own 1 stake in an asset at a time, and each asset should have the same amount ($100 right now)
oco_bal = util.get_balances(oco)
oco_bal_wo_dust = oco_bal.loc[oco_bal['total_usd']>=10].sort_values(by=['total_usd'],ascending=False)
# List of quote currencies not to trade in.
# If I list a currency here but not above then it will buy multiples of it:
oco_bal_filtered = oco_bal_wo_dust.loc[~oco_bal_wo_dust['baseAsset'].isin(['BNB','USD','USDC','DAI','USDT','BUSD'])]
#oco_merged = df_info2_usd.merge(oco_bal_wo_dust, on='baseAsset',how='left')
oco_merged_pre = df_info2_usd.merge(oco_bal_filtered, on='baseAsset',how='left')

# We don't want to try to buy assets that we have open buy stop limit
# orders on (but which we don't currently hold yet) so exclude them
# from oco_no_position below
# Remove those we have open buy orders on so we don't attempt to buy
# base assets that we are already trying to buy.
if (len(all_open_orders) > 0):
    open_orders_pre = all_open_orders.loc[(
        all_open_orders['side']=='BUY')
        & (all_open_orders['status']=='NEW')
    #    & (all_open_orders['type']=='STOP_LOSS_LIMIT') # exclude this line
                                                    # because I want to filter
                                                    # any new buy orders, I would think.
    ]
    open_orders = open_orders_pre[['symbol','orderId']].groupby('symbol').count()
    symbols_with_open_buy_orders = open_orders.rename(columns={'orderId':'count_of_open_orders'})
    held_as_open_orders = open_orders.merge(df_info, on='symbol', how='inner')
    oco_merged = oco_merged_pre.loc[~oco_merged_pre['baseAsset'].isin(held_as_open_orders['baseAsset'].to_list())]
else:
    oco_merged = oco_merged_pre

# assets I do not have a position in right now:
oco_no_position = oco_merged.loc[oco_merged['total_usd'].fillna(0) == 0][['symbol']] #,'baseAsset','quoteAsset']]

# ######################################################################
# Buy the Assets
# ######################################################################
# if I don't have enough of the quote asset to buy anything then skip past the purchase part
cash_left = float(oco_bal.loc[oco_bal['baseAsset']==quote_asset_to_filter_on]['total_free_usd'])
ocos = pd.DataFrame(columns=['symbol','baseAsset','quoteAsset','pct_change'])

if(cash_left>=quote_amount_usd):
    ocos_unfiltered = strat.choose_oco(oco, candle_span=15, candle_count=8, method='pct_change', info=info) # 24hr change

# Get all of the symbols and their current prices.
# Call get_all_tickers after choose_oco() runs so that the prices
# are as current as possible. Keep it outside the if() so that it's
# available at the end of the script when I call
# adjust_existing_buy_side_stop_loss_orders()
symbol_prices = pd.DataFrame(oco.get_all_tickers())

if(cash_left>=quote_amount_usd):
    # Buy OCO orders
    ########################
    #ocos_unfiltered = strat.choose_oco(oco, candle_span=15, candle_count=8, method='pct_change', info=info) # 24hr change
    #ocos_unfiltered = strat.choose_oco(oco, candle_span=60, candle_count=24, method='pct_change', info=info) # 24hr change
    #ocos_unfiltered = strat.choose_oco(oco, candle_span=15, candle_count=8, method=None, info=info) # 6 out of 8 of the last 15-min candles are red
    util.save(ocos_unfiltered, 'data/continuous_oco_stop_loss/ocos_unfiltered.pkl')
    #ocos_unfiltered = util.load('data/continuous_oco_stop_loss/ocos_unfiltered.pkl')
    #ocos_unfiltered = util.load('data/continuous_oco_stop_loss/ocos_unfiltered_FOR_TESTING.pkl')
    ########################
    ocos_unfiltered_all = util.load('data/continuous_oco_stop_loss/oco_stop_loss_unfiltered.pkl')
    ocos_unfiltered_all = ocos_unfiltered_all.append(ocos_unfiltered)
    util.save(ocos_unfiltered_all, 'data/continuous_oco_stop_loss/oco_stop_loss_unfiltered.pkl')

    # Filter ocos list with my no_position list.
    ocos = ocos_unfiltered.merge(oco_no_position,on='symbol',how='inner')
    #print(ocos)

    # no selection:
    #oco_pct_drop = ocos
    # keep assets with >= X% drop or on an upward trend
    oco_pct_drop = ocos.loc[(ocos['pct_change'] < 0)] # only buy drops # MAR 31 16:31
    #oco_pct_drop = ocos.loc[(ocos['pct_change'] < -1000)] # only buy drops # MAR 31 16:31
    #oco_pct_drop = ocos # buy the highest % drop, even if it's actually the lowest gain (method='min' below)
    ###pct_drop_list = ocos.loc[(ocos['pct_change'] >= .04)]
    ###oco_pct_drop = ocos.loc[(ocos['pct_change'] <= -.06)]
    ###oco_pct_drop = ocos.loc[(ocos['pct_change'] <= -.04) | (ocos['pct_change'] >= .04)]
    ###oco_pct_drop = ocos.loc[(abs(ocos['pct_change']) >= .04)] # consider mixing them up like this with absolute value.
    # but maybe first experiment which one works better.

    # group by base asset to remove duplicates...
    rank_by_pct = oco_pct_drop.groupby('baseAsset')['pct_change'].rank(method='min')
    # ... keep the base/quote pair with the highest % drop (pick ETHUSDT and disregard ETHBTC, ETHBUSD, etc. for each base_asset)
    ocos_to_buy = oco_pct_drop.loc[rank_by_pct==1] # short notation works when there's 1 column with no name
    # sort the final result ascending (so that -4% comes before -1%)
    ocos_to_buy = ocos_to_buy.sort_values(by='pct_change', ascending=True)
    print ("")
    print ("ocos_to_buy: ")
    print (ocos_to_buy)
    # Save a list for a reporting script that pulls recent orders
    # for this list of assets and calculates profit.
    util.save(ocos_to_buy, 'data/continuous_oco_stop_loss/ocos_to_buy.pkl')
    ocos_list = util.load('data/continuous_oco_stop_loss/ocos_list.pkl')
    util.save(ocos_list.append(ocos_to_buy), 'data/continuous_oco_stop_loss/ocos_list.pkl')

    ############
    #info = oco.get_exchange_info()
    #df_info = pd.DataFrame(info['symbols'])
    # some, like XRP are not currently tradeable
    # df_info = df_info[['symbol','baseAsset','quoteAsset']].loc[(df_info['status']=='TRADING')]
    # df_info2 = df_info.loc[(~df_info['baseAsset'].isin(['USD','USDC','DAI','USDT','BUSD']))]
    # df_info2 = df_info2.loc[(df_info2['quoteAsset'] == 'USD')]
    # ocos_to_buy = df_info2
    # ocos = df_info2
    ############

    #not sure that my tactics are any better than random selection. Let's find out...
    # 1 every 15 minutes (crontab -e)
    #ocos_to_buy = ocos_to_buy.sample(1)


    #print("--------------------------------------------------")
    #print("Top OCO orders (may not meet criteria)")
    #print("--------------------------------------------------")
    #pprint.pprint(ocos.sort_values(by='pct_change', ascending=True))
    #print("")
    html_ocos_to_buy = str(ocos_to_buy[0:number_of_coins].to_html(classes='table table-striped'))
    #automatically trade top results
    # drop USDCUSDT, etc.
    # Only buy one at a time if I'm running this every 15 minutes - the one with the highest pct drop.
    # Give simple_trade_oco a list of ocos to buy.
    print("simple_trade_oco_buy() function call...")
    orders_placed = strat.simple_trade_oco_buy(
        oco,
        ocos_to_buy[0:number_of_coins],
        quote_amount_usd=quote_amount_usd,
        profit=profit,
        loss=loss,
        actually_trade=True,
        symbol_prices = symbol_prices
    )
else:
    print("No cash to spend. "+str(cash_left)+" "+quote_asset_to_filter_on)
    pd.DataFrame({cash_left}).to_csv("data/continuous_oco_stop_loss/oco_stop_losss_no_cash.txt")
    # Don't exit. Do the next part regardless of whether or not I have
    # enough cash to buy with.

# ######################################################################
# Adjust SELL Orders
# ######################################################################
# Go through the assets I own. Did the price go up? If so,
# then cancel all current orders and create a new OCO stop loss
# below the current price. A trailing take-profit.

# Get the symbols I have a position in right now.
oco_have_position = pd.DataFrame(oco_merged.loc[oco_merged['total_usd'].fillna(0) > 0])
# later this can be a table I store locally with each asset's start amount:
oco_have_position['start_amount_usd'] = quote_amount_usd

# Go through the assets that we currently hold a position in. We don't save
# the price from the last time the script ran. Instead, we use the last
# stop loss order to know where the price was at that time.
# 1) Look for any old stop loss orders so that we can tell if the current
#    price went up or down since last time.
# 2) If it went up, then:
#    a) figure out what the new stop loss order price should be
#    b) cancel existing orders
#    c) place the new order
# 3) If the price went down then don't change the current order.
#    HOWEVER, if the total USD amount of the asset is already in profit,
#    then set the stop loss order to just under the current price. We
#    want that profit before the price drops much lower.
print ("")
print ("oco_have_position: ")
print (oco_have_position)
for index, row in oco_have_position.iterrows():
    total_usd = row['total_usd']
    start_amount_usd = row['start_amount_usd']
    symbol = row['symbol']
    base_asset = row['baseAsset']
    asset_current_price = row['price_usd']
    # quantity for the stop loss order
    asset_quantity = row['free'] + row['locked']
    # Pull any current stop loss orders and then cancel them.
    # Check for open orders on this symbol before placing a market
    # order. Then cancel any that we find.
    orders = pd.DataFrame(oco.get_all_orders(symbol=symbol, limit=20))
    # If there are orders, then cancel them. (There should have been
    # at least one OCO). What we want out of this: the price of the
    # OCO order's stop loss. If the current price is greater than or
    # equal to 1.02 * that stop limit price then we want to create a
    # new stop limit price that's -2% of the current price.
    print("symbol: " + symbol)
    print("new asset_current_price: " + str(asset_current_price))
    print("len(orders): " + str(len(orders)))
    #print("new stop_loss_price: " + new_stop_loss_price)

    # New stop loss order price is current_price minus loss
    # E.g., $1.00 * 0.50 = 50 cents
    new_stop_loss_price = asset_current_price * (1-loss_sell_side)

    # Did this asset have orders?
    if (len(orders)>0):
        orders_new = orders.loc[orders['status']=='NEW']
        orders_new_stop_loss = orders_new.loc[orders_new['type']=='STOP_LOSS_LIMIT']
        # This asset has stop loss order(s) that we can get a price from
        print("len(orders_new_stop_loss): " + str(len(orders_new_stop_loss)))
        if(len(orders_new_stop_loss) > 0):
            # sort by highest stop price
            orders_new_stop_loss = orders_new_stop_loss.sort_values(by='price', ascending=False)
            # iloc[0] will take the first row now matter how it's sorted so
            # don't change this.
            order_to_cancel = orders_new_stop_loss.iloc[0]
            order_id_to_cancel = order_to_cancel.orderId
            highest_stop_loss_price = float(order_to_cancel.price)
            # if the current asset price minus the loss % is higher than
            # the current stop loss price then cancel existing orders
            # to make way for a new one at a higher stop loss price.
            print("asset_current_price x loss: %s, highest_stop_loss_price: %s" % (asset_current_price * (1-loss_sell_side), highest_stop_loss_price))
            if (asset_current_price * (1-loss_sell_side) > highest_stop_loss_price):
                # cancel the order (comment out temporarily while we test).
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("cancel_order(): " + base_asset)
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                #Since I cancel all of the orders further below, just don't bother
                # with this single order cancelling part.
                result = oco.cancel_order(symbol=order_to_cancel.symbol,orderId=order_id_to_cancel)

                # reinstate the order during testing. this is JUST for testing:
                # DOES NOT WORK YET because I can't specify an absolute maker and limit price. Right now it
                # recreates at the current market price. But I tested the cancel command
                # and it works fine so I may not even need this:
                # reinstate = strat.oco(oco, quote_amount=0, quantity=float(order_to_cancel.origQty),profit=profit, loss=loss, symbol=order_to_cancel.symbol, market_buy=False)

                log_cancel = log_cancel.append(pd.DataFrame([result]))
                # Remove the just-canceled order from the orders dataframe
                # otherwise cancel_all_existing_orders will generate an
                # exception. That exception is already handled, but it's
                # cleaner to keep track of orders and only cancel ones that
                # currently exist. First, make sure that the order was
                # actually canceled by finding it in the canceled orders
                # result. Index will always be zero because we're only
                # ever canceling one order in this part of the script.
                canceled_orders = pd.DataFrame(log_cancel['orders'].iloc[0])['orderId']
                #if (orders_new['orderId'].isin(canceled_orders.to_list())):
                # remove them from the orders dataframe (the stop loss
                # and the related limit maker)
                orders_new = orders_new.loc[(~orders_new['orderId'].isin(canceled_orders.to_list()))]

                print("")
                print("////////////////// new location: inside IF ///////////////")
                print(symbol + " (ins) total_usd: " + str(total_usd))
                print(symbol + " (ins) quote_amount_usd: " + str(quote_amount_usd))
                print(symbol + " (ins) quote_amount_usd * 1.02: " + str(quote_amount_usd * 1.02))
                print(symbol + " (ins) new_stop_loss_price: " + str(new_stop_loss_price))
                print(symbol + " (ins) asset_current_price: " + str(asset_current_price))
                print(symbol + " (ins) asset_current_price * .99: " + str(asset_current_price * .9975))
                # greater than $252.50 (+.002 to try to account for $0.25 fees with each trade)
                if (total_usd > quote_amount_usd * 1.012):
                    print(" (ins) inside outer if ")
                    # make the stop loss 1% below the current price
                    #new_stop_loss_price = asset_current_price * (1 + (loss_sell_side-.01))
                    if(new_stop_loss_price <= asset_current_price * .9975):
                        print(" (ins) inside inner if ")
                        new_stop_loss_price = asset_current_price * .9975
                    else:
                        print(" (ins) inside second inner else ")
                        new_stop_loss_price = asset_current_price * (1-loss_sell_side)
                else:
                    print(" (ins) inside second outer else ")
                    #new_stop_loss_price = None
                    new_stop_loss_price = asset_current_price * (1-loss_sell_side) # "Account has insufficient balance for requested action."

            # set the new price after cancelations were successful
            # I decided NOT to do this and just set it at the top since
            # otherwise I have to repeat else statements below
            # new_stop_loss_price = highest_stop_loss_price

            else:
                # the current symbol price is lower than the stop loss price * 1.02
                # !current highest stop loss price on this symbol so do nothing.
                # so reset the stop loss price to current_price * (1-(loss/2))
                # in other words, the current stop loss price is the best possible
                # price.

                #new_stop_loss_price = asset_current_price * (1-loss_sell_side/2) # 2% loss becomes 1%
                #new_stop_loss_price = asset_current_price * (1-.01) # 1% loss

                #new_stop_loss_price = highest_stop_loss_price # * (1 + .01) If it's going down,
                print("")
                print("////////////////// new location: else ///////////////")
                print(symbol + " (else) total_usd: " + str(total_usd))
                print(symbol + " (else) quote_amount_usd: " + str(quote_amount_usd))
                print(symbol + " (else) quote_amount_usd * 1.02: " + str(quote_amount_usd * 1.02))
                print(symbol + " (else) new_stop_loss_price: " + str(new_stop_loss_price))
                print(symbol + " (else) asset_current_price: " + str(asset_current_price))
                print(symbol + " (else) asset_current_price * .99: " + str(asset_current_price * .9975))
                # greater than $252.50 (+.002 to try to account for $0.25 fees with each trade)
                if (total_usd > quote_amount_usd * 1.012):
                    print(" (else) inside outer if ")
                    # make the stop loss 1% below the current price
                    #new_stop_loss_price = asset_current_price * (1 + (loss_sell_side-.01))
                    if(new_stop_loss_price <= asset_current_price * .9975):
                        print(" (else) inside inner if ")
                        new_stop_loss_price = asset_current_price * .9975
                    else:
                        print(" (else) inside second inner else ")
                        new_stop_loss_price = None
                else:
                    print(" (else) inside second outer else ")
                    new_stop_loss_price = None

                # then meet it but only if we're above $250.
                print("The current price (%s) of %s minus the loss pct (%s) equals %s which is lower than %s (the current stop loss price) by %s pct so the current sell side stop losses were not canceled or adjusted." % (asset_current_price,symbol,loss,asset_current_price * (1-loss_sell_side),highest_stop_loss_price,(asset_current_price * (1-loss_sell_side))/highest_stop_loss_price-1))

        # Cancel any orders that could be locking up funds we need for
        # the new OCO stop loss... but not if the new stop loss order
        # would be lower than the current one. In the latter case,
        # new_stop_loss_price will be set to None above. Another valid
        # criteria would be:
        # asset_current_price * (1-loss) >= highest_stop_loss_price
        if(len(orders_new) > 0):
            if(new_stop_loss_price != None):
                # cancel all unfilled ("NEW") orders
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("cancel_all_existing_orders(): " + base_asset)
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                remaining_canceled_orders = util.cancel_all_existing_orders(oco, base_asset)
                #loop through the canceled orders
                for index_c, row_c in remaining_canceled_orders.iterrows():
                    # There's no contingencyType if the remaining order
                    # was not OCO so check that first.
                    if ('contingencyType' in remaining_canceled_orders.columns.to_list()):
                        if (row_c.contingencyType=='OCO'):
                            #remaining_stop_loss = remaining_stop_loss[index]
                            print("FYI there was an unexpected additional OCO that got canceled: listClientOrderId %s" % (row_c.listClientOrderId))

                    # if there was more than 1 NEW STOP_LOSS order then print
                    # a message about it but continue.
                    # Actually, the canceled order list doesn't tell us what
                    # type of order it canceled, just that it was
                    # part of an OCO so we can't do this exactly:
                        # for index_d, row_d in pd.DataFrame(remaining_canceled_orders['orders'].iloc[0]).iterrows():
                        #     print(row_d)
                        #     if (row_d['type']=='STOP_LOSS_LIMIT'):
                                # print("FYI there was an unexpected additional stop loss that got canceled: OrderId %s for %s of %s at %s." % (row_d['orderId'], row_c['origQty'], row_c['symbol'], row_c['price']))

        else:
            # If there are no open orders then make the new
            # stop loss price = current price.
            new_stop_loss_price = asset_current_price * (1-loss_sell_side)
            if (total_usd > quote_amount_usd * 1.012):
                print(" (else 1 a) inside outer if ")
                # make the stop loss 1% below the current price
                #new_stop_loss_price = asset_current_price * (1 + (loss_sell_side-.01))
                if(new_stop_loss_price <= asset_current_price * .9975):
                    print(" (else 1 b) ")
                    new_stop_loss_price = asset_current_price * .9975

    else:
        # If there are no unfilled OR filled orders
        # then make the stop loss price = current price.
        new_stop_loss_price = asset_current_price * (1-loss_sell_side)
        if (total_usd > quote_amount_usd * 1.012):
            print(" (else 2 a) inside outer if ")
            # make the stop loss 1% below the current price
            #new_stop_loss_price = asset_current_price * (1 + (loss_sell_side-.01))
            if(new_stop_loss_price <= asset_current_price * .9975):
                print(" (else 2 b) inside inner if ")
                new_stop_loss_price = asset_current_price * .9975


# DELETE THIS LINE. PREVIOUS LOCATION

    # if $15.97 * 13.84 < $225 then make the stop loss price higher,
    # $225 / quantity = $16.257
    # if (new_stop_loss_price * quantity < quote_amount_usd * (1 - sell_side_loss):
        # new_stop_loss_price = (quote_amount_usd * (1 - sell_side_loss)) / quantity

    # Now that we know what the new stop loss order's price should be,
    # and we've canceled all existing orders, we can finally place the
    # order.
    print("")
    print("------------------------------------------")
    print("Just before entering oco() for %s..." % (symbol))
    print("------------------------------------------")
    print("new_stop_loss_price: " + str(new_stop_loss_price))
    print("highest_stop_loss_price: " + str(highest_stop_loss_price))
    print("asset_current_price: " + str(asset_current_price))
    if ((new_stop_loss_price != None)):
        strat.oco(
            oco, # exchange connection object
            symbol = symbol, # symbol to trade
            quantity = asset_quantity, # quantity (in base asset)
            # amount to purchase/sell in quote currency if no quantity
            quote_amount = 0,
            market_buy = False, # true if asset needs to be purchased first
            side = 'sell', # buy or sell
            profit = profit, # a high maker bc the stop should be our profit
            loss = loss_sell_side, # 1.0% loss for stop limit
            # set our own stop limit. the stop and maker price are
            # based on this. stop is +0.001 and maker is +(stop+loss)
            stop_limit_price_param = new_stop_loss_price,
            verbose = False, # true to print out lots of messages
            test = False # do everything except actually send the order
        )
# Really easy way out of not reviewing the log info below but then I
# don't know what the oco_stop_loss section did.
#if(cash_left>=quote_amount_usd):
# exit()

# This iterates through all of the exchange assets to find out if
# I have a buy order on it already or not and if I do to adjust it
# down from the current price if the price is lower.
util.adjust_existing_buy_side_stop_loss_orders(oco, symbol_prices, all_open_orders)

# Go line by line through the "Review OCO Orders Placed" section to see what I need to change in the log if I skip all the order stuff for not having enough cash.
# ################################

# print("--------------------------------------------------")
# print("Review OCO Orders Placed")
# print("--------------------------------------------------")
# pprint.pprint(pd.DataFrame(orders_placed))
# print("")
# saved_orders = pd.DataFrame(util.load('data/continuous_oco_stop_loss/oco_stop_loss_orders_placed.pkl'))
# saved_orders.append(pd.DataFrame(orders_placed))
# util.save(saved_orders, 'data/continuous_oco_stop_loss/oco_stop_loss_orders_placed.pkl')
# html_saved_orders = str(saved_orders.to_html(classes='table table-striped'))

# summary table
# oco_summary = pd.DataFrame(columns=['time', 'symbol', 'quantity', 'make_market_buy','profit_pct','loss_pct','buy_quantity','current_price','limit_maker_price','stop_price','stop_limit_price'])
# oco_summary = oco_summary.append(pd.DataFrame(orders_placed))
# oco_summary['quote_cost'] = pd.to_numeric(oco_summary['buy_quantity'])*oco_summary['current_price']
# oco_summary = oco_summary.merge(ocos, on='symbol')

# write html to file
# html_header = "<html><body>"
# html_footer = "</body></html>"
# html_text = "<p><b>OCO Summary</b></p><p>Here is the OCO summary for "+dt_string+"</p><br><br>"
# html_table = html_saved_orders
# text_file = open("data/continuous_oco_stop_loss/index_oco_stop_loss.html", "w")
# text_file.write(html_header+html_text+html_ocos_to_buy+"<br><br>"+html_table+html_footer)
# text_file.close()
