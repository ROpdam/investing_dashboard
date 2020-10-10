import pandas as pd
import datetime
import os
from yahoo_scraping import YahooFinanceHistory
from forex_python.converter import CurrencyRates

def scrape_prices(tickers, days_back):
    print('scraping...')
    all_prices = pd.DataFrame()
    for tick in tickers:
        month_prices = YahooFinanceHistory(tick, days_back=days_back).get_quote().set_index('Date')['Close'].to_frame().rename({'Close':tick}, axis=1)
        all_prices = month_prices.join(all_prices).interpolate()
    return all_prices.reset_index()

def get_history(tickers, days_back=120, store=True):
    global _prices
    # Check if history file exists, not => scrape 120 days back and interpolate
    file_name = 'history/PF_history.xlsx'
    if not os.path.exists(file_name):
        scraped_df = scrape_prices(tickers, days_back)
        scraped_df.iloc[:-1].to_excel(file_name, index=False)
    
    # Read history, add days not covered till today, interpolate (excluding today)
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    historic_p = pd.read_excel(file_name)
    delta = yesterday - historic_p.iloc[-1].Date

    new_p = scrape_prices(tickers, delta.days + 1).iloc[:-1].copy()
    _prices = pd.concat([historic_p, new_p]).to_excel(file_name, index=False)

    # return all_prices

# print(get_prices(['NVDA', 'AAPL'], 30))
pf = pd.read_excel('investing_source.xlsx')
his = pd.read_excel('history/PF_history.xlsx')
# pf['profit_perc'] = his.set_index('Date').iloc[-1][::-1].to_numpy() / pf.cost_per_stock.to_numpy()
# y = (pf['number_of_stocks'].to_numpy()[::-1] * his.set_index('Date')).sum(axis=1)

# global _c
# _c = CurrencyRates()
# print(his.head())
# for curr, tick in zip(pf[pf.currency != 'EUR']['currency'], pf[pf.currency != 'EUR']['ticker']):
#     his[tick] = his.apply(lambda x: _c.convert(curr, 'EUR', x[tick], x.Date), axis=1)

his['total'] = his.sum(axis=1)
print(his.head())
# print(his)
# get_history(pf.ticker)
# pf['profit_perc']=prices.mean().iloc[::-1]/pf.cost_per_stock - 1
# # print(prices.interpolate())
# print(prices.mean().iloc[::-1]/pf.cost_per_stock.to_numpy())
# print(prices)