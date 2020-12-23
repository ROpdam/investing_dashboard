import pandas as pd
import datetime
import os
from forex_python.converter import CurrencyRates
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


def shrink_pf(pf):
    pf = pf.sort_values('date')
    originals = pf[~pf.ticker.duplicated()].set_index('ticker')
    cols_to_add = ['number_of_stocks', 'total_cost_eur', 'transaction_costs']

    for i, row in pf[pf.ticker.duplicated()].iterrows():
        tick = row['ticker']
        originals.loc[tick, cols_to_add] = originals.loc[tick, cols_to_add] + row[cols_to_add]
    
    return originals.reset_index()


def get_hist_prices(pf, days_back=0):
    print('Retrieving prices...')

    if days_back == 0:
        from_date = pf['date'].min().strftime('%d/%m/%Y')
    elif days_back > len(_prices):
        print("More back than existing prices")
        from_date = (exclude_weekends() - datetime.timedelta(days=days_back)).strftime('%d/%m/%Y')
    else: 
        print("prices already exist")
        return _prices.iloc[-days_back:]
        # from_date = _prices.iloc[-1].Date.strftime('%d/%m/%Y')

    to_date = exclude_weekends().date().strftime('%d/%m/%Y')  #(exclude_weekends() - datetime.timedelta(days=1))
    all_prices = []
    pf = shrink_pf(pf)
    for i, row in pf.iterrows():
        search_results = investpy.search_quotes(text=row['ticker'], products=[row['product']], countries=[row['country']])
        # from_date = row['date'].strftime('%d/%m/%Y')
        for sr in search_results[:1]:
            hist_p = sr.retrieve_historical_data(from_date=from_date, to_date=to_date)['Close'].to_frame().rename({'Close':row['ticker']}, axis=1)
            all_prices.append(hist_p.interpolate(axis=1))
    
    return pd.concat(all_prices, axis=1)


def exclude_weekends():
    today = datetime.datetime.now()
    if today.weekday() == 6:
        return today - datetime.timedelta(days=2)
    if today.weekday() == 0:
        return today - datetime.timedelta(days=3)
    return today - datetime.timedelta(days=1)


def update_history(pf, days_back=0, store=True):
    global _prices

    # Check if history file exists, not => scrape back till first purchase
    file_name = 'history/PF_history.xlsx'
    if not os.path.exists(file_name):
        print('No existing PF_history, scraping ...')
        scraped_df = get_hist_prices(pf)
        scraped_df = to_eur(scraped_df, pf)
        scraped_df.to_excel(file_name, index=False)   

    # Read history, add days not covered till today
    yesterday = exclude_weekends() # Or Friday if today == Sunday
    historic_p = pd.read_excel(file_name)
    delta = yesterday - historic_p.iloc[-1].Date
    if delta.days == 0:
        _prices = historic_p
    else:
        print('Adding new days to existing history...')
        new_p = get_hist_prices(pf, days_back=delta.days)
        new_p = to_eur(new_p, pf)
        _prices = pd.concat([historic_p, new_p]).set_index('Date').interpolate(axis=0).reset_index(drop=True)
        _prices.to_excel(file_name, index=False)


def get_start_date(time_period):
    # Always adding 2 days for if today is a weekend
    if time_period == '1y':
        return datetime.datetime.now() - pd.DateOffset(months=12)
    elif time_period == '2y':
        return datetime.datetime.now() - pd.DateOffset(months=24)
    else:
        return datetime.datetime.now() - pd.DateOffset(months=int(time_period[0]))

def get_total(pf, his_subset):
    his_subset['Total Portfolio'] = 0
    for ticker, nos in zip(pf.ticker, pf.number_of_stocks):
        his_subset['Total Portfolio'] += his_subset[ticker].fillna(0) * nos
    return his_subset



######################################## FIGURES ############################################
def budget_pie(pf, b, layout):
    update_history(pf)
    # Init
    pf = pf.append({'color':'white', 'ticker':'Transaction', 'total_cost_eur':pf['transaction_costs'].sum()}, ignore_index=True)
    # Create fig
    fig = px.pie(data_frame=pf, values='total_cost_eur', names='ticker', color='ticker', color_discrete_map=dict(zip(pf['ticker'], pf['color'])), title='Portfolio Split', opacity=0.9, hole=0.3)
    # Update layout
    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return dcc.Graph(id="budget-pie", figure=fig)


# def profit_perc_bar(pf, layout):
#     pf['profit_perc'] = _prices.set_index('Date').iloc[-1][::-1].to_numpy()/pf.cost_per_stock_eur.to_numpy() - 1
#     fig = px.bar(data_frame=pf, x='ticker', y='profit_perc', labels={'ticker':'', 'profit_perc':''}, color='ticker', color_discrete_map=dict(zip(pf['ticker'], pf['color'])), title=f'Profit Percentage', opacity=0.9)

#     fig.update_layout(layout)
#     fig.update_traces(textfont={'color':'white', 'size':14})

#     return dcc.Graph(id="profit-bar", figure=fig)


def change_over_time_line(pf, layout, stocks_or_pf, time_period):
    global _prices
    
    start_date = get_start_date(time_period)
    days_back = (datetime.datetime.now() - start_date).days
    update_history(pf, days_back=days_back)
    his_subset = _prices.iloc[-days_back:].set_index('Date')
    perc_change = his_subset.apply(lambda x: x.div(x.iloc[0]).subtract(1).mul(100)).round(2)
    perc_change.set_index(perc_change.index.date, inplace=True)

    if stocks_or_pf == 'Individual Stocks':
        y = list(pf['ticker'].unique())
        colors = list(pf['color'].unique())
        title = stocks_or_pf
        fig = px.line(data_frame=perc_change, x=perc_change.index, y=y, color_discrete_sequence=colors, title=title)
        fig.update_layout(yaxis_title = "% Daily Change", xaxis_title="")
        for i, row in pf.iterrows():            
            if len(perc_change[perc_change.index == row.date][row.ticker]) > 0:
                fig.add_annotation(x=row.date, y=perc_change[perc_change.index == row.date][row.ticker].iloc[0], text=f"{row.number_of_stocks} {row.ticker}: {row.total_cost_eur}", 
                showarrow=True,
                font=dict(family="Courier New, monospace", size=12, color="#ffffff"),
                align="center",
                arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor=row.color,
                ax=20, ay=30,
                bordercolor=row.color, borderwidth=2, borderpad=4,
                bgcolor=row.color, opacity=0.8)

    elif stocks_or_pf == 'Portfolio':
        y = 'Total Portfolio'
        his_subset = get_total(pf, his_subset) #(pf['number_of_stocks'].to_numpy()[::-1] * his_subset).sum(axis=1)
        his_subset = his_subset.reset_index()
        his_subset['Profit'] = his_subset[y] - pf.total_cost_eur.sum()
        title = stocks_or_pf
        colors = ['red']
        if his_subset[y].iloc[-1] > pf.total_cost_eur.sum(): colors = ['green']
        fig = px.line(data_frame=his_subset, x='Date', y=[y], color_discrete_sequence=colors, title=title, hover_data=['Profit'])
        fig.update_layout(yaxis_title = "Value in Euros")
    
    fig.update_layout(layout)
    fig.update_traces(textfont={'color':'white', 'size':14})

    return fig