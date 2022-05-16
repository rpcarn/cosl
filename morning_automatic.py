import lib.util as util
import lib.strategy as strat
import pprint
import pandas as pd
from importlib import reload

# ############################
# Daily
# ############################
# Connect to Binance.us
# b = util.startup_binance('com')
# bus = util.startup_binance('us')
# bcom = util.startup_binance('com')
oco = util.startup_binance_from_username('binance-us')
highlow = util.startup_binance_from_username('binance')
b2 = util.startup_binance_from_username('binance2')
gridbifi = util.startup_binance_from_username('binance3')

# Don't truncate rows when printing
# pd.set_option('display.max_rows', 1000)
# pd.set_option('display.max_columns', 100)

# for interactive python session:
#reload(util)
#reload(strat)

# High / Low analysis
high_low = strat.high_low(highlow)

# Get binance balances
final_bal = util.get_binance_balances((oco,highlow,gridbifi,b2))
