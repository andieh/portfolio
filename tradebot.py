#-*- coding: utf-8 -*-

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

sell_fee = 0.004
min_spread = sell_fee * 2

MIN_MAX_SELL = (60, 350)
MIN_MAX_BUY = (60, 350)

# minimal trading difference/step
min_step = 1e-8

# timezone shift of target
TZ_SHIFT = -6

# prohibit any order creation (canceling is ok)
DO_NOT_TRADE = False

# clear console before writing new content
CLEAR_CONSOLE = True

# starttime
STARTTIME = time.time()
TRADEVOLUME = 1000


if len(sys.argv) != 2:
    print "Usage: python2 tradebot.py <symbol>"
    sys.exit(1)

# take symbol from cmdline
sym = sys.argv[1]

# fancy (useless) header shit 
header_idx = 3
header_dir = 1

def get_balance(havelock_obj, symbol, hours_back, timezone=-6):
     # (timezone correction) + X hours
    start = time.time() - (60*60*-timezone + 60*60*hours_back)
    end = time.time() - (60*60*-timezone)
    
    p = havelock_obj.portfolio
    t = p.symbols[symbol]
    

    havelock_obj.setStartDate(int(start))
    havelock_obj.setEndDate(int(end))
    balance = p.getCurrentWin(symbol) - t.getDividendAmount()
    
    return {"amount": t.getShareQuantity(), 
            "balance": balance,
            "buys": havelock_obj.transactions.getBuyAmount(symbol),
            "sells": havelock_obj.transactions.getSellAmount(symbol),
            "fees": havelock_obj.transactions.getFeeAmount(symbol),
            "buy_shares" :havelock_obj.transactions.getBuyQuantity(symbol),
            "sell_shares": havelock_obj.transactions.getSellQuantity(symbol)
            }

def show_market_info(hl_obj, bids, asks, fee, symbol, myids=None):
    ids = myids or []

    o, to = [], []

    # time and header-line
    dt = time.strftime("%d.%m.%Y \\\\ %H:%M:%S \\\\")
    top_frame_width = get_console_size()["width"] - len(dt) - 6
    o.append("{} \\\\ {}".format(
        ":"*top_frame_width, dt))
    
    # wormy header 
    global header_idx, header_dir 
    worm_parts = ["o","O","0", "o"]
    o[-1] = o[-1][:header_idx-1] + \
            "".join(random.choice(worm_parts) for i in xrange(3)) + \
            o[-1][header_idx+2:]
    header_idx += header_dir
    if header_idx > top_frame_width - 5:
        header_dir = -1
        header_idx = top_frame_width - 5
    elif header_idx < 3:
        header_dir = 1
        header_idx = 3 
    elif random.random() < 0.05:
        header_dir *= -1

   
    # reset start/end for transactions
    hl_obj.setStartDate(0)
    hl_obj.setEndDate(int(time.time()))
    
    # market stats:
    cash = hl_obj.havelockBalanceAvailable 
    shares = hl_obj.portfolio.getSymbol(symbol).getShareQuantity()

    o.append(":: symbol:   {}                 :: open orders: {:<2d}". \
        format(symbol, len(myids) if myids is not None else 0))
    o.append(":: spread: {:>12.8f} BTC ({:>6.3%}) :: fee:         {:<10.8f} BTC ({:>4.1%})". \
        format(spread, spread/(asks[0]["price"]), asks[0]["price"]*fee, fee))
    o.append(":: cash:   {:>12.8f} BTC          :: shares:      {:<6d}".\
        format(cash, shares))

    # showing bids / asks 
    o.append("::" + " "*79 + "{:^65}".format("mBTC"))
    o.append("::" + " "*78 + "+" + "-"*60)
    o.append("::{:^25} |{:^25}  {:>13} | {:>7} | {:>7} | {:>7} | {:>7} | {:>8} | {:>8} | {:>9}". \
            format(""    , ""    , "window", "", "",             "", "", "Ø-buy", "Ø-sell", ""))
    o.append("::{:^25} |{:^25}  {:>13} | {:>7} | {:>7} | {:>7} | {:>7} | {:>7} | {:>7} | {:>9}". \
            format("bids", "asks", "hours"  , "shares", "balance", "buys", "sells", "price", "price", "Ø win"))

    o.append(":: " + "-"*51 + " "*6 + "-"*81) 
    
    data = [[], [], [], [], [], [], [], []]
    for h in [1, 2, 6, 12, 24, 24*4, 24*10, 24*20, 24*30, 24*60, 24*90, 24*178]:
        data[0].append(h)
        d = get_balance(hl_obj, symbol, h, TZ_SHIFT)
        data[1].append(d["amount"])
        data[2].append(d["balance"])
        data[3].append(d["buys"])
        data[4].append(d["sells"])
        b = (d["buys"] / d["buy_shares"]) if d["buy_shares"] > 0 else 0
        data[5].append(b)
        s = ((d["sells"]+d["fees"]) / d["sell_shares"]) if d["sell_shares"] > 0 else 0
        data[6].append(s)
        data[7].append(s - b)
    
    for bid, ask, hours, shares, balance, buys, sells, avg_buy, avg_sell, avg_price in \
            zip(bids[:12], asks[:12], *data):

        o.append(":: {:>6d} - {:>12.8f} {} |{:>6d} - {:>12.8f} {}". \
            format(bid["amount"], bid["price"], 
                   "<-" if bid["id"] in ids else "  ",
                   ask["amount"], ask["price"], 
                   "<-" if ask["id"] in ids else "  ")
        )
        o[-1] += " "*4
        o[-1] += "{:>12d} | {:>7d} | {:>7.1f} | {:>7.1f} | {:>7.1f} | {:>7.5f} | {:>7.5f} | {:>8.5f}". \
                format(hours, shares, balance*1e3, buys*1e3, sells*1e3, avg_buy*1e3, avg_sell*1e3, avg_price*1e3)
    
    o.append("::")
    return o

def clean_orders(otype, symbol, orders):
    for o_id, o in myorders.items():
        if o["type"] == otype and o["symbol"] == symbol:
            hl.cancelOrder(o_id)

def get_bids_asks(symbol):
    res = hl.fetchOrderbook(symbol, full=True)
    if res is None:
        print ":: Could not fetch orderbook, apirate ??"
        return None, None
    asks, bids = res

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

def clear_console():
    print chr(27) + "[2J"
    print chr(27) + "[H"



hl = Havelock(Config)
hl.loadTransactionFile(Config.hl_history)

# if symbol not in portfolio, add it 
if sym not in hl.portfolio.symbols:
    hl.portfolio.addSymbol(sym)

synchronize(hl)

overview = 1
oput = o = []

idbook = {}

while True:
    # own orders + ids 
    tmp = hl.fetchOrders()
    if tmp is not None:
        myorders = dict((d["id"], d) for d in tmp \
                if d["symbol"] == sym)
        myids = [int(x[0]) for x in myorders.items()]
    
    # get current asks/bids
    bids, asks = get_bids_asks(sym)
    if bids is None or asks is None:
        continue
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

    # every 10 iterations, refresh - TODO inside a thread!?
    # (Portfolio, Balance, Transactions)
    if overview <= 0:
        overview = 10
        synchronize(hl)
    else:
        overview -= 1

    # general market information
    o = show_market_info(
        hl, bids, asks, sell_fee, sym, 
        myids=myids)
 
    # use them :)
    #print hl.transactions.getTransactions(sym, time.time() - (60*60*6 + 60*60*24), time.time())

    access_trade_section = True

    tmpl_spread_low = ":: spread too low {}{:.8f} BTC ({:.2%}) - waiting..."
    if spread < fee:
        o.append("::")
        o.append(tmpl_spread_low.format("", fee, sell_fee))
        access_trade_section = False

    elif spread/top_ask["price"] < min_spread:
        o.append("::")
        o.append(tmpl_spread_low.format("may bid from: ", 
                   top_ask["price"] - top_ask["price"] * min_spread, 
                   min_spread))
        access_trade_section = False 

    
    if not access_trade_section or DO_NOT_TRADE:
        if CLEAR_CONSOLE: clear_console()
        print "\n".join(o)
        continue 

    bal = get_balance(hl, sym, (time.time()-STARTTIME)/60./60.)
    o += [":: from start:"]
    o += [":: " + str(bal)]


    #### TRADE SECTION
    ############################################################################
    # check range to second (bid)
    pre = ":: too much difference in price to second"
    if top_bid["id"] in myids and \
            second_bid["price"] < top_bid["price"] - min_step and \
            not DO_NOT_TRADE:

        o.append("{} ({:.8f}) in bid order - canceling!". \
            format(pre, bid_price - second_bid["price"]))
        hl.cancelOrder(top_bid["id"])
        bid_price = second_bid["price"] + min_step

    # check range to second (ask)
    if top_ask["id"] in myids and \
            second_ask["price"] > top_ask["price"] + min_step and \
            not DO_NOT_TRADE:

        o.append("{} ({:.8f}) in ask order - canceling!". \
            format(pre, second_ask["price"] - ask_price))
        hl.cancelOrder(top_ask["id"])
        ask_price = second_ask["price"] - min_step

    # check if top in bid
    if top_bid["id"] not in myids and not DO_NOT_TRADE:
        amount = random.randint(*MIN_MAX_BUY)
        
        o.append(":: Placing bid order:")
        o.append(":: - delete old ")
        clean_orders("bid", sym, myorders)
        o.append(":: - create order ({} @ {} = {})". \
                format(amount, bid_price, amount*bid_price))

        if amount + bal["amount"] > TRADEVOLUME:
            o.append(":: {}+{}>{} -> buy boundary reached".format(amount, bal["amount"], TRADEVOLUME))
        else:
            hl.createOrder(sym, "buy", bid_price, amount)
    
    # check if top in ask:
    if top_ask["id"] not in myids and not DO_NOT_TRADE:
        amount = random.randint(*MIN_MAX_SELL)
        o.append(":: Placing ask order:")
        o.append(":: - delete old ")
        clean_orders("ask", sym, myorders)
        o.append(":: - create order ({} @ {} = {})". \
                format(amount, ask_price, amount*ask_price))
        
        if -amount + bal["amount"] < -TRADEVOLUME:
            o.append(":: -{}+{}<-{} -> sell boundary reached".format(amount, bal["amount"], TRADEVOLUME))
        else:
            hl.createOrder(sym, "sell", ask_price, amount)



    if CLEAR_CONSOLE: 
        clear_console()
    print "\n".join(o)

    



