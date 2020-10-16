import pandas as pd
import datetime
import os
from yahoo_scraping import YahooFinanceHistory
from forex_python.converter import CurrencyRates
import investpy

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


pf = pd.read_excel('investing_source.xlsx')
# his = pd.read_excel('history/PF_history.xlsx')

# his['total'] = his.sum(axis=1)
# print(his.head())

# df = investpy.get_stock_historical_data(stock='AAPL', country='United States', from_date='16/09/2020', to_date='15/10/2020')
# df = investpy.get_etf_historical_data(etf='"Vanguard FTSE All-World UCITS"', country='Netherlands', from_date='16/09/2020', to_date='15/10/2020')
# search_results = investpy.search_quotes(text='vwrl',
#                                         products=['etfs'],
#                                         countries=['netherlands'],
#                                         n_results=10)
# search_results = investpy.search_quotes(text='bfit',
#                                         products=['stocks'],
#                                         countries=['netherlands'],
#                                         n_results=10)
# search_results = investpy.search_quotes(text='NVDA',
#                                         products=['stocks'],
#                                         countries=['United States'],
#                                         n_results=10)

def get_hist_prices(pf):
    print('Retrieving prices')
    from_date = pf['date'].min().strftime('%d/%m/%Y')
    to_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date().strftime('%d/%m/%Y')
    all_prices = pd.DataFrame()
    for i, row in pf.iterrows():
        search_results = investpy.search_quotes(text=row['ticker'], products=[row['product']], countries=[row['country']])
        for sr in search_results[:1]:
            hist_p = sr.retrieve_historical_data(from_date=from_date, to_date=to_date)['Close'].to_frame().rename({'Close':row['ticker']}, axis=1)
            all_prices = hist_p.join(all_prices)

    return all_prices

# print(get_hist_prices(pf))
print(datetime.datetime.strptime('2020-06-18T18:29:22.600518'.split('T')[0], '%Y-%m-%d').date())
# print((datetime.datetime.now() - datetime.timedelta(days=1)).date().strftime('%d/%m/%Y'))
# print(pf['date'].min().strftime('%d/%m/%Y'))
# for sr in search_results[:1]:
#     print(sr.retrieve_historical_data(from_date='16/09/2020', to_date='15/10/2020'))

# # div = investpy.get_stock_dividends(stock='BFIT', country='Netherlands',)
# etf = investpy.get_etf_information('VWRL', 'Netherlands')
# print(div)


# def scrape_prices(tickers, days_back):
#     print('scraping...')
#     all_prices = pd.DataFrame()
#     for tick in tickers:
#         month_prices = YahooFinanceHistory(tick, days_back=days_back).get_quote().set_index('Date')['Close'].to_frame().rename({'Close':tick}, axis=1)
#         all_prices = month_prices.join(all_prices).interpolate()
#     return all_prices.reset_index()