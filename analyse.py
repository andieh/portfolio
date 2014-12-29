import sys, os
import argparse
import time
import datetime

from classes import Havelock
from classes import Bitcoin
from classes import Rates

from config import Config
from utils import get_console_size

import numpy as np
import matplotlib.pyplot as plot
import matplotlib.dates as md

cmdline_parse = cp = \
    argparse.ArgumentParser(
            description="BTC.de and Havelock portfolio analyser",
            epilog="Blaaaaa.......")

cp.add_argument("-B", "--btcde-csv-file", type=str, 
        default=Config.btc_de_history,
        help="Bitcoin.de transaction log / history")

cp.add_argument("-H", "--havelock-csv-file", type=str, 
        default=Config.hl_history,
        help="Havelock transaction log / history")

cp.add_argument("-S", "--start-time", type=str,
        default="2010-01-01",
        help="Time to start from in form %Y-%M-%D")

cp.add_argument("-X", "--symbol", type=str,
        help="show one single symbol only")

args = cp.parse_args()

bitcoin = Bitcoin(Config)
havelock = Havelock(Config)
rates = Rates()
rates.load("rates.prf")

fn = args.btcde_csv_file
if os.path.exists(fn) and os.path.isfile(fn):
    bitcoin.loadTransactionFile(fn)
else:
    print "[-] no bitcoin.de transaction history found..."

fn = args.havelock_csv_file
if os.path.exists(fn) and os.path.isfile(fn):
    havelock.loadTransactionFile(fn)
else:
    print "[-] no havelock transaction history found..."

#debug a single symbol
if args.symbol is not None:
    print "analyse symbol {:s}".format(args.symbol)

    s = havelock.portfolio.getSymbol(args.symbol)
    #if s is None:
    #    print "failed to get data for that symbol"
    #    sys.exit(1)

    if not rates.hasSymbol(args.symbol):
        print "symbol not found in ratefile!"
        sys.exit(1)

    minTs = rates.getMinTimestamp(args.symbol)
    maxTs = rates.getMaxTimestamp(args.symbol)
    diff = maxTs - minTs
    steps = diff / 50

    timestamps = []
    r = []
    for ts in range(minTs, maxTs, steps):
        timestamps.append(datetime.datetime.fromtimestamp(ts))
        r.append(rates.getRate(args.symbol, ts))

    fig = plot.figure()
    ax = fig.add_subplot(111)
    plot.xticks( rotation=25 )
    xfmt = md.DateFormatter('%Y-%m-%d %H:%M:%S')
    ax.xaxis.set_major_formatter(xfmt)

    ax.plot(timestamps, r, 'ks-', label="Rate")
    ax.legend(loc=1)

    if args.symbol == "BITCOIN":
        plot.show()
        sys.exit(0)

    d = s.getDividend()
    timestampsDividend = []
    dividends = []
    ax2 = ax.twinx()
    for dividend in d:
        ts = dividend.getTimestamp()
        timestampsDividend.append(datetime.datetime.fromtimestamp(ts))
        havelock.setEndDate(ts)
        qt = s.getShareQuantity()
        div = dividend.getAmount()
        perShare = div / float(qt)
        #dividends.append(dividend.getAmount())
        #print "{:d} shares, dividend {:f}, per Share {:f}".format(qt, div, perShare)
        dividends.append(perShare)
        ax2.axvline(x=timestampsDividend[-1], ymin=0, ymax=1)
    ax2.plot(timestampsDividend, dividends, 'bs-', label="Dividend per Share")
    ax2.legend(loc=2)


    plot.show()

    sys.exit(0)

# debug win / loss shit
# all symbols 
analyse = havelock.portfolio.getSymbols().keys()

dates = havelock.transactions.getTimestamps()
des = []

yes = {}
xes = {}
dxes = {}
for sym in analyse:
    yes[sym] = []
    xes[sym] = []
    dxes[sym] = []

btcX = []
btcY = []
wins = []
bwins = []
btcCount = []

cnt = 0
symbols = havelock.portfolio.getSymbols().values()

depotMode = None
oldDepositValue = 0.0
oldWithdrawValue = 0.0
reduceBtc=0.0


for d in dates:
    ds = datetime.datetime.fromtimestamp(d)
    des.append(ds)
    #print "{:d} transactions until {:s}:".format(cnt, ds.strftime("%Y-%m-%d %H:%M:%s"))
    havelock.setEndDate(d)

    deposit = havelock.transactions.getDepositAmount()
    if deposit != oldDepositValue:
        reduceBtc = deposit-oldDepositValue
        #print "{:d} entering deposit mode, deposit {:f} btc to havelock".format(cnt, reduceBtc)
        oldDepositValue = deposit
        depotMode = True

    bitcoin.setEndDate(d)
    val = 0.0
    por = 0.0
    for sym in symbols:
        name = sym.getName()
        if name not in analyse:
            continue
        amount = sym.getShareQuantity()
        rate = rates.getRate(name, d)
        book = sym.getBookAmount()
        div = sym.getDividendAmount()
        cur = amount * rate
        win = cur - book + div
        val += win
        por += cur
            
        if amount != 0:
            yes[name].append(win)
            xes[name].append(d)
            dxes[name].append(ds)

    withdraw = bitcoin.transactions.getWithdrawAmount()
    if withdraw != oldWithdrawValue:
        diff = withdraw-oldWithdrawValue
        #print "{:d} withdraw {:f} btc from bitcoin.de".format(cnt, diff)
        oldWithdrawValue = withdraw
        if (reduceBtc - diff) < 0.0001 and (reduceBtc - diff) > -0.0001:
            depotMode = False
            reduceBtc = 0.0


    btc = rates.getRate("BITCOIN", d)
    btcBalance = bitcoin.getBalance()
    btcCount.append(btcBalance+havelock.getBalance(False)+por-reduceBtc)
    invest = bitcoin.getInvest()
    bwin = ((btcBalance-reduceBtc) * btc) + (por * btc) + invest
    bwins.append(bwin)
    btcX.append(ds)
    btcY.append(btc)
    wins.append(val) #havelock.getBalance(False) + val)
    cnt += 1
ts = int(time.mktime(datetime.datetime.strptime(args.start_time, "%Y-%m-%d").timetuple())) 

fig = plot.figure()
ax = fig.add_subplot(121)
colors = ["b-", "g-", "r-", "c-", "m-", "y-", "k-"]
ci = 0
plot.xticks( rotation=25 )
xfmt = md.DateFormatter('%Y-%m-%d %H:%M:%S')
ax.xaxis.set_major_formatter(xfmt)
for sym in analyse:
    start = -1
    for (i, x) in enumerate(xes[sym]):
        if x > ts:
            start = i
            break
    if start != -1:
        ax.plot(dxes[sym][start:], yes[sym][start:], colors[ci], label=sym)
        ci = (ci+1)%len(colors)

start = 0
for (i,x) in enumerate(dates):
    if x > ts:
        start = i
        break
ax.plot(des[start:], wins[start:], 'ko-', label='win')
ax.legend(loc=3)

ax_1 = ax.twinx()
ax_1.plot(des[start:], btcCount[start:], 'yx-', label="BTCs")
ax_1.legend(loc=4)

ax2 = fig.add_subplot(122)#ax.twinx()
ax2.xaxis.set_major_formatter(xfmt)
plot.xticks( rotation=25 )
ax2.plot(btcX[start:], btcY[start:], 'bs-', label="BTC price")
ax2.legend(loc=3)

ax3 = ax2.twinx()
ax3.plot(btcX[start:], bwins[start:], 'rs-', label="total win")
ax3.legend(loc=1)

plot.show()

sys.exit(0)

