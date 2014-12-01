import sys, os
import argparse

from classes import Havelock
from classes import Bitcoin

from config import Config
from utils import get_console_size

cmdline_parse = cp = \
    argparse.ArgumentParser(
            description="BTC.de and Havelock portfolio manager",
            epilog="Blaaaaa.......")

cp.add_argument("-B", "--btcde-csv-file", type=str, 
        default=Config.btc_de_history,
        help="Bitcoin.de transaction log / history")
cp.add_argument("--btcde-api-key", type=str, 
        default=Config.btc_de_api_key,
        help="The API key to be used for bitcoin.de")

cp.add_argument("-H", "--havelock-csv-file", type=str, 
        default=Config.hl_history,
        help="Havelock transaction log / history")
cp.add_argument("--havelock-api-key", type=str, 
        default=Config.hl_api_key,
        help="The API key to be used for Havelock")

cp.add_argument("--btc2eur", type=float, default=None,
        help="Force an exchange rate btc-to-eur for calculations")

args = cp.parse_args()

bitcoin = Bitcoin(Config)
havelock = Havelock(Config)

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
 


while 1:
    # update transactions
    havelock.fetchTransactions()
    # get current prices
    havelock.fetchPortfolio()
    
    # fetch btc.de data, if available
    if bitcoin.fetchData() == 0.0 and args.btc2eur is not None:
        bitcoin.btc2eur = args.btc2eur


    # some fancy output
    d = get_console_size()
    havelock.printDetails(full=False, btc2eur=bitcoin.btc2eur, width=d["width"])
    havelockBalance = havelock.getBalance()
    havelock.store()
    
    print 

    bitcoin.printDetails(full=False)
    
    print 

    bitcoinBalance = bitcoin.getBalance()

    print "Summary:"
    print "------------------------------"
    sumBtc = bitcoinBalance + havelockBalance
    sumEur = bitcoin.exchange(sumBtc)
    print "Total sum: {:.8f} BTC ({:.2f} EUR)".format(sumBtc, sumEur)
    invest = bitcoin.getInvest()
    print "Total sum of invest: {:.2f} EUR".format(invest)
    print "in sum your profit is: {:.2f} EUR".format(sumEur + invest)
    break

    time.sleep(10)


"""
# debug win / loss shit
data = havelock.getActivity()
cnt = 0
data2 = []
for (ts, balance) in data:
    data2.append((cnt, balance))
    cnt +=1

data3 = havelock.getData("B.MINE")
data4 = havelock.getData("AMHASH1")
data5 = havelock.getData("SCRYPT")
data6 = havelock.getData("PETA")

import numpy as np
import matplotlib.pyplot as plot

fig = plot.figure()
ax = fig.add_subplot(111)
(xes, yes) = zip(*data3)
ax.plot(xes, yes, 'b-')
(xes, yes) = zip(*data4)
ax.plot(xes, yes, 'r-')
(xes, yes) = zip(*data5)
ax.plot(xes, yes, 'k-')
(xes, yes) = zip(*data6)
ax.plot(xes, yes, 'y-')
plot.show()"""

