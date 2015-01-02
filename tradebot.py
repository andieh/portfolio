import sys, os
import argparse
import math
import time, datetime

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
shares = hl.portfolio.getSymbol(sym).getShareQuantity()

myorders = dict((d["id"], d) for d in orders)

print "cash: {} - shares: {} - open orders: {}".format(
        cash, shares, len(myorders))

while True:
    myorders = dict((d["id"], d) for d in hl.fetchOrders())
    asks, bids = hl.fetchOrderbook(sym, full=True)
    
    asks = [{"price": float(d["price"]), 
             "amount": float(d["amount"]), 
             "id": d["id"]} for d in asks.values()]
    
    bids = [{"price": float(d["price"]), 
             "amount": float(d["amount"]), 
             "id": d["id"]} for d in bids.values()]

    asks.sort(key=lambda o: o["price"])
    bids.sort(reverse=True, key=lambda o: o["price"])

    # buying shares for price
    top_bid = bids[0]
    # selling shares for price
    top_ask = asks[0]
    # spread
    spread = top_ask["price"] - top_bid["price"]

    # check if top in bid:
    if top_bid["id"] not in myorders:
        print "##### BID ACTION #####"
        print "- delete all old orders:"
        for o_id, o in myorders.items():
            if o["type"] == "bid" and o["symbol"] == sym:
                print "delete: ", hl.cancelOrder(o_id)
        print "- create new order: "
        print hl.createOrder(sym, "buy", top_bid["price"]+1e-8, 13)
        print "##### BID ACTION DONE #####"

    
    if top_ask["id"] not in myorders:
        print "##### ASK ACTION #####"
        print "- delete all old orders:"
        for o_id, o in myorders.items():
            if o["type"] == "ask" and o["symbol"] == sym:
                print "delete: ", hl.cancelOrder(o_id)
        print "- create new order: "
        print hl.createOrder(sym, "sell", top_bid["price"]-1e-8, 13)
        print "##### ASK ACTION DONE #####"

    print "top ask: {} bid: {} spread: {}".format(top_ask, top_bid, spread)
    
    time.sleep(4)


