import pandas as pd
import os
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import datetime

from components import total_cost_eur, shrink_pf, budget_pie, profit_perc_bar, change_over_time_line

# TODO
# Make deployable on Heroku: roportfolio.heroku.app

########################################### Data ###########################################
# path = '/Users/Robin/Documents/personal_finance/Investing/Dashboard/data/'
path = './data/'

portfolio = pd.read_excel(path + 'investing_source.xlsx', sheet_name='Stocks')
portfolio['date'] = portfolio['date'].dt.date
portfolio = portfolio.apply(total_cost_eur, axis=1).sort_values('total_cost_eur', ascending=False)

pf_no_dupl = shrink_pf(portfolio)
ticker_dates = portfolio.set_index('ticker').groupby(level=0).apply(lambda x : list(x['date'])).to_dict()
profit_pf = portfolio.copy()
budget = pd.read_excel(path + 'investing_source.xlsx', sheet_name='Budget')
max_days = 120

if os.path.exists(path + 'history/PF_history.xlsx'):
    history = pd.read_excel(path + 'history/PF_history.xlsx')
    max_days = len(history)

########################################### Styles ###########################################
colors = {
        'background':'black',
        'text':'white',
        'background-plot':'black',
        'text-plot':'white'
    }

active_button_style = {
        'background-color': 'red',
        'color': 'white',
        'height': '50px',
        'width': '50px',
        # 'margin-left': '1px'
}

inactive_button_style = {
        'background-color': 'grey',
        'color': 'white',
        'height': '50px',
        'width': '50px',
        # 'margin-left': '1px'
}
        
# Budget pie chart
budget_pie_layout = {
        'plot_bgcolor':'rgba(0, 0, 0, 0)',
        'paper_bgcolor':'rgba(0, 0, 0, 0)',
        'title':{'font':{'size':20, 'color':'white'}},
        'legend':{'font':{'size':18, 'color':'white'}},
        'margin':{'pad':10},
        'xaxis':{'color':'white'},
        'yaxis':{'color':'white'}
        }

# Profit Percentage bar chart
profit_perc_bar_layout = {
        'plot_bgcolor':'rgba(0, 0, 0, 0)',
        'paper_bgcolor':'rgba(0, 0, 0, 0)',
        'title':{'font':{'size':20, 'color':'white'}},
        # 'legend':{'font':{'size':14, 'color':'white'}},
        'showlegend':False,
        'margin':{'pad':10},
        'xaxis':{'color':'white'},
        'yaxis':{'color':'white'}
         }

# Percentaeg change line chart
change_over_time_line_layout = {
        'plot_bgcolor':'rgba(0, 0, 0, 0)',
        'paper_bgcolor':'rgba(0, 0, 0, 0)',
        'title':{'font':{'size':20, 'color':'white'}},
        'legend':{'font':{'size':14, 'color':'white'}},
        # 'margin':{'pad':10},
        'xaxis':{'color':'white', 'showgrid':False},
        'yaxis':{'color':'white'}
         }


########################################### APP ###########################################
app = dash.Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP, path + 'external.css'])
server = app.server
app.config.suppress_callback_exceptions = True

app.layout = html.Div(
    [
        # Top Row
    html.Div(
        [
    html.Div('Personal Finance', style={'fontSize': 28, 'marginLeft':'40px', 'marginBottom':'50px', 'font-weight': 'bold', 'marginTop':'20px'}),
        # Controls and Budget
    html.Div([dbc.Button('More Controls', 
                id='more_controls_button',
                color='secondary', 
                className='mr-1',
                style={'margin-top':'20px', 'position':'absolute', 'right':300}),

    dbc.Collapse(
            dbc.Card(
                dbc.CardBody([
                    'Select Purchase Date of Stock',
                    dcc.Dropdown(
                        id='name-dropdown',
                        options=[{'label':i, 'value':i} for i in list(ticker_dates.keys())],
                        value = list(ticker_dates.keys())[0]
                    ), 
                    html.Div([
                    dcc.Dropdown(
                        id='opt-dropdown',
                        )
                    ]),
                 ]),
            style={'background-color':'black'}),
            id="collapse",
            style={'background-color':'black', 'margin-top':'5px', 'position':'absolute', 'right':400}
        )]),

    html.Div(dbc.RadioItems(
                    id='radio_pf-or-stocks',
                    options=[{'label': i, 'value': i} for i in ['Portfolio', 'Individual Stocks']],
                    value='Individual Stocks'),
                    style={'padding':'20px', 'margin-left':'50px'}
            ),
    html.Div(dbc.RadioItems(
                    id='radio-time-period',
                    options=[{'label': i, 'value': i} for i in ['1m', '3m', '6m', '1y', '2y']],
                    value='3m',
                    inline=True,
                ), style={'display':'inline-block', 'margin-left':'5%', 'margin-top':'1%'}
            ),

    html.P(
            [
                'In DeGiro', html.Br(), '\u20AC ', '{:.2f}'.format(round(float(budget.Budget.iloc[0]), 2))
            ], 
            style={'fontSize': 20, 'marginLeft':'20px', 'font-weight': 'bold', 'border':'solid white', 'padding':'10px', 'position':'absolute', 'right':0}),
    html.P(
            [
                'In Portfolio', html.Br(), '\u20AC ', '{:.2f}'.format(float(portfolio.total_cost_eur.sum()))
            ], 
            style={'fontSize': 20, 'marginLeft':'20px', 'font-weight': 'bold', 'border':'solid white', 'padding':'10px', 'position':'absolute', 'right':150})
        ], 
        className="row", style={'background-color':'black', 'color':'white'}),

    # Second Row
    html.Div(
            [
               dcc.Graph(id="change-line")
            ],
    style={'background-color':'black', 'color':'white', 'margin-left':'3%', 'margin-right':'2%'}),
    # Third Row
    html.Div(
        [
        html.Div(budget_pie(pf_no_dupl, budget, budget_pie_layout), style={'margin-left':'auto', 'margin-right':'10%'}),
        # html.Div(profit_perc_bar(pf_no_dupl, profit_perc_bar_layout), style={'margin-left':'200px'})
        ], 
        className="row", style={'background-color':'black', 'color':'white'}),

    html.Footer('Last edited November 2020', style={'color':'grey', 'margin-left':'1%'})
    ], 
    style={
        'background-color':'black',
        # 'width':'100%',
        # 'height':'100%'
        # 'top':'0px',
        # 'left':'0px',
        # 'margin': '0px',
        # 'z-index':'1000'
        })

####################################### CALL BACKS ############################################
@app.callback(
    Output('change-line', 'figure'),
    [
        Input('radio_pf-or-stocks', 'value'),
        Input('radio-time-period', 'value'),
    ]
)
def update_change_line(radio_pf, time_period):
    return change_over_time_line(pf_no_dupl, change_over_time_line_layout, stocks_or_pf=radio_pf, time_period=time_period)

@app.callback(
    Output("collapse", "is_open"),
    [Input("more_controls_button", "n_clicks")],
    [State("collapse", "is_open")]
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

@app.callback(
    dash.dependencies.Output('opt-dropdown', 'options'),
    [dash.dependencies.Input('name-dropdown', 'value')]
)
def update_date_dropdown(name):
    return [{'label': i, 'value': i} for i in ticker_dates[name]]

@app.callback(
    dash.dependencies.Output('profit-bar', 'figure'),
    [dash.dependencies.Input('name-dropdown', 'value'),
     dash.dependencies.Input('opt-dropdown', 'value')]
)
def update_profit_bar(ticker, date):
    global profit_pf
    tick_pf = profit_pf[profit_pf['ticker'] == ticker].copy()
    if (portfolio.date.astype(str)==date).any():
        print(tick_pf)
    return profit_perc_bar(portfolio, profit_perc_bar_layout)

if __name__ =='__main__':
    app.run_server(debug=True)