import sys, os
import argparse
import math
import time, datetime 
import random

from classes import Havelock
from classes import Bitcoin
from classes import Info
from classes import Rates 

from config import Config
from utils import get_console_size


hl = Havelock(Config)

sym = "AMHASH1"

orders = hl.fetchOrders()
hl.fetchBalance()

cash = hl.havelockBalanceAvailable 

hl.portfolio.addSymbol(sym)
hl.loadTransactionFile(Config.hl_history)
shares = hl.portfolio.getSymbol(sym).getShareQuantity()

myorders = dict((d["id"], d) for d in orders)

print "cash: {} - shares: {} - open orders: {}".format(
        cash, shares, len(myorders))

MIN_MAX_AMOUNT = (1, 350)
MIN_MAX_SLEEP = (4, 15)

wallet = {"cash": 0.50000, "shares": 1000, 
          "sold": 0.00000, "bought": 0.00000,
          "buy" : 0.00000, "sell"  : 0.00000,
          "fee" : 0.00000 }

current_orders = []

overview = 10

while True:
    myorders = dict((d["id"], d) for d in hl.fetchOrders())
    asks, bids = hl.fetchOrderbook(sym, full=True)
    
    asks = [{"price": float(d["price"]), 
             "amount": float(d["amount"]), 
             "id": int(d["id"])} for d in asks.values()]
    
    bids = [{"price": float(d["price"]), 
             "amount": float(d["amount"]), 
             "id": int(d["id"])} for d in bids.values()]

    asks.sort(key=lambda o: o["price"])
    bids.sort(reverse=True, key=lambda o: o["price"])

    # buying shares for price
    top_bid = bids[0]
    second_bid = bids[1]
    # selling shares for price
    top_ask = asks[0]
    second_ask = asks[1]
    # spread
    spread = top_ask["price"] - top_bid["price"]
    fee = top_ask["price"] * 0.004

    if spread < fee:
        print "##### SPREAD TO SMALL - waiting some seconds"
        time.sleep(random.randint(*MIN_MAX_SLEEP))
        continue

    myids = [int(x[0]) for x in myorders.items()]
 

    # check range to second 
    if top_bid["id"] in myids and second_bid["price"] < top_bid["price"]-1e-8:
        hl.cancelOrder(top_bid["id"])
    if top_ask["id"] in myids and second_ask["price"] > top_ask["price"]+1e-8:
        hl.cancelOrder(top_ask["id"])


    # check if top in bid:
    if top_bid["id"] not in myids:
        amount = random.randint(*MIN_MAX_AMOUNT)
        print "##### BID ACTION -- delete old -- create new #####"
        for o_id, o in myorders.items():
            if o["type"] == "bid" and o["symbol"] == sym:
                hl.cancelOrder(o_id)
        if cash < (top_bid["price"]+1e-8)*amount:
            print "NOT ENOUGH CASH to buy: {} at {}".format(amount, top_bid["price"])
        else:
            hl.createOrder(sym, "buy", top_bid["price"]+1e-8, amount)
    #else:
    #    print "##### NO BID ACTION #####"

    
    if top_ask["id"] not in myids:
        amount = random.randint(*MIN_MAX_AMOUNT)
        print "##### ASK ACTION -- delete old -- create new #####"
        for o_id, o in myorders.items():
            if o["type"] == "ask" and o["symbol"] == sym:
                hl.cancelOrder(o_id)
        hl.createOrder(sym, "sell", top_ask["price"]-1e-8, amount)
    #else:
    #    print "##### NO ASK ACTION #####"
    
    print "ask: {} bid: {} spread: {} ({:.3f}%) fee: {}".format(top_ask["price"], top_bid["price"],spread, spread/top_ask["price"]*100, fee)


    p = hl.portfolio
    t = p.symbols[sym]
    if overview <= 0:
        overview = 100
        hl.fetchTransactions()
        hl.fetchPortfolio()
        hl.fetchBalance()

        # (timezone -6h) + 24 hours
        since = 60*60*6 + 60*60*24

        hl.setStartDate(time.time()-(int(since)))
        hl.setEndDate(time.time())
        print "------> overview (24h) share balance: {} btc balance: {}".format(t.getShareQuantity(), p.getCurrentWin(sym)-t.getDividendAmount())
        overview -= 1

    elif overview % 10 == 0:
        hl.fetchTransactions()
        hl.fetchPortfolio()
        hl.fetchBalance()

        # (timezone -6h) + 2 hours
        since = 60*60*6 + 60*60*2

        hl.setStartDate(time.time()-(int(since)))
        hl.setEndDate(time.time())
        print "------> overview (2h) share balance: {} btc balance: {}".format(t.getShareQuantity(), p.getCurrentWin(sym)-t.getDividendAmount())
        overview -= 1
    else:
        overview -= 1




    time.sleep(random.randint(*MIN_MAX_SLEEP))


