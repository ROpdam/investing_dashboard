import re
from io import StringIO
from datetime import datetime, timedelta

import requests
import pandas as pd


class YahooFinanceHistory:
    """
    Scrape financial data from yahoo finance website
    Found on: https://stackoverflow.com/questions/44225771/scraping-historical-data-from-yahoo-finance-with-python
    """
    timeout = 2
    crumb_link = 'https://finance.yahoo.com/quote/{0}/history?p={1}'
    crumble_regex = r'CrumbStore":{"crumb":"(.*?)"}'
    quote_link = 'https://query1.finance.yahoo.com/v7/finance/download/{quote}?period1={dfrom}&period2={dto}&interval=1d&events=history&crumb={crumb}'

    def __init__(self, symbol, days_back=7):
        self.symbol = symbol
        self.session = requests.Session()
        self.dt = timedelta(days=days_back)

    def get_crumb(self):
        response = self.session.get(self.crumb_link.format(self.symbol, self.symbol), timeout=self.timeout)
        response.raise_for_status()
        match = re.search(self.crumble_regex, response.text)
        if not match:
            raise ValueError('Could not get crumb from Yahoo Finance')
        else:
            self.crumb = match.group(1)

    def get_quote(self):
        if not hasattr(self, 'crumb') or len(self.session.cookies) == 0:
            self.get_crumb()
        now = datetime.utcnow()
        dateto = int(now.timestamp())
        datefrom = int((now - self.dt).timestamp())
        url = self.quote_link.format(quote=self.symbol, dfrom=datefrom, dto=dateto, crumb=self.crumb)
        response = self.session.get(url)
        try:
            response.raise_for_status()
        except:
            url = self.quote_link.format(quote=f'%5E{self.symbol}', dfrom=datefrom, dto=dateto, crumb=self.crumb)
            response = self.session.get(url)
            
        return self.create_df(response.text)
    
    def create_df(self, response):
        df = pd.read_csv(StringIO(response))#, parse_dates=['Date'])
        df.Date = pd.to_datetime(df.Date)
        return df