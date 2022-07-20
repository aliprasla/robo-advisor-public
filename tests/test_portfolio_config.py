import unittest
import json
import pandas as pd
import numpy as np

## two things:

# make sure all security held are in the asset universe file
# make sure all target allocations add up to 100%

class TestPortfolioConfig(unittest.TestCase):
    def setUp(self):
        self.asset_universe = json.loads(open('config/asset_universe.json','r').read())
        self.portfolio = json.loads(open('config/portfolio.json','r').read())

    def test_target_allocations(self):
        for _key in self.portfolio.keys():
            target_allocation_dir = self.portfolio[_key]['target_portfolio']
            portfolio_share_series = pd.DataFrame(target_allocation_dir)['portfolio_share']

            self.assertAlmostEqual(portfolio_share_series.sum(),100,7)
    
    def test_securities_in_list(self):
        owned_securities = set()

        # all securities 
        for _key in self.portfolio.keys():
            current_holdings = self.portfolio[_key]['current_holdings']
            for holdings in current_holdings:
                if holdings['ticker'] not in owned_securities:
                    owned_securities.add(holdings['ticker'])

        # get all tickers
        ticker_universe_list = [item['tickers'] for item in self.asset_universe['data']]
        ticker_universe_set = set(np.concatenate(ticker_universe_list).flatten())

        for ticker in owned_securities:
            if ticker not in ticker_universe_set:
                raise Exception("Ticker Symbol, {}, is not in the asset_universe directory".format(ticker))

        

            
