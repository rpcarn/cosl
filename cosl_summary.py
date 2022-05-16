import lib.util as util
import lib.strategy as strat
import pprint
import pandas as pd
from importlib import reload
from datetime import date, datetime, timedelta
from IPython.display import HTML
import random

def add_group_val_to_orders(osg):
    prev_symbol = ""
    prev_side = ""
    prev_group_num = 1
    osg['group_val'] = ""
    osg = osg.reset_index()
    for index, row in osg.iterrows():
        symbol = row['symbol']
        side = row['side']
        # Symbol is different.
        if (symbol != prev_symbol):
            prev_group_num = 1
            if (side == 'BUY'):
                osg.loc[index,'group_val'] = symbol+str(1)
        # Symbol is the same.
        else:
            # The sell of a previous buy.
            if (side == 'SELL' and prev_side == 'BUY'):
                osg.loc[index,'group_val'] = symbol+str(prev_group_num)
            # A single order was split into multiple orders.
            if (side == 'BUY' and prev_side == 'BUY'):
                osg.loc[index,'group_val'] = symbol+str(prev_group_num)
            if (side == 'SELL' and prev_side == 'SELL'):
                osg.loc[index,'group_val'] = symbol+str(prev_group_num)
            # New buy for this symbol.
            elif (side == 'BUY' and prev_side == 'SELL'):
                osg.loc[index,'group_val'] = symbol+str(prev_group_num + 1)
                prev_group_num = prev_group_num + 1
        prev_symbol = symbol
        prev_side = side
    return osg


# current date and time
now = datetime.now()
dt_string = now.strftime("%a, %b %d, %Y %H:%M:%S")
dt_string_filename = now.strftime("%Y-%m-%d_%H%M.%S")
yesterday = pd.to_datetime(date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

# The buy/sell script saves which assets it buys so
# use that list here.
ocos_list = util.load('data/continuous_oco_stop_loss/ocos_list.pkl')
gb = ocos_list.groupby(['symbol','baseAsset','quoteAsset'])
sym_gb = gb.count().sort_values(by='symbol')
sym_no_index = sym_gb.reset_index()
sym = sym_no_index.loc[~sym_no_index['baseAsset'].isin(['ETH','BTC','VTHO','REP'])]
symbols = sym
#symbols = sym.head(10)

# symbols = ocos_list = util.load('data/continuous_oco_stop_loss/ocos_list.pkl')
orders = pd.DataFrame()

oco = util.startup_binance_from_username('binance-us')

# Iterate over the list.
for index, row in symbols.iterrows():
    print("====== Asset loop ======")

    symbol = row['symbol']
    base_asset = row['baseAsset']
    quote_asset = row['quoteAsset']

    # Get the asset's filled orders from yesterday
    # and append them to the orders table.
    orders_asset = pd.DataFrame(oco.get_all_orders(symbol=symbol, limit=500))

    print("Symbol: %s (%s)" % (symbol, len(orders_asset)))

    if (len(orders_asset)>0):
# Convert unix time to datetime.
        orders_asset['create_time'] = pd.to_datetime(round(orders_asset['time']/1000), unit='s')
        orders_asset['fill_time'] = pd.to_datetime(round(orders_asset['updateTime']/1000), unit='s')
        orders_asset['time_elapsed'] = orders_asset['fill_time'] - orders_asset['create_time']
        orders_asset['fill_complete'] = orders_asset['origQty'] == orders_asset['executedQty']
        orders_asset['quoteQty'] = pd.to_numeric(orders_asset['cummulativeQuoteQty'])
        orders_asset = orders_asset.loc[orders_asset['status'] == 'FILLED']
        orders_asset = orders_asset.loc[orders_asset['fill_time'].dt.date == pd.to_datetime(date.today() - timedelta(days=1))]
        orders_asset['base_asset'] = base_asset
        orders_asset['quote_asset'] = quote_asset
        orders = orders.append(orders_asset)

# !!!!!!!!!!
orders_yesterday = orders
# !!!!!!!!!!

util.save(orders_yesterday, 'data/continuous_oco_stop_loss/orders_'+yesterday+'.pkl')
util.save(orders_yesterday, 'data/continuous_oco_stop_loss/orders_yesterday.pkl')
orders_all = util.load('data/continuous_oco_stop_loss/orders_all.pkl')
#orders_all = pd.DataFrame()
orders_all = orders_all.append(orders_yesterday)
util.save(orders_all, 'data/continuous_oco_stop_loss/orders_all.pkl')
util.save(orders_all, 'data/continuous_oco_stop_loss/orders_all_backup_'+yesterday+'.pkl')

# !!!!!!!!!!
orders = orders_all
# !!!!!!!!!!

orders_slice = orders[[
    'base_asset'
    ,'symbol'
    ,'quote_asset'
    ,'side'
    ,'create_time'
    ,'fill_time'
    ,'executedQty'
    ,'fill_complete'
    ,'price'
    ,'quoteQty'
    ,'type'
#    ,'create_time'
#    ,'time_elapsed'
    ,'orderId'
    ]]

# Sort by symbol, create_time
# (orders can fill out of order, but the create time
# always orders them logically, even if it's not
# representative of when the money came in (for a sell).
# The binance orders page uses create time and not fill time.
# I ran into problems with linking sells to specific orders
# when I used fill time so I changed it to create time.
# In Cosl, the orders generally happen soon after each
# other so the fills usually occur the same day.
orders_sort = orders_slice.sort_values(by=['symbol','create_time'])

# Connect each sell with its preceding buy
# Exclude orphan buy or sell orders.
orders_grp = add_group_val_to_orders(orders_sort)
# Combine split orders into a single order
# (Sometimes a buy or sell order gets split by Binance)
orders_grp[['side','symbol','quoteQty','group_val','create_time']]
orders_grp = orders_grp.groupby(['group_val','symbol','side']).agg({'quoteQty':'sum','create_time':'min'}).reset_index()

buy_side = orders_grp.loc[orders_grp['side']=='BUY'][['symbol','quoteQty','group_val','create_time']]
buy_side = buy_side.rename(columns={'quoteQty':'buy', 'create_time':'buy_time'})
sell_side = orders_grp.loc[orders_grp['side']=='SELL'][['quoteQty','group_val','create_time']]
sell_side = sell_side.rename(columns={'quoteQty':'sell', 'create_time':'sell_time'})
cosl_orders = buy_side.merge(sell_side, on=['group_val'], how='inner')
# Remove orders with unmatched buys/sells
cosl_orders = cosl_orders[cosl_orders['group_val']!=""]

cosl_orders['proceeds'] = (cosl_orders['sell']-cosl_orders['buy']).round(2)
cosl_orders = cosl_orders[['group_val','symbol','buy','sell','proceeds','buy_time','sell_time']].sort_values(by='group_val')

cosl_orders = cosl_orders.sort_values(by='sell_time', ascending=False)

print(cosl_orders[['group_val','symbol','buy','sell','proceeds','buy_time','sell_time']].head(50))

cosl_orders['fees'] = (cosl_orders['buy']+cosl_orders['sell'])*.001
cosl_orders['profit'] = (cosl_orders['proceeds'] - cosl_orders['fees']).round(2)
cosl_orders['sell_date'] = cosl_orders['sell_time'].dt.date

cosl_orders_yesterday = cosl_orders.loc[cosl_orders['sell_date']==pd.to_datetime(date.today())-timedelta(days=1)]
proceeds_yesterday = round(cosl_orders_yesterday['proceeds'].sum(),2)
print("proceeds yesterday: "+str(proceeds_yesterday))
util.save(proceeds_yesterday, 'data/continuous_oco_stop_loss/cosl_orders_proceeds.pkl')
util.save(proceeds_yesterday, 'data/continuous_oco_stop_loss/cosl_orders_proceeds_'+yesterday+'.pkl')

util.save(cosl_orders, 'data/continuous_oco_stop_loss/cosl_orders.pkl')
util.save(cosl_orders, 'data/continuous_oco_stop_loss/cosl_orders_'+yesterday+'.pkl')
cosl_orders.to_csv('data/continuous_oco_stop_loss/cosl_orders.csv')

cosl_orders_html = cosl_orders[['sell_date','proceeds','profit']].groupby('sell_date').sum().sort_values(by='sell_date', ascending=False)
profit_yesterday = round(cosl_orders_yesterday['profit'].sum(),2)
print("profit yesterday: "+str(profit_yesterday))
util.save(cosl_orders_html, 'data/continuous_oco_stop_loss/cosl_orders_html.pkl')
#cosl_orders_html.to_csv('data/continuous_oco_stop_loss/cosl_orders_html.csv')

# Add yesterday's balance to the table and save it.
#cosl_orders_html = util.load('data/continuous_oco_stop_loss/cosl_orders_html.pkl')
#balances = util.load('data/binance_balances_data/binance_balances_'+yesterday+'.pkl')
balances = util.load('data/binance_balances_data/binance_balances.pkl')
balance = 0 #round(balances[balances['api_key'] == 'AwdvQ']['total_usd'].sum())
balances['sell_date'] = balances['date_time'].dt.date
balances_total = balances[balances['api_key'] == 'AwdvQ'][['sell_date','total_usd']].groupby(['sell_date']).sum()
cosl_orders_html = cosl_orders_html.merge(balances_total, on='sell_date', how='left')
#cosl_orders_html.loc[cosl_orders_html.index==pd.to_datetime(yesterday).date(),'balance'] = balance
#util.save(cosl_orders_html, 'data/continuous_oco_stop_loss/cosl_orders_html_with_balance.pkl')

# Yesterday only.
#yesterdays_orders = cosl_orders.loc[cosl_orders['sell_time'] >= pd.to_datetime(date.today())-timedelta(days=1)]
# All time.
yesterdays_orders = cosl_orders
yesterdays_orders['base_asset'] = yesterdays_orders['symbol'].str.replace("USD","") # remove "USD"
yesterdays_orders = yesterdays_orders[['sell_date','buy_time','sell_time','base_asset','buy','sell','proceeds','profit']]

html_daily_summary = str(cosl_orders_html.to_html(classes='table table-striped'))
html_yesterdays_orders = str(yesterdays_orders.to_html(classes='table table-striped'))

# write html to file
html_header = "<html><body>"
html_footer = "</body></html>"
html_text = "<p><b>OCO Summary</b></p><p>Here is the OCO summary and orders for "+yesterday+"</p>"
html_balance = "<p>Balance: %s </p>" % ("NA") #(balance)
# https://www.geeksforgeeks.org/rendering-data-frame-to-html-template-in-table-view-using-django-framework/
# from IPython.display import IFrame
# IFrame(src='./nice.html', width=700, height=600)

text_file = open("data/continuous_oco_stop_loss/index_cosl_summary.html", "w")
#text_file.write(html_header+html_text+html_daily_summary+"<br><br>"+html_yesterdays_orders+html_footer)
text_file.write((html_text+html_balance+html_daily_summary+"<br><br>"+html_yesterdays_orders))
text_file.close()
