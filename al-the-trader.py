# NOTES
"""
"AL" currently trades on a simple Relative Strength Index (RSI) trigger (30 buy, 70 sell)
with a simple moving average (SMA) and shortened lookback period of 10 days. 

Current watchlist contains the 30 stocks in the DJIA, as of May 1, 2020. 

TO-DO: 
- Backdating
- Portfolio summary adjustments (running overall return, 
    current portfolio return, 
    performance metrics, 
    trade profits, 
    # days held)
"""

# LIBRARIES 
from datetime import datetime
from objects import assetfuncs as af
from objects import algofuncs as alg
from objects import updatefuncs as uf
from objects.algofuncs import EMAIL_ADDRESS, EMAIL_PASSWORD 
from objects.algofuncs import PORTFOLIO, PORTFOLIO_HIST, WATCHLIST, STOCKS, TRADES, CASH_ON_HAND
from objects.updatefuncs import GS_WORKBOOK

# DECLARATIONS
testing = False
manual = False # for manually selling/buying shares through bugs
current_date = datetime.now()

# MAIN
if manual: 
    ### TEMPORARY for manual sell trades - current bug: not selling @ rsi > 70.
    tickers = ['WMT'] # SET MANUAL TICKERS

    for ticker in tickers: 
        asset = alg.initialize_asset(ticker, STOCKS)

        order = 'sell'
        num_shares = asset.shares

        # Update WATCHLIST df: price, trend (% change), indicator values
        WATCHLIST = alg.update_port_ticker_values(WATCHLIST, ticker, asset)

        # Trade 
        trade = alg.execute_trade(asset, order, num_shares, STOCKS, PORTFOLIO, TRADES)
        TRADES = TRADES.append(trade, ignore_index = True)
        PORTFOLIO.loc['CASH'].value -= asset.cash_change

        # Update STOCKS df to remove unowned tickers, or update with new values
        if asset.shares == 0: 
            STOCKS.drop(asset.ticker, inplace = True)
        elif asset.shares > 0: 
            STOCKS.loc[asset.ticker] = asset.compiled
else: 
    for ticker in WATCHLIST.index:
        # Initialize asset
        asset = alg.initialize_asset(ticker, STOCKS)

        # Check triggers & determine action
        order = alg.check_indicators(asset, ['rsi']) #buy, sell, or neutral
        num_shares = alg.buyable_shares(asset.price, CASH_ON_HAND)  # TEMPORARY: num shares to buy

        # Update WATCHLIST df: price, trend (% change), indicator values
        WATCHLIST = alg.update_port_ticker_values(WATCHLIST, ticker, asset)

        if order != 'neutral': 
            # Check if portfolio contains enough cash/shares to buy/sell, and last activity
            tradable = alg.check_tradable(asset, order, num_shares, STOCKS, PORTFOLIO)
            if tradable:
                num_shares = asset.shares if order == 'sell' else num_shares # sell all shares, buy only buyable 
                trade = alg.execute_trade(asset, order, num_shares, STOCKS, PORTFOLIO, TRADES)
                TRADES = TRADES.append(trade, ignore_index = True)
                PORTFOLIO.loc['CASH'].value -= asset.cash_change
                # Update STOCKS df to remove unowned tickers, or update with new values
                if asset.shares == 0: 
                    STOCKS.drop(asset.ticker, inplace = True)
            else:
                print(f"{asset.ticker}: Hold at {asset.price}\n")
        else:
            print(f"{asset.ticker}: Hold at {asset.price}\n")

        if asset.shares > 0: 
            STOCKS.loc[asset.ticker] = asset.compiled

# Update dfs
PORTFOLIO.loc['STOCKS'].value = STOCKS.value.sum()
PORTFOLIO.loc['TOTAL'] = sum([PORTFOLIO.loc['CASH'].value,
                            PORTFOLIO.loc['STOCKS'].value])
PORTFOLIO_HIST = PORTFOLIO_HIST.loc[PORTFOLIO_HIST.index.str[0:10] != current_date.strftime("%d/%m/%Y")]
PORTFOLIO_HIST.loc[current_date.strftime("%d/%m/%Y %H:%M:%S")] = PORTFOLIO.transpose().values[0]

WATCHLIST.sort_values(by = 'rsi', inplace = True)

if not testing: 
    #UPDATE: EXCEL
    alg.update_workbook(WATCHLIST, STOCKS, PORTFOLIO, TRADES, PORTFOLIO_HIST)
    #UPDATE: GOOGLE SHEETS
    sheet_names_list = ['watchlist','stocks','portfolio','trades','summary']
    df_list = [WATCHLIST, STOCKS, PORTFOLIO, TRADES, PORTFOLIO_HIST]
    try:
        for name, df in zip(sheet_names_list, df_list): 
            uf.update_gs_workbook(GS_WORKBOOK, name, df) 
    except Exception as error: 
        print(f'FAILED TO UPDATE GOOGLE SHEET: {str(error)}')

    # SUMMARY EMAIL
    if current_date.hour >= 16:
        trades_executed = alg.todays_trades(TRADES)
        alg.send_email(trades_executed, STOCKS, PORTFOLIO)
