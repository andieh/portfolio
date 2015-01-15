import sys, os
import argparse
import math
import time, datetime
import tty

from classes import Havelock
from classes import Bitcoin
from classes import Info
from classes import Rates 

from config import Config
from utils import get_console_size

cmdline_parse = cp = \
    argparse.ArgumentParser(
            description="Havelock transaction viewer",
            epilog="Blaaaaa.......")

cp.add_argument("-H", "--havelock-csv-file", type=str, 
        default=Config.hl_history,
        help="Havelock transaction log / history")
args = cp.parse_args()

havelock = Havelock(Config)
fn = args.havelock_csv_file
if os.path.exists(fn) and os.path.isfile(fn):
    havelock.loadTransactionFile(fn)
else:
    print "[-] no havelock transaction history found..."
 
trans = havelock.transactions.transactions
trans.reverse()

symbols = havelock.transactions.getSymbols()
symbols = ["All"] + symbols
sym = 0

types = ["All", "buy", "sell", "fee", "dividend"] 
typ = 0

entries = [[x.getTimestamp(), \
            x.getType(), \
            x.getQuantity(), \
            x.getPrice(), \
            x.getSymbol(), \
            x.getAmount()] \
           for x in trans\
           if x.getType() != "escrow"
          ]

while True:

    console_width = get_console_size()["width"]

    if sym == 0:
        use = entries
    else:
        use = [x for x in entries if x[4] == symbols[sym]]

    if typ != 0:
        use = [x for x in use if x[1] == types[typ]]


    print "-" * console_width
    print "show: symbol: {}, type: {}".format(symbols[sym], types[typ])
    print "-" * console_width

    fmts =    [ "s", "s", "d", ".8f", 
                "s", ".8f", ".8f", ".8f"]
    header =  [ "Date/Time", "Type", "Qty", "Price", 
                "Symbol", "Credit", "Debit", "Balance"]


    print "-" * console_width
    colwidth = (console_width / len(header)) - 3
    fill = " | "       
    print fill.join("{:>{}s}".format(h, colwidth) \
            for f, h in zip(fmts, header))

    tty.setcbreak(sys.stdin)
    print "-" * console_width
    h = get_console_size()["height"]-12
    lines = 0
    for t in use[:h]:
        ts = datetime.datetime.fromtimestamp(t[0]).strftime('%Y-%m-%d %H:%M:%S')
        data = [ts, t[1], t[2], t[3], t[4], t[5], 0.0, 0.0]
        
        print fill.join("{0:>{1}{2}}".format(d, colwidth, f) \
                 for f, d in zip(fmts, data))
        lines += 1

    print "\n"*(h-lines)

    print "-" * console_width
    print "selection: ",
    for (i, s) in enumerate(symbols):
        print "({}) {} |".format(i,s),
        
    print "({}) All".format(len(symbols))
    print "commands: (q) Quit |",
    print "(t) change type",
    print

    print "-" * console_width

    i = ord(sys.stdin.read(1))
    if ord('q') == i:
        break
    elif i >= 48 and i <= 57:
        ind = i - 48
        try:
            print "selecting symbol {}".format(symbols[ind])
            sym = ind
        except:
            print "unknown selection"
            sym = 0
    elif ord('t') == i:
        typ = (typ+1)%len(types)
        print "selecting type {}".format(types[typ])
    else:
        print "unknown command ord {}".format(i)


print "goodbye"
