import json
import requests
import datetime
import pandas as pd
from urllib.parse import urlencode, urlunsplit


class PortfolioRetriever:
    config_folder_path = "config/"

    def __init__(self,portfolio_name):
        self.portfolio_name = portfolio_name

        self.portfolio_file_path = self.config_folder_path + "/{}.json".format(portfolio_name)

        raw_portfolio = self._get_raw_portfolio(portfolio_name)
        
        self._raw_target_holdings = raw_portfolio['target_portfolio']

        self.target_holdings_df = pd.DataFrame(self._raw_target_holdings)

        self._raw_current_holdings = raw_portfolio['current_holdings']
        


    def _get_raw_portfolio(self,portfolio_name):
        file = open(self.portfolio_file_path,'r')
        json_data = json.loads(file.read())

        file.close()
        return json_data

    def load_current_prices(self):
        ticker_list = [item['ticker'] for item in self._raw_current_holdings]

        data_retriver = YahooStockPriceRetriver(ticker_list=ticker_list)

        current_price_list = data_retriver.get_current_prices()

        for holding_item in self._raw_current_holdings:
            for price_item in current_price_list:
                if price_item['ticker'] == holding_item['ticker']:
                    holding_item['price'] = price_item['bid_price']

        self.current_holdings_df = pd.DataFrame(self._raw_current_holdings)


    def save_new_portfolio(self,new_holdings_dataframe):
        """
        Takes new holdings dataframe
        """

        self._update_current_holdings_json(new_holdings_dataframe)

        file = open(self.portfolio_file_path,'w')

        new_json = {
            'target_portfolio':self._raw_target_holdings,
            'current_holdings':self._raw_current_holdings
        }
        st = json.dumps(new_json,indent=4)
        file.write(st)

        file.close()

        # write to portfolio file
    def _update_current_holdings_json(self,new_holdings_dataframe):
        new_raw_current_holdings_list = []
        for idx in range(new_holdings_dataframe.shape[0]):
            row = new_holdings_dataframe.iloc[idx]
            new_raw_current_holdings_list.append(
                {
                "ticker":row.ticker,
                "quantity":row.quantity_after_transactions}
                )

        self._raw_current_holdings =  new_raw_current_holdings_list

class AssetClassUniverseRetriver:
    asset_class_universe_file_path = "config/asset_universe.json"

    def load_asset_class_universe (self):
        raw_file = open(self.asset_class_universe_file_path,'r')
        self._raw_asset_class_universe = json.loads(raw_file.read())

        final_asset_class_list = []
        for item in self._raw_asset_class_universe['data']:
            asset_class_name = item['name']
            for ticker in item['tickers']:
                final_asset_class_list.append({
                    'ticker':ticker,
                    'asset_class':asset_class_name
                })
            
        self.asset_class_universe_df = pd.DataFrame(final_asset_class_list)



         
        

class YahooStockPriceRetriver:
    """
    Captures prices 
    """

    max_tickers_per_query = 10
    symbol_list_uri_separator = "%2C"
    region = "US"
    lang = "en"
    _url_scheme = 'https'
    _base_url = "yfapi.net"
    _current_prices_url = "/v6/finance/quote"
    _historical_prices_url = "/v8/finance/chart/VOO"

    # TODO: create new account and add to environment
    _api_key = "fs6UBbghya8K7quvqGHdfeXACsQZ06meEHxNGy30"

    # driven by yahoo finance api
    _acceptable_date_ranges = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', '10y', 'ytd' 'max']

    _acceptable_types = ['open','close','adj_close','low','high']

    _acceptable_intervals = ['1m', '5m', '15m','1d','1w','1mo']


    
    def __init__(self, ticker: str = None, ticker_list : list = None):
        if ticker is None and ticker_list is None:
            raise ValueError("You must specify a stock ticker or a list of stock tickers when initializing YahooStockPriceRetriver.")
        elif ticker is not None and ticker_list is not None:
            raise ValueError("You cannot specifiy both an individual ticker and a ticker list when initializing YahooStockPriceRetriver")

        elif ticker is not None:
            self._is_single_ticker = True 
            if type(ticker) != str:
                raise TypeError("Ticker parameter must be a string.")


            self.ticker = ticker

        elif ticker_list is not None:
            self._is_single_ticker = False

            # validate ticker_list 

            if type(ticker_list) != list:
                raise TypeError("Ticker_list must be a list.")

            for item in ticker_list:
                if type(item) != str:
                    raise TypeError("Each item in ticker list should be a string")

         
            self.ticker_list = ticker_list

        else:
            raise Exception("Something went wrong here.")

    def _create_symbol_list(self):
        # Construct symbol_list.
        symbol_list = []
        if self._is_single_ticker is True:
            symbol_list.append(self.ticker)


        elif self._is_single_ticker is False:
            # if you have a ticker list
            current_symbol_url_item = ""
            for item_number,ticker in enumerate(self.ticker_list):

                if current_symbol_url_item == "":
                    current_symbol_url_item = ticker
                else:
                    current_symbol_url_item = current_symbol_url_item + self.symbol_list_uri_separator + ticker

                if item_number % (self.max_tickers_per_query) == self.max_tickers_per_query - 1:
                    # if you've hit the max number of symbols per query, start a new query list.

                    symbol_list.append(current_symbol_url_item)
                    current_symbol_url_item = ""

            if current_symbol_url_item != "":
                symbol_list.append(current_symbol_url_item)

        return symbol_list

    def get_current_prices(self):
        # make requests using symbol list
        current_price_list = []
        for symbol in self._create_symbol_list():
            url_query = urlencode({
                'region':self.region,
                'lang':self.lang,
                'symbols':symbol

            })

            final_url = urlunsplit((self._url_scheme,self._base_url,self._current_prices_url,url_query,""))
            
            response = requests.get(url=final_url.__str__(),
                            headers={ 'accept':'application/json', 'X-API-KEY':self._api_key }
                        )

            quote_time = datetime.datetime.now()

            try:
                quote_list = response.json()['quoteResponse']['result']

            except:
                raise Exception("Unable to parse Yahoo API response. Output: {}".format(response.json()))

            
            for quote in quote_list:
                current_price_list.append({'ticker':quote['symbol'],'bid_price':quote['bid'],'quote_time':quote_time})
            
        return current_price_list






    # def get_historic_prices(self,range:str = "5y", type:str = 'adj_close',interval:str ="1mo",include_returns:bool = True):

    #     # validate parameters
    #     if range not in self._acceptable_date_ranges: 
    #         raise ValueError("Invalid Range Parameter: {0}. Acceptable ranges: {1}".format(range,self._acceptable_date_ranges))
    #     if type not in self._acceptable_types:
    #         raise ValueError("Invalid Type Parameter: {0}. Acceptable ranges: {1}".format(type,self._acceptable_types))

    #     if interval not in self._acceptable_intervals:
    #         raise ValueError("Invalid Interval Parameter: {0}. Acceptable ranges: {1}".format(interval,self._acceptable_intervals))

    #     for symbol in self._create_symbol_list():
    #         url_query = urlencode({
    #             'region':self.region,
    #             'lang':self.lang,
    #             'comparisons':symbol,
    #             'interval':interval,
    #             'range':range,
    #             'events':'div,split'
    #         })
    #         final_url = urlunsplit((self._url_scheme,self._base_url,self._historical_prices_url,url_query,""))

    #         response = requests.get(url=final_url.__str__(),
    #                         headers={ 'accept':'application/json', 'X-API-KEY':self._api_key }
    #                     )

    #         quote_time = datetime.datetime.now()

    #         response_json = response.json()

    #         if response_json['chart']['error'] is not None:
    #             raise Exception("Error in Pulling API: {}".format(response_json['chart']['error']))
            
    #         timestamps = response_json['chart']['result'][0]['timestamp']

    #         comparison_items = response_json['chart']['result'][0]['comparisons']

    #         ticker_data_dict = {}
    #         for item in comparison_items:
    #             ticker = item.pop('symbol')
    #             item.pop('chartPreviousClose')
    #             historical_df = pd.DataFrame(item)

    #             historical_df['timestamp'] = timestamps
                
                
    #             historical_df['timestamp'] = historical_df['timestamp'].map(datetime.datetime.utcfromtimestamp)

                

    #             import code
    #             code.interact(local=locals())
                



