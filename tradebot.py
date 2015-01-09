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

min_spread = 0.015
sell_fee = 0.004

def show_balance(havelock_obj, symbol, hours_back):
     # (timezone -6h) + X hours
    since = 60*60*6 + 60*60*hours_back

    p = havelock_obj.portfolio
    t = p.symbols[symbol]
    havelock_obj.setStartDate(time.time()-(int(since)))
    havelock_obj.setEndDate(time.time())
    balance = p.getCurrentWin(symbol)-t.getDividendAmount()
    print "------> overview ({:>2}h) share balance: {:>8} btc balance: {:>12.8f}". \
        format(hours_back, t.getShareQuantity(), balance)

    return balance

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

MIN_MAX_AMOUNT = (200, 550)
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
    fee = top_ask["price"] * sell_fee
    
    # showing current bid/ask
    print "-"*60
    print "SPREAD: {} ({:.3f}%) FEE: {}".format(spread, spread/top_ask["price"]*100, fee)
    for b, a in zip(bids[:10], asks[:10]):
        print "{:>7} - {:>12.8f} {}|{:>7} - {:>12.8f} {}". \
                format(b["amount"], b["price"], "<-" if b["id"] in myids else "  ",
                       a["amount"], a["price"], "<-" if a["id"] in myids else "  ")


    notrade = False
    if spread < fee:
        print "##### SPREAD TO SMALL - waiting some seconds"
        time.sleep(random.randint(*MIN_MAX_SLEEP))
        notrade = True

    if spread/top_ask["price"] < min_spread:
        print "##### SPREAD under 1,5% - wait..."
        time.sleep(random.randint(*MIN_MAX_SLEEP))
        notrade = True

    myids = [int(x[0]) for x in myorders.items()]
 
    # check range to second 
    if top_bid["id"] in myids and second_bid["price"] < top_bid["price"]-1e-8:
        print "-> too much diff in bid - canceling"
        hl.cancelOrder(top_bid["id"])
    if top_ask["id"] in myids and second_ask["price"] > top_ask["price"]+1e-8:
        print "-> too much diff in ask - canceling"
        hl.cancelOrder(top_ask["id"])

    if not notrade:
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
        
        # check if top in ask:
        if top_ask["id"] not in myids:
            amount = random.randint(*MIN_MAX_AMOUNT)
            print "##### ASK ACTION -- delete old -- create new #####"
            for o_id, o in myorders.items():
                if o["type"] == "ask" and o["symbol"] == sym:
                    hl.cancelOrder(o_id)
            hl.createOrder(sym, "sell", top_ask["price"]-1e-8, amount)
    
        p = hl.portfolio
    t = p.symbols[sym]
    if overview <= 0:
        overview = 100
        hl.fetchTransactions()
        hl.fetchPortfolio()
        hl.fetchBalance()
        hl.store(Config.hl_history)
        cash = hl.havelockBalanceAvailable 

        overview -= 1

    elif overview % 10 == 0:
        hl.fetchTransactions()
        hl.fetchPortfolio()
        hl.fetchBalance()
        hl.store(Config.hl_history)
        cash = hl.havelockBalanceAvailable 

        show_balance(hl, sym, 1)
        show_balance(hl, sym, 2)
        show_balance(hl, sym, 4)
        show_balance(hl, sym, 8)
        show_balance(hl, sym, 12)
        show_balance(hl, sym, 24)
        show_balance(hl, sym, 36)
        show_balance(hl, sym, 48)


        overview -= 1
    else:
        overview -= 1


    time.sleep(random.randint(*MIN_MAX_SLEEP))


