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

def show_options():
    print "options:"
    print "(s)ell shares"
    print "(a)uto sell shares"
    print "(c)ancel sell"
    print "(q)uit"
    print "(r)efresh"

if len(sys.argv) < 2:
    print "please support symbol to sell"
    sys.exit(0)

hl = Havelock(Config)
sym = sys.argv[1]
hl.portfolio.addSymbol(sym)
hl.loadTransactionFile(Config.hl_history)

auto_sell = None

while 1:
    orders = hl.fetchOrders()
    if orders is None:
        time.sleep(5)
        continue

    hl.fetchBalance()
    cash = hl.havelockBalanceAvailable 
    if cash is None:
        time.sleep(5)
        continue

    shares = hl.portfolio.getSymbol(sym).getShareQuantity()
    if shares is None:
        time.sleep(5)
        continue

    myorders = dict((int(d["id"]), d) for d in orders)
    r = hl.fetchOrderbook(sym, full=True)
    if r is None:
        time.sleep(5)
        continue
    (asks, bids) = r

    asks = [{"price": float(d["price"]), 
             "amount": int(d["amount"]), 
             "id": int(d["id"])} for d in asks.values()]
        
    bids = [{"price": float(d["price"]), 
             "amount": int(d["amount"]), 
             "id": int(d["id"])} for d in bids.values()]

    asks.sort(key=lambda o: o["price"])
    bids.sort(reverse=True, key=lambda o: o["price"])
    ask_ids = [x["id"] for x in asks]
    print "market:"
    print "   {:41s} ||   {:38s}".format("asks", "bids")
    for i in range(10):
        ap = asks[i]["price"]
        aa = asks[i]["amount"]
        av = aa*ap
        amark = "*" if asks[i]["id"] in myorders.keys() else " "
        bp = bids[i]["price"]
        ba = bids[i]["amount"]
        bv = ba*bp
        bmark = "*" if bids[i]["id"] in myorders.keys() else " "
        print "{} {:<010g} BTC | # {:<6d} | {:<010g} BTC ||{} {:<010g} BTC | # {:<6d} | {:<010g} BTC".format(
                amark,
                ap, aa, av, 
                bmark,
                bp, ba, bv)

    if auto_sell is not None:
        print "AUTOSELL ACTIVE!"
        (ids, amount, price, step, current) = auto_sell
        print auto_sell
        print "try to sell {:g} shares for a minimum price of {:g} BTC / share".format(amount, price)
        top_sell = asks[0]
        if len(ids) == 0:
            # place bid (\TODO: step
            if top_sell["price"] < price:
                # smallest price is lower than my minimum, create single order
                print "create single order"
                qty = min(amount, step)
                sid = hl.createOrder(sym, "sell", price, qty)
                auto_sell = ([sid["id"]], amount, price, step, qty)
                continue
            else:
                print "create the cheapest order!" 
                np = top_sell["price"] - 1e-8
                qty = min(amount, step)
                sid = hl.createOrder(sym, "sell", np, qty)
                auto_sell = ([sid["id"]], amount, price, step, qty)
                continue
        else: 
            sid = ids[0] 
            if not sid in ask_ids:
                bal = amount - current
                if bal <= 0:
                    print "all shares sold, finish auto sell"
                    auto_sell = None
                    continue
                else:
                    print "start from beginning"
                    auto_sell = ([], bal, price, step, 0)
                    continue
            else:
                # update current and amount
                order = myorders[sid]
                remain = int(order["remaining"])
                print "checking current amount"
                if remain != current:
                    diff = current - remain
                    amount -= diff
                    current = remain
                    auto_sell = ([sid], amount, price, step, current)
                    print auto_sell

            if top_sell["id"] == sid:
                second_sell = asks[1]
                diff = second_sell["price"] - top_sell["price"]
                print "order active and lowest one, check diff {:g}".format(diff)
                if diff > 1e-8:
                    print "diff is bigger, cancel sell"
                    hl.cancelOrder(top_sell["id"])
                    np = second_sell["price"] - 1e-8
                    qty = min(amount, step)
                    sid = hl.createOrder(sym, "sell", np, qty)
                    auto_sell = ([sid["id"]], amount, price, step, qty)
                    continue

                time.sleep(10)
                continue
            else:
                if top_sell["price"] < price:
                    print "i can't go cheaper, sleeping"
                    time.sleep(10)
                    continue
                else:
                    # cancel already placed ask
                    print "go cheaper!"
                    hl.cancelOrder(sid)
                    np = top_sell["price"] - 1e-8
                    qty = min(amount, step)
                    sid = hl.createOrder(sym, "sell", np, qty)
                    auto_sell = ([sid["id"]], amount, price, step, qty)
                    continue

    while 1:
        show_options()

        ri = raw_input("your option: ")

        if ri == "q":
            sys.exit(0)

        elif ri == "r":
            break

        elif ri == "c":
            print "your asks:"
            for o_id, o in myorders.items():
                if o["symbol"] != sym:
                    continue
                print "({}): {} shares @ {}".format(o_id, o["remaining"], o["price"])
            idx = raw_input("select id: ")
            print idx
            if not idx:
                break
            hl.cancelOrder(idx)
            break

        elif ri == "s":
            amount = int(raw_input("shares to sell: "))
            price = float(raw_input("price per share: "))
            value = amount * price
            answer = raw_input("sell {} shares @ {} (total: {} BTC)? (y/n): ".format(amount, price, value))
            if answer == "y":
                hl.createOrder(sym, "sell", price, amount)
            break

        elif ri == "a":
            amount = int(raw_input("total shares to sell: "))
            price = float(raw_input("minimum price to sell one share for: "))
            step = int(raw_input("maximum number for one sell order: "))
            answer = raw_input("is it ok to sell {} shares for a total of {} BTC? (y/n)".format(amount, (price*amount)))
            if answer == "y":
                auto_sell = ([], amount, price, step, 0)
            else:
                auto_sell = None
            break;


        else:
            print "unknown command"
            continue




