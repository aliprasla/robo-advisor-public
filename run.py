import os
import argparse
from threading import local
from src.portfolio import Portfolio




MAX_AMOUNT_UNINVESTED_DEFAULT = 100
BUY_ONLY_DEFAULT = True

print("==========================================================================")
print("Welcome to Ali's Portfolio Optimizer")
print("Don't sue me")

available_portfolios = [item for item in os.listdir('config/') if item != 'asset_universe.json']

my_parser = argparse.ArgumentParser(description = "Welcome to Ali's Portfolio Optimizer. \n Please don't sue me.")
my_parser.add_argument('--p',type = str,help = 'Name of portfolio in config/ directory. Available Portfolios {}'.format(available_portfolios))
my_parser.add_argument('--c',type=float,help='Amount to be invested')
my_parser.add_argument('--buy-only',type=bool,action=argparse.BooleanOptionalAction,default=BUY_ONLY_DEFAULT)
my_parser.add_argument('--u',type=float,default=MAX_AMOUNT_UNINVESTED_DEFAULT)


args = my_parser.parse_args()
print("=======================PARAMETERS================================")
print("Portfolio: {}".format(args.p))
print("Amount to be invested: ${:,.2f}".format(args.c))
print("Only Purchase Securities?: {}".format(args.buy_only))
print("Maximum Uninvested Capital: ${:,.2f}".format(args.u))
print("===================================================================")


print("Initializing Portfolio")
portfolio = Portfolio(args.p)

print("Portfolio Initialized. Creating Contribution calculations")

portfolio.contribute_to_portfolio(args.c,buy_only=args.buy_only,max_uninvested_capital=args.u)

print("Printing Summary")
portfolio.print_summary()


save_param = None
while save_param is None:
    user_response = input("Do you want to save this new portfolio to a json file? It will overwrite the previous file. (Y or N) ")
    user_response = user_response.lstrip().rstrip().lower()
    if user_response.lower() not in ['y','n']:
        print("Invalid input. Please try again.")
    elif user_response == 'y':
        save_param = True
    elif user_response == 'n':
        save_param = False
    else:
        raise Exception("Unknown error occured here.")


if save_param is True:
    portfolio.save_portfolio()

