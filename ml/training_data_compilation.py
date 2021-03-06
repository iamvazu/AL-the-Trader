#LIBRARIES
import pandas as pd
import numpy as np
import yfinance as yf
import os

from objects.algofuncs import WATCHLIST
import ml.rolling_agg_funcs as ra
import ml.indicators as ind

import imp
imp.reload(ra)
imp.reload(ind)

#DECLARATIONS/PARAMS
period = '5y' # for individual stock history
periods = [5, 10, 21, 65] # for rolling aggregate calcs
cols = ['Open','High','Low','Close', 'Volume', 'rsi', 'macd_hist', 
        'bb_upper_band', 'bb_upper_diff', 'bb_lower_band', 'bb_lower_diff']
drop_cols = ['Dividends', 'Stock Splits']
features_to_keep = pd.read_csv('ml/regression/lm_inputs/features.csv', header = None)
funcs = [ra.rolling_mean, ra.rolling_max, ra.rolling_min, ra.rolling_stdev, ra.z_score]
benchmark_ticker = 'VTSMX' # The Vanguard Total Stock Market Index 

'''
BENCHMARK INDEX
- Set benchmark using ticker benchmark_ticker from above: gather history
- Calculate applicable indicators 
- Add rolling cols (means, mins, maxes, z_scores)
- change column names to denote vs. stock column names
'''
##Indicators
benchmark_history = yf.Ticker(benchmark_ticker).history(period = period)
benchmark_history['rsi'] = benchmark_history['Close'].rolling(15).apply(ind.calc_rsi) 
benchmark_history['macd_hist'] = ind.calc_macd(benchmark_history['Close']) 
benchmark_history['bb_upper_band'], benchmark_history['bb_upper_diff'], benchmark_history['bb_lower_band'], benchmark_history['bb_lower_diff'] = ind.calc_bb(benchmark_history['Close'])
##Rolling Aggregates 
benchmark_history = ra.add_rolling_cols(benchmark_history, cols, periods, funcs).drop(drop_cols, axis = 1)
benchmark_history['next_close'] = benchmark_history['Close'].shift(-1)
##Denote market benchmark column names
benchmark_history.columns = [f'market_{col}' for col in benchmark_history.columns]

'''
MAIN LOOP
- for each stock in watchlist, initialize asset 
- then add indicators and rolling col aggregates
- JOIN: Benchmark history info based on Date
- Calculate growth % deltas for all figures; column concatenate with original figures in 'cols' list
- Drop all null columns and any null rows, rearrange columns 
'''
n = 0
for ticker in WATCHLIST.index: 
    file_path = f'ml/regression/lm_objects/training/feature_data/{ticker}.csv'    
    # if f'{ticker}.csv' in os.listdir('ml/stock_data/stock_features'):
    #     print(f"Pass on {ticker}")
    #     continue

    # Initialize asset history
    asset = yf.Ticker(ticker)
    asset_figs = asset.history(period = period)

    # Add Rolling columns + indicators
    asset_figs['rsi'] = asset_figs['Close'].rolling(15).apply(ind.calc_rsi) #RSI
    asset_figs['macd_hist'] = ind.calc_macd(asset_figs['Close']) #MACD
    asset_figs['bb_upper_band'], asset_figs['bb_upper_diff'], asset_figs['bb_lower_band'], asset_figs['bb_lower_diff'] = ind.calc_bb(asset_figs['Close'])# BBs

    asset_figs = ra.add_rolling_cols(asset_figs, cols, periods, funcs).drop(drop_cols, axis = 1)

    # JOIN: Benchmark info
    asset_figs = pd.merge(asset_figs, benchmark_history, on = 'Date')

    # Calculate growth rates, concat with original figs and ticker info
    deltas = asset_figs.diff()/asset_figs.shift(1)
    deltas.columns = [f'{col}_delta' for col in deltas.columns]
    asset_figs = pd.concat([asset_figs[cols],
                            asset_figs.iloc[:, ['z_score' in col for col in asset_figs.columns]],
                            deltas], 
                            axis = 1)
    try: 
        asset_figs['sector'] = asset.info['sector']
    except: 
        asset_figs['sector'] = 'No Sector'

    asset_figs['next_close'] = asset_figs['Close'].shift(-1)
    asset_figs['next_close_2'] = asset_figs['Close'].shift(-2)
    asset_figs['next_close_3'] = asset_figs['Close'].shift(-3)
    asset_figs['next_close_5'] = asset_figs['Close'].shift(-5)
    asset_figs['next_close_10'] = asset_figs['Close'].shift(-10)
    asset_figs['Ticker'] = ticker
    
    # Drop all-Nan columns, save only needed columns while removing any hindsight 'next' cols
    asset_figs.dropna(how = 'all', axis = 1, inplace = True)
    asset_figs.dropna(how = 'any', axis = 0, inplace = True)

    asset_figs.loc[:,['Ticker', 'next_close', 'next_close_2', 'next_close_3', 'next_close_5', 'next_close_10']].to_csv(f'ml/regression/lm_objects/training/labels/{ticker}.csv')
    asset_figs = asset_figs.loc[:, features_to_keep[0]]
    asset_figs.drop('Date', axis = 1, inplace = True)
    asset_figs.reset_index(inplace = True)

    # Reorder columns
    first_cols = ['Date','sector']; rem_cols = [col for col in asset_figs.columns if col not in first_cols]
    asset_figs = asset_figs[first_cols+rem_cols]

    print(ticker); print(asset_figs.shape)
    asset_figs.to_csv(file_path)