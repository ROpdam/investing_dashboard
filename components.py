import pandas as pd
import datetime
import os
from forex_python.converter import CurrencyRates
from yahoo_scraping import YahooFinanceHistory
import plotly.express as px
import dash_html_components as html
import dash_core_components as dcc

global _prices, _c
_prices = pd.DataFrame()
_c = CurrencyRates()

def total_cost_eur(x):
    if x['currency'] is not 'EUR':
        x['total_cost_eur'] = x['number_of_stocks'] * x['cost_per_stock_eur']
    else: 
        x['total_cost_eur'] = x['number_of_stocks'] * x['cost_per_stock_eur']
    return x

def to_eur(prices, pf):
    print('Converting to EUR...')
    global _c
    to_exchange = pf[pf.currency != 'EUR']
    for curr, tick in zip(to_exchange['currency'], to_exchange['ticker']):
        prices[tick] = prices.apply(lambda x: _c.convert(curr, 'EUR', x[tick], x.Date), axis=1)
    print(prices.columns)
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


def scrape_prices(tickers, days_back):
    print('scraping...')
    all_prices = pd.DataFrame()
    for tick in tickers:
        month_prices = YahooFinanceHistory(tick, days_back=days_back).get_quote().set_index('Date')['Close'].to_frame().rename({'Close':tick}, axis=1)
        all_prices = month_prices.join(all_prices).interpolate()
    return all_prices.reset_index()


def update_history(pf, days_back=120, store=True):
    global _prices
    if days_back < len(_prices):
        print('days_back < len(_prices')
        _prices = _prices.iloc[:-days_back].copy()
        return
    # Check if history file exists, not => scrape 120 days back and interpolate
    file_name = 'history/PF_history.xlsx'
    if not os.path.exists(file_name):
        print('Scraping 120 days back history of ticker prices')
        scraped_df = scrape_prices(pf['ticker'], days_back)
        scraped_df = to_eur(scraped_df, pf)
        scraped_df.iloc[:-1].to_excel(file_name, index=False)
        
    
    # Read history, add days not covered till today, interpolate (excluding today)
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    historic_p = pd.read_excel(file_name)
    delta = yesterday - historic_p.iloc[-1].Date
    if delta.days == 0:
        _prices = historic_p
    else:
        print('Adding new days to existing history')
        new_p = scrape_prices(pf['ticker'], delta.days + 1).iloc[:-1].copy()
        new_p = to_eur(new_p, pf)
        _prices = pd.concat([historic_p, new_p])
        _prices.to_excel(file_name, index=False)


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
    update_history(pf, days_back=120)
    pf['profit_perc'] = _prices.set_index('Date').iloc[-1][::-1].to_numpy()/pf.cost_per_stock_eur.to_numpy() - 1
    fig = px.bar(data_frame=pf, x='ticker', y='profit_perc', labels={'ticker':'', 'profit_perc':''}, color='ticker', color_discrete_map=dict(zip(pf['ticker'], pf['color'])), title=f'Profit Percentage', opacity=0.9)

    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return dcc.Graph(id="profit-bar", figure=fig)


def change_over_time_line(pf, pf_no_dupl, layout, stocks_or_pf, days_back):
    global _prices
    his_subset = _prices[-days_back:].set_index('Date').copy()
    perc_change = his_subset.pct_change().reset_index()
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

    print(his_subset)
    fig = px.line(data_frame=perc_change, x='Date', y=[y], labels=labels, color_discrete_sequence=colors, title=title, hover_data=['Profit'])
    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return fig