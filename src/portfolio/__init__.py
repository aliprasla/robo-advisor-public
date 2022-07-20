from cgi import print_environ_usage
import pandas as pd
from src.data_collector import PortfolioRetriever
from src.data_collector import AssetClassUniverseRetriver

# convex optimization problem solver
import cvxpy as cp
import numpy as np

class Portfolio:

    ROUNDING_PRECISION = 5
    def __init__(self,portfolio_name):
        self.portfolio_name = portfolio_name
        
        self.retriver = PortfolioRetriever(portfolio_name)
        self.retriver.load_current_prices()

        self.current_holdings = self.retriver.current_holdings_df

        self.target_holdings = self.retriver.target_holdings_df

        assert np.round(self.target_holdings.portfolio_share.sum(),self.ROUNDING_PRECISION) == 1, "Target Asset Class Allocation Dataframe does not sum to 1"

        asset_class_retriver = AssetClassUniverseRetriver()

        asset_class_retriver.load_asset_class_universe()

        self.asset_class_universe_df = asset_class_retriver.asset_class_universe_df

        # add asset class column to current holdings
        self.current_holdings = pd.merge(self.current_holdings,self.asset_class_universe_df,on = "ticker",how="left")
        print("Current Market Value: ${:,.2f}".format((self.current_holdings.quantity * self.current_holdings.price).sum()))

    def __str__(self):
        return self.current_holdings.__str__()

    def print_summary(self):
        assert 'transactions_to_make' in self.current_holdings.columns, "New Contribution Amount has not been made to the portfolio yet. Call contribute_to_portfolio method before calling this method"

        print("================================= PRINTING FINAL HOLDINGS ====================================================")

        print(self.current_holdings[['ticker','asset_class','price','previously_owned_quantity','quantity_after_transactions']])


        print("================================== PRINTING ASSET CLASS SUMMARY ===============================================")

        # print final allocation differences from target allocation
        print(self.asset_class_summary)
        

        print("================================= PRINTING TRANSACTIONS ========================================================")

        

        for ticker in self.current_holdings.ticker.values:
            assert len(self.current_holdings[self.current_holdings.ticker == ticker]) == 1, "Ticker, {} is not unique in Portfolio. Something went wrong here.".format(ticker)

            ticker_row = self.current_holdings[self.current_holdings.ticker == ticker].iloc[0]

            transactions = int(ticker_row.transactions_to_make)
            

            price = ticker_row.price


            if ticker_row.transactions_to_make != 0:
                if ticker_row.transactions_to_make > 0:
                    print("Buy {0}  --- {1} @ {2} ---- Previous Quantity Owned: {3} --- Final Quantity Owned: {4}".format(ticker, transactions, price ,ticker_row.previously_owned_quantity, ticker_row.quantity_after_transactions))
                else:
                    print("Sell {0} --- {1} @ {2}---- Previous Quantity Owned: {3} --- Final Quantity Owned: {4}".format(ticker,transactions, price, ticker_row.previously_owned_quantity, ticker_row.quantity_after_transactions))


        


        previous_asset_class_allocation = self.current_holdings.groupby('asset_class')['previous_percent_of_portfolio'].sum()

        final_percent_of_portfolio = self.current_holdings.groupby('asset_class')['final_percent_of_portfolio'].sum()

        # get target holdings
        
        assert np.array_equal(previous_asset_class_allocation.index, self.target_holdings.asset_class_name.values), "Previous asset class allocation and target holdings array out of index order"

        assert np.array_equal(final_percent_of_portfolio.index,self.target_holdings.asset_class_name.values), "Final Percent of portfolio and target holdings array out of index"

        error_before_contribution = ((previous_asset_class_allocation.values- self.target_holdings.portfolio_share.values) ** 2).sum()

        error_after_contribution = ((final_percent_of_portfolio- self.target_holdings.portfolio_share.values) ** 2).sum()

        print("================================ ERROR SUM SQUARED DIFFERENCES FROM TARGET ALLOCATIONS ==================")
        print("Sum Squared Error before contribution: {}".format(error_before_contribution))
        print("Sum Squared Error after contribution: {}".format(error_after_contribution))

        print("Percent improvement: {} %".format(((np.round((error_after_contribution - error_before_contribution) / error_before_contribution * 100,self.ROUNDING_PRECISION)))))

        print("================================== UNINVESTED CAPITAL ====================================================")        
        total_cash_outflow_after_transactions =  (self.current_holdings.transactions_to_make * self.current_holdings.price).sum()

        # pretty up
        if total_cash_outflow_after_transactions >= 0:
            print("Net Purchases of Securities: ${:,.2f}".format(total_cash_outflow_after_transactions))
        else:
            print("Net Purchases of Securities: =${:,.2f}".format(abs(total_cash_outflow_after_transactions)))
            
        print("Uninvested Capital After Transactions: ${:,.2f}".format(self.dollar_amount_contributed - total_cash_outflow_after_transactions))

    def contribute_to_portfolio(self,dollar_amount_contributed : float, buy_only:bool = True, max_uninvested_capital:float = 50):
        """
        
        Investment Methodlogy - 

        Minimize the Sum of Squared Differences between the asset class and the target portfolio allocation by buying certain securities.


        dollar_amount_contributed (float) : Amount of dollars to add to the portfolio
        buy_only (bool) : Will the optimizer buy & sell securities or only buy? (Important for taxation)
        max_uninvested_capital : Maximum dollars remaining after purchases are complete. $50 by default

        """
        self.dollar_amount_contributed = dollar_amount_contributed
        self.buy_only = buy_only
        self.max_uninvested_capital = max_uninvested_capital

        current_holdings = self.current_holdings.copy()

        current_holdings_with_optimized_transactions = self.calculate_individual_security_transactions(current_holdings,
                                                                            dollar_amount_contributed=dollar_amount_contributed,
                                                                            buy_only=buy_only,
                                                                            max_uninvested_capital=max_uninvested_capital)

        

        # add quantity labels
        
        current_holdings_with_optimized_transactions.rename(columns={'quantity':'previously_owned_quantity'},inplace=True)
        current_holdings_with_optimized_transactions['previous_percent_of_portfolio'] =  (current_holdings_with_optimized_transactions.price * current_holdings_with_optimized_transactions.previously_owned_quantity) / (current_holdings_with_optimized_transactions.price * current_holdings_with_optimized_transactions.previously_owned_quantity).sum()


        current_holdings_with_optimized_transactions['quantity_after_transactions'] = current_holdings_with_optimized_transactions.previously_owned_quantity + current_holdings_with_optimized_transactions.transactions_to_make

        current_holdings_with_optimized_transactions['final_percent_of_portfolio'] = (current_holdings_with_optimized_transactions.price * current_holdings_with_optimized_transactions.quantity_after_transactions) / (current_holdings_with_optimized_transactions.price * current_holdings_with_optimized_transactions.quantity_after_transactions).sum()

        self.current_holdings = current_holdings_with_optimized_transactions

        # create summary attribute

        new_asset_class_allocations = self.current_holdings.groupby('asset_class')['final_percent_of_portfolio'].sum()
        old_asset_class_allocations = self.current_holdings.groupby('asset_class')['previous_percent_of_portfolio'].sum()


        self.asset_class_summary = pd.merge(self.target_holdings,old_asset_class_allocations,left_on='asset_class_name',right_index=True,how='left')
        
        self.asset_class_summary = pd.merge(self.asset_class_summary,new_asset_class_allocations,left_on='asset_class_name',right_index = True,how='left')


        self.asset_class_summary.rename(columns={'portfolio_share':'target_portfolio_share','final_percent_of_portfolio':'share_after_contribution','previous_percent_of_portfolio':'share_before_contribution'},inplace=True)

        # reformat to look appealing
        
    
    def calculate_individual_security_transactions(self,current_holdings,dollar_amount_contributed,buy_only,max_uninvested_capital):
        
        if type(buy_only) != bool:
            raise TypeError("buy_only param must be a boolean.")

        assert type(dollar_amount_contributed) == float or type(dollar_amount_contributed) == int, "dollar_amount_contributeed must be a float or an int"

        # Construct the problem.
        price_vec = current_holdings.price.values

        number_of_tickers = price_vec.shape[0]


        current_quantities_vec = current_holdings.quantity.values





        # create empty variable matrix. the diagonals of this matrix will be the transactions
        # integer == only whole stocks. 
        purchase_matrix = cp.Variable((number_of_tickers,number_of_tickers),integer=True)

        security_asset_class_mapping_matrix, ticker_index_mapping, asset_class_index_mapping = self.create_security_asset_class_matrix(current_holdings)

        target_asset_class_allocation_dollars = self.create_target_asset_class_allocation_vector(current_holdings,asset_class_index_mapping,dollar_amount_contributed)
        




        # construct least squared difference between Target allocation (in dollars) and the final allocation


        # get the final market_caps for each security by multiplying the ending quantity held for the security by the price
        final_market_caps = current_quantities_vec * price_vec +  price_vec @ purchase_matrix

        # assert that the order of your security asset class mapping matrix equals the ordering of your price vector
        for i in range(number_of_tickers):
            assert current_holdings.ticker[i] == ticker_index_mapping[i], "Misaligned index for ticker mapping"


        # multiply by the security_asset_class_mapping_matrix 
        final_asset_class_allocation_dollars = final_market_caps @ security_asset_class_mapping_matrix


        cost_func =  cp.sum_squares( final_asset_class_allocation_dollars- target_asset_class_allocation_dollars)
        
        # minimize least squares
        mini = cp.Minimize(cost_func)


        # add diagonal constraint manually
        constraint_list = []
        for idx in range(number_of_tickers):
            # make sure there are only values in the diagonals
            constraint_list.append(purchase_matrix[:,idx] @ price_vec == purchase_matrix[idx,idx] * price_vec[idx])
            
            # make sure you don't sell more than you own - no short selling constraint
            constraint_list.append(current_quantities_vec[idx] + purchase_matrix[idx,idx] >= 0)

            if buy_only is True:
                # if you are buying only 
                constraint_list.append(purchase_matrix[idx,idx] >= 0)


        # add contribution amount constraint - sum of all purchased securities should be less than the contribution amount
        constraint_list.append(dollar_amount_contributed - cp.sum(price_vec @ purchase_matrix) >= 0)




        # add max_uninvested constraint - contribution amount + net transaction cash flow has to be less than the max uninvested capital parameter
        constraint_list.append(dollar_amount_contributed - cp.sum(price_vec @ purchase_matrix) <= max_uninvested_capital)


        

        prob = cp.Problem(mini,constraints=constraint_list)
        
        result = prob.solve(solver=cp.CPLEX)
        
        if prob.status != 'optimal':
            print("OPTIMAL SOLUTION NOT FOUND. OPENING DEBUGGING SHELL")
            import code
            code.interact(local=locals())

        print("Optimization Successful")


        current_holdings['transactions_to_make'] = purchase_matrix.value.diagonal()
        
    
        return current_holdings


    def create_target_asset_class_allocation_vector(self,current_holdings,asset_class_index_mapping,dollar_amount_contributed):

        target_allocation_percentages = np.zeros(len(asset_class_index_mapping))

        for asset_class_name in asset_class_index_mapping.keys():

            # get index from dictionary
            index = asset_class_index_mapping[asset_class_name]

            # allocation from target holdings
            row = self.target_holdings[self.target_holdings.asset_class_name == asset_class_name]

            assert row.shape[0] == 1, "Duplicate asset_class_name {} present in target holdings json".format(asset_class_name)

            # overwrite existing output vector
            target_allocation_percentages[index] = row.iloc[0].portfolio_share


        # make sure
        assert np.round(target_allocation_percentages.sum(),self.ROUNDING_PRECISION) == 1, "Portfolio file's target allocation do not sum to 1"

        # calculate final market value of entire portfolio

        final_market_value = (current_holdings.price * current_holdings.quantity).sum() + dollar_amount_contributed

        return target_allocation_percentages * final_market_value



        





    def create_security_asset_class_matrix(self,current_holdings):
        """
        Creates a n x m numpy matrix with each row representing a security and each column representing an asset class.

        If [n,m] == 1, this means the security belongs to the specified asset class.
        """
        
        # keep index the same

        ticker_index_mapping_dict = {i: current_holdings.iloc[i]['ticker'] for i in range(self.current_holdings.shape[0])}
        unique_asset_classes = np.unique(current_holdings.asset_class.values)

        asset_class_index_mapping_dict = {unique_asset_classes[i]:i for i in range(len(unique_asset_classes))}

        # create empty matrix
        output_matrix = np.zeros((len(ticker_index_mapping_dict),len(unique_asset_classes)))

        for ticker_index in range(len(ticker_index_mapping_dict)):
            ticker_name = ticker_index_mapping_dict[ticker_index]
            
            # lookup asset class
            ticker_df = self.current_holdings[self.current_holdings.ticker == ticker_name]

            assert ticker_df.shape[0] == 1, "Duplicated ticker in portfolio: {}".format(ticker_name)

            asset_class_name = ticker_df.iloc[0]['asset_class']

            # get asset class index
            asset_class_index = asset_class_index_mapping_dict[asset_class_name]

            # overwrite 0 in output matrix to one for that specific pairing
            output_matrix[ticker_index][asset_class_index] = 1 

        
        # check to see if rows sum to one
        assert np.array_equal(np.sum(output_matrix,axis = 1),(np.ones(len(ticker_index_mapping_dict)))), "Something went wrong here. Rows in output matrix do not sum to 1. Actual sum: {}".format(np.sum(output_matrix,axis=1))
        
        
        return output_matrix, ticker_index_mapping_dict, asset_class_index_mapping_dict


    def save_portfolio(self):
        assert 'transactions_to_make' in self.current_holdings.columns, "New Contribution Amount has not been made to the portfolio yet. Call contribute_to_portfolio method before calling this method"

        self.retriver.save_new_portfolio(self.current_holdings)

