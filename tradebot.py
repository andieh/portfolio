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

MIN_MAX_AMOUNT = (200, 550)

min_sleep = 0.1
max_sleep = 4

min_step = 1e-8

if len(sys.argv) != 2:
    print "Usage: python2 tradebot.py <symbol>"
    sys.exit(1)

# take symbol from cmdline
sym = sys.argv[1]

def get_balance(havelock_obj, symbol, hours_back, timezone=-6):
     # (timezone correction) + X hours
    start = time.time() - 60*60*-timezone + 60*60*hours_back
    end = time.time() - 60*60*-timezone 

    p = havelock_obj.portfolio
    t = p.symbols[symbol]

    havelock_obj.setStartDate(int(start))
    havelock_obj.setEndDate(int(end))
    balance = p.getCurrentWin(symbol) - t.getDividendAmount()

    return t.getShareQuantity(), balance

def show_balance(havelock_obj, symbol, timezone=6):
    for h in [1, 2, 4, 8, 12, 24, 48]:
        print "[i] ({:>2}h) shares: {:>8} btc: {:>12.8f}". \
            format(hours_back, *get_balance(havelock_obj, symbol, h, timezone))

def show_market_info(bids, asks, fee, myids=None):
    ids = myids or []

    print "{} @ {}".format("-"*60, time.ctime())
    
    # market stats:
    print "[i] spread: {} ({:.3%}) fee: {:.8f}". \
            format(spread, spread/(asks[0]["price"]), asks[0]["price"]*fee)

    # showing bids / asks
    for b, a in zip(bids[:10], asks[:10]):
        print "{:>7d} - {:>12.8f} {}|{:>7d} - {:>12.8f} {}". \
                format(b["amount"], b["price"], "<-" if b["id"] in ids else "  ",
                       a["amount"], a["price"], "<-" if a["id"] in ids else "  ")

def clean_orders(otype, symbol, orders):
    for o_id, o in myorders.items():
        if o["type"] == otype and o["symbol"] == symbol:
            hl.cancelOrder(o_id)

def get_bids_asks(symbol):
    asks, bids = hl.fetchOrderbook(symbol, full=True)
    
    asks = [{"price": float(d["price"]), 
             "amount": int(d["amount"]), 
             "id": int(d["id"])} for d in asks.values()]
    
    bids = [{"price": float(d["price"]), 
             "amount": int(d["amount"]), 
             "id": int(d["id"])} for d in bids.values()]

    asks.sort(key=lambda o: o["price"])
    bids.sort(reverse=True, key=lambda o: o["price"])

    return bids, asks

def update_log(hl_obj):
    hl_obj.fetchTransactions()
    hl_obj.fetchPortfolio()
    hl_obj.fetchBalance()
    hl_obj.store(Config.hl_history)


hl = Havelock(Config)

orders = hl.fetchOrders()
hl.fetchBalance()

cash = hl.havelockBalanceAvailable 

hl.portfolio.addSymbol(sym)
hl.loadTransactionFile(Config.hl_history)
shares = hl.portfolio.getSymbol(sym).getShareQuantity()

myorders = dict((d["id"], d) for d in orders)

print "cash: {} - shares: {} - open orders: {}".format(
        cash, shares, len(myorders))


wallet = {"cash": 0.50000, "shares": 500, 
          "sold": 0.00000, "bought": 0.00000,
          "buy" : 0.00000, "sell"  : 0.00000,
          "fee" : 0.00000 }

current_orders = []

overview = 10

while True:
    time.sleep(random.random() * (max_sleep-min_sleep) + min_sleep)

    # own orders + ids
    myorders = dict((d["id"], d) for d in hl.fetchOrders())
    myids = [int(x[0]) for x in myorders.items()]
    
    # get current asks/bids
    bids, asks = get_bids_asks(sym)

    # buying shares for price
    top_bid = bids[0]
    second_bid = bids[1]
    # selling shares for price
    top_ask = asks[0]
    second_ask = asks[1]
    # spread
    spread = top_ask["price"] - top_bid["price"]
    # current fee
    fee = top_ask["price"] * sell_fee
    # best prices 
    ask_price = top_ask["price"] + min_step 
    bid_price = top_bid["price"] - min_step

    show_market_info(bids, asks, sell_fee, myids)
    
    if spread < fee:
        print "[!] SPREAD BELOW FEE {:.8f} - waiting...". \
            format(fee)
        continue 

    elif spread/top_ask["price"] < min_spread:
        print "[!] SPREAD BELOW {:.2%} - waiting...". \
            format(min_spread)
        continue
 
    # check range to second (bid)
    if top_bid["id"] in myids and second_bid["price"] < top_bid["price"] - min_step:
        print "-> too much diff ({:.8f}) in bid order - canceling".format(
            bid_price - second_bid["price"])
        hl.cancelOrder(top_bid["id"])
        bid_price = second_bid["price"]

    # check range to second (ask)
    if top_ask["id"] in myids and second_ask["price"] > top_ask["price"] + min_step:
        print "-> too much diff ({:.8f}) in ask order - canceling".format(
            second_ask["price"] - ask_price)
        hl.cancelOrder(top_ask["id"])
        ask_price = second_ask["price"]

    # check if top in bid
    if top_bid["id"] not in myids:
        amount = random.randint(*MIN_MAX_AMOUNT)
        print "[i] BID action, delete existing, create new bid ({} @ {})".\
                format(amount, bid_price)

        clean_orders("buy", sym)
        hl.createOrder(sym, "buy", bid_price, amount)
    
    # check if top in ask:
    if top_ask["id"] not in myids:
        amount = random.randint(*MIN_MAX_AMOUNT)
        print "[i] ASK action, delete existing, create new ask ({} @ {})". \
                format(amount, ask_price)

        clean_orders("sell", sym, myorders)
        hl.createOrder(sym, "sell", ask_price, amount)

    if overview <= 0:
        overview = 10
        
        update_log(hl)
        cash = hl.havelockBalanceAvailable 
        show_balance(hl, sym)

    else:
        overview -= 1




