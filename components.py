import pandas as pd
import datetime
import os
from forex_python.converter import CurrencyRates
from yahoo_scraping import YahooFinanceHistory
import plotly.express as px
import dash_html_components as html
import dash_core_components as dcc
import investpy

global _prices, _c
_prices = pd.DataFrame()
_c = CurrencyRates()

def total_cost_eur(x):
    if x['currency'] != 'EUR':
        x['total_cost_eur'] = x['number_of_stocks'] * x['cost_per_stock_eur']
    else: 
        x['total_cost_eur'] = x['number_of_stocks'] * x['cost_per_stock_eur']
    return x


def to_eur(prices, pf):
    print('Converting to EUR...')
    global _c
    to_exchange = pf[pf.currency != 'EUR']
    prices = prices.reset_index()
    for curr, tick in zip(to_exchange['currency'], to_exchange['ticker']):
        prices[tick] = prices.apply(lambda x: _c.convert(curr, 'EUR', x[tick], x.Date), axis=1)
    return prices
    # prices.iloc[:, pd.eval([to_eur_ticks])].apply(lambda x: c.get_rates(base_cur='USD', dest_cur='EUR'))


def shrink_pf(pf):
    pf = pf.sort_values('date')
    originals = pf[~pf.ticker.duplicated()].set_index('ticker')
    cols_to_add = ['number_of_stocks', 'total_cost_eur', 'transaction_costs']

    for i, row in pf[pf.ticker.duplicated()].iterrows():
        tick = row['ticker']
        originals.loc[tick, cols_to_add] = originals.loc[tick, cols_to_add] + row[cols_to_add]
    
    return originals.reset_index()


def get_hist_prices(pf, days_back=0):
    print('Retrieving prices')

    if days_back == 0:
        from_date = pf['date'].min().strftime('%d/%m/%Y')
    elif days_back > len(_prices):
        from_date = (datetime.datetime.now() - datetime.timedelta(days=days_back)).strftime('%d/%m/%Y')
    else: 
        from_date = _prices.iloc[-1].Date.strftime('%d/%m/%Y')

    to_date = (datetime.datetime.now() - datetime.timedelta(days=1)).date().strftime('%d/%m/%Y')

    
    all_prices = pd.DataFrame()
    for i, row in pf.iterrows():
        search_results = investpy.search_quotes(text=row['ticker'], products=[row['product']], countries=[row['country']])
        for sr in search_results[:1]:
            hist_p = sr.retrieve_historical_data(from_date=from_date, to_date=to_date)['Close'].to_frame().rename({'Close':row['ticker']}, axis=1).interpolate()
            all_prices = hist_p.join(all_prices)

    return all_prices


def exclude_weekends():
    today = datetime.datetime.now()
    if today.weekday() == 6:
        return today - datetime.timedelta(days=2)
    return today - datetime.timedelta(days=1)


def update_history(pf, days_back=0, store=True):
    global _prices

    # Check if history file exists, not => scrape back till first purchase
    file_name = 'history/PF_history.xlsx'
    if not os.path.exists(file_name):
        print('Scraping 120 days back history of ticker prices')
        scraped_df = get_hist_prices(pf)
        scraped_df = to_eur(scraped_df, pf)
        # print(scraped_df)
        scraped_df.to_excel(file_name, index=False)   

    # Read history, add days not covered till today
    yesterday = exclude_weekends() # Or Friday if today == Sunday
    historic_p = pd.read_excel(file_name)
    delta = yesterday - historic_p.iloc[-1].Date
    if delta.days == 0:
        _prices = historic_p
    else:
        print('Adding new days to existing history')
        new_p = get_hist_prices(pf, days_back=delta.days).copy()
        new_p = to_eur(new_p, pf)
        _prices = pd.concat([historic_p, new_p]).reset_index()
        _prices.to_excel(file_name, index=False)


def get_start_date(time_period):
    # Always adding 2 days for if today is a weekend
    if time_period[1] == 'y':
        print((datetime.datetime.now() - pd.DateOffset(months=1).date()) # get date from here
        return datetime.datetime.now() - pd.DateOffset(years=1) # years possible?
    else:
        return datetime.datetime.now() - pd.DateOffset(months=1)

######################################## FIGURES ############################################
def budget_pie(pf, b, layout):
    # Init
    pf = pf.append({'color':'white', 'ticker':'Transaction', 'total_cost_eur':pf['transaction_costs'].sum()}, ignore_index=True)
    # Create fig
    fig = px.pie(data_frame=pf, values='total_cost_eur', names='ticker', color='ticker', color_discrete_map=dict(zip(pf['ticker'], pf['color'])), title='Portfolio Split', opacity=0.9, hole=0.3)
    # Update layout
    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return dcc.Graph(id="budget-pie", figure=fig)


def profit_perc_bar(pf, layout):
    update_history(pf)
    pf['profit_perc'] = _prices.set_index('Date').iloc[-1][::-1].to_numpy()/pf.cost_per_stock_eur.to_numpy() - 1
    fig = px.bar(data_frame=pf, x='ticker', y='profit_perc', labels={'ticker':'', 'profit_perc':''}, color='ticker', color_discrete_map=dict(zip(pf['ticker'], pf['color'])), title=f'Profit Percentage', opacity=0.9)

    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return dcc.Graph(id="profit-bar", figure=fig)


def change_over_time_line(pf, pf_no_dupl, layout, stocks_or_pf, time_period):
    global _prices
    start_date = get_start_date(time_period)
    print('start_date: ', start_date)
    print(datetime.datetime.strptime(start_date.split('T')[0], '%Y-%m-%d').date(), datetime.datetime.strptime(end_date.split('T')[0], '%Y-%m-%d').date())
    
    his_subset = update_history(pf, start_date, end_date)
    # print(perc_change)
    perc_change = his_subset.set_index('Date').pct_change().reset_index()
    # print(days_back, len(_prices))
    if stocks_or_pf == 'Individual Stocks':
        y = list(pf['ticker'])
        colors = list(pf['color'])
        title = 'Portfolio Over Time (Individual Stocks)'
        labels = {'y':'Percentage Daily Change'}

    elif stocks_or_pf == 'Portfolio':
        y = 'Total Portfolio'
        his_subset[y] = (pf['number_of_stocks'].to_numpy() * his_subset).sum(axis=1)
        his_subset['Profit'] = his_subset[y] - pf.total_cost_eur.sum()
        title = 'Portfolio Over Time'
        labels = {y:'Value in Euros'}

        if his_subset[y].iloc[-1] > pf.total_cost_eur.sum():
            colors = ['green']
        else:
            colors = ['red']

    # print(his_subset)
    fig = px.line(data_frame=perc_change, x='Date', y=[y], labels=labels, color_discrete_sequence=colors, title=title, hover_data=['Profit'])
    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return fig