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
max_sleep = 2

min_step = 1e-8

#### Does not work as intended :(
# 'True' will lead to an cleared console in each iteration
# 'False' keeps writing to stdout as usual
clear_console = False


if len(sys.argv) != 2:
    print "Usage: python2 tradebot.py <symbol>"
    sys.exit(1)

# take symbol from cmdline
sym = sys.argv[1]

def get_balance(havelock_obj, symbol, hours_back, timezone=-6):
     # (timezone correction) + X hours
    start = time.time() - (60*60*-timezone + 60*60*hours_back)
    end = time.time() - (60*60*-timezone)
    
    p = havelock_obj.portfolio
    t = p.symbols[symbol]

    havelock_obj.setStartDate(int(start))
    havelock_obj.setEndDate(int(end))
    balance = p.getCurrentWin(symbol) - t.getDividendAmount()

    return t.getShareQuantity(), balance

def show_balance(hl_obj, symbol, timezone=-6):
    out = []
    for h in [1, 2, 4, 8, 12, 24, 48]:
        shares, balance = get_balance(hl_obj, symbol, h, timezone)
        out.append( (" {:>11d} ".format(h), 
                     " {:>11d} ".format(shares),
                     " {:>13.8f} ".format(balance)) )

    print "::"
    print ":: {:>13} :: {:>13} :: {:>14}".format(
            "since (h)", "shares", "balance")
    print ":: " + "-"*51
    for j, s, b in out:
        print ":: {} :: {} :: {}".format(j, s, b)

def show_market_info(hl_obj, bids, asks, fee, symbol, myids=None, last_table=None):
    ids = myids or []
 
    hl_obj.setStartDate(0)
    hl_obj.setEndDate(int(time.time()))

    print 
    top_frame_width = get_console_size()["width"] - len(time.ctime()) - 5
    print "{} # {}".format(":"*top_frame_width, time.ctime())
    
    # market stats:
    cash = hl_obj.havelockBalanceAvailable 
    shares = hl_obj.portfolio.getSymbol(symbol).getShareQuantity()
    print ":: symbol:   {}                 :: open orders: {:<2d}". \
        format(symbol, len(myids) if myids is not None else 0)
    print ":: spread: {:>12.8f} BTC ({:>6.3%}) :: fee:         {:<10.8f} BTC ({:>4.1%})". \
        format(spread, spread/(asks[0]["price"]), asks[0]["price"]*fee, fee)
    print ":: cash:   {:>12.8f} BTC          :: shares:      {:<6d}".\
        format(cash, shares)

    # showing bids / asks 
    out = ["::",]
    out.append(":: {:^25} |{:^25}".format("bids", "asks"))
    out.append(":: " + "-"*51 )
    for b, a in zip(bids[:12], asks[:12]):
        out.append("::  {:>6d} - {:>12.8f} {} |{:>6d} - {:>12.8f} {}". \
            format(b["amount"], b["price"], "<-" if b["id"] in ids else "  ",
                   a["amount"], a["price"], "<-" if a["id"] in ids else "  ")
        ) 
    
    # do not print same table multiple times... 
    # - except if console is cleared on each iteration
    if last_table != out or clear_console:
        print "\n".join(out)
    return out

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

def synchronize(hl_obj):
    hl_obj.fetchTransactions()
    hl_obj.fetchPortfolio()
    hl_obj.fetchBalance()
    hl_obj.store(Config.hl_history)
    return hl_obj

hl = Havelock(Config)
hl.loadTransactionFile(Config.hl_history)

# if symbol not in portfolio, add it 
if sym not in hl.portfolio.symbols:
    hl.portfolio.addSymbol(sym)

synchronize(hl)

overview = 1
last_table = None 
output = o = ""

while True:
    time.sleep(random.random() * (max_sleep-min_sleep) + min_sleep)
    if clear_console:
        print chr(27) + "[2J" 
        print chr(27) + "[H"
    
    
    # own orders + ids
    myorders = dict((d["id"], d) for d in hl.fetchOrders() if d["symbol"] == sym)
    myids = [int(x[0]) for x in myorders.items()]
    
    # get current asks/bids
    bids, asks = get_bids_asks(sym)
    # buying shares for price
    top_bid, second_bid = bids[:2]
    # selling shares for price
    top_ask, second_ask = asks[:2]
    # spread
    spread = top_ask["price"] - top_bid["price"]
    # current fee
    fee = top_ask["price"] * sell_fee
    # best prices 
    ask_price = top_ask["price"] - min_step 
    bid_price = top_bid["price"] + min_step

    # general market information
    last_table = show_market_info(
        hl, bids, asks, sell_fee, sym, 
        myids=myids, last_table=last_table)

    # show some balance overviews...
    if overview <= 0:
        overview = 10
        synchronize(hl)
        show_balance(hl, sym)
        last_table = 0
    else:
        overview -= 1
    
    tmpl_spread_low = ":: spread too low {}{:.8f} BTC ({:.2%}) - waiting..."
    if spread < fee:
        print "::"
        print tmpl_spread_low.format("", fee, sell_fee)
        continue

    elif spread/top_ask["price"] < min_spread:
        print "::"
        print tmpl_spread_low.format("may bid from: ", 
                   top_ask["price"] - top_ask["price"] * min_spread, 
                   min_spread) 
        continue
 
    # check range to second (bid)
    pre = ":: too much difference in price to second"
    if top_bid["id"] in myids and second_bid["price"] < top_bid["price"] - min_step:
        print "{} ({:.8f}) in bid order - canceling!". \
            format(pre, bid_price - second_bid["price"])
        hl.cancelOrder(top_bid["id"])
        bid_price = second_bid["price"] + min_step

    # check range to second (ask)
    if top_ask["id"] in myids and second_ask["price"] > top_ask["price"] + min_step:
        print "{} ({:.8f}) in ask order - canceling!". \
            format(pre, second_ask["price"] - ask_price)
        hl.cancelOrder(top_ask["id"])
        ask_price = second_ask["price"] - min_step

    # check if top in bid
    if top_bid["id"] not in myids:
        amount = random.randint(*MIN_MAX_AMOUNT)
        
        print ":: Placing bid order:"
        print ":: - delete old "
        clean_orders("bid", sym, myorders)
        print ":: - create order ({} @ {} = {})".format(amount, bid_price, amonut*bid_price)
        hl.createOrder(sym, "buy", bid_price, amount)
    
    # check if top in ask:
    if top_ask["id"] not in myids:
        amount = random.randint(*MIN_MAX_AMOUNT)
        print ":: Placing ask order:"
        print ":: - delete old "
        clean_orders("ask", sym, myorders)
        print ":: - create order ({} @ {} = {})".format(amount, ask_price, amount*ask_price)
        hl.createOrder(sym, "sell", ask_price, amount)


    



