import pandas as pd
from forex_python.converter import CurrencyRates
from yahoo_scraping import YahooFinanceHistory
import plotly.express as px
import dash_html_components as html
import dash_core_components as dcc


def to_eur(x):
    if x['currency'] is not 'EUR':
        x['total_cost_eur'] = x['number_of_stocks'] * x['cost_per_stock_eur']
    else: 
        x['total_cost_eur'] = x['number_of_stocks'] * x['cost_per_stock_eur']
    return x


def shrink_pf(pf):
    pf = pf.sort_values('date')
    originals = pf[~pf.ticker.duplicated()].set_index('ticker')
    cols_to_add = ['number_of_stocks', 'total_cost_eur', 'transaction_costs']

    for i, row in pf[pf.ticker.duplicated()].iterrows():
        tick = row['ticker']
        originals.loc[tick, cols_to_add] = originals.loc[tick, cols_to_add] + row[cols_to_add]
    
    return originals.reset_index()


def perc_change_month(pf):
    all_prices = pd.DataFrame()
    for i, row in pf.iterrows():
        month_prices = YahooFinanceHistory(row['ticker'], days_back=30).get_quote().set_index('Date')['Close'].to_frame().rename({'Close':row['ticker']}, axis=1)
        all_prices = month_prices.join(all_prices * row['number_of_stocks'])
    
    return all_prices


def get_perc(row, days):
    avg_close = YahooFinanceHistory(row['ticker'], days_back=days).get_quote()['Close'].mean()
    row['profit_perc'] = avg_close/row['cost_per_stock'] - 1
    
    return row


def budget_pie(pf, b, layout):

    # Init
    pf = pf.append({'color':'white', 'ticker':'Transaction', 'total_cost_eur':pf['transaction_costs'].sum()}, ignore_index=True)

    # Create fig
    fig = px.pie(data_frame=pf, values='total_cost_eur', names='ticker', color_discrete_sequence=list(pf['color']), title='Portfolio Split', opacity=0.9, hole=0.3)

    # Update layout
    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return dcc.Graph(id="budget-pie", figure=fig)


def profit_perc_bar(pf, layout, days=1):
    pf = pf.apply(lambda x: get_perc(x, days), axis=1)
    fig = px.bar(data_frame=pf, x='ticker', y='profit_perc', labels={'ticker':'', 'profit_perc':'Profit Ratio'}, color=list(pf['color']), color_discrete_map='identity', title=f'Profit Percentage', opacity=0.9)

    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return dcc.Graph(id="profit-bar", figure=fig)


def change_over_time_line(pf, pf_no_dupl, layout, input, days=30):
    pf_over_time = perc_change_month(pf)
    if input == 'Individual Stocks':
        y = list(pf_no_dupl['ticker'])
        colors = list(pf_no_dupl['color'])
        title = 'Portfolio Over Time (Individual Stocks)'
        labels = {'y':'Percentage Daily Change'}
    elif input == 'Portfolio':
        y = pf_over_time.sum(axis=1)
        title = 'Portfolio Over Time'
        labels = {'y':'Value in Euros'}
        if pf_over_time.sum(axis=1).iloc[-1] > pf.total_cost_eur.sum():
            colors = ['green']
        else:
            colors = ['red']

    fig = px.line(data_frame=pf_over_time.reset_index(), x='Date', y=y, labels=labels, color_discrete_sequence=colors, title=title)
    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return fig