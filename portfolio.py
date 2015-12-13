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

cp.add_argument("-R", "--rate-file", type=str,
        default=Config.rate_file,
        help="File with rate for your symbols")

cp.add_argument("--btc2eur", type=float, default=None,
        help="Force an exchange rate btc-to-eur for calculations")

cp.add_argument("-p", "--plain", action="store_true",
        help="print data in plain format for parsing later")

cp.add_argument("-s", "--show-all", action="store_true",
        help="show all symbols in your portfolio", default=False)

cp.add_argument("-S", "--secs-history", 
        help="ignore all transactions older than seconds", default=None)

cp.add_argument("-w", "--wallet-balance",
        help="local wallet balance, not listed on installed plugins", default=Config.wallet_balance)

args = cp.parse_args()

bitcoin = Bitcoin(Config)
#havelock = Havelock(Config)

bitcoinInfo = Info()
rates = Rates()

fn = args.btcde_csv_file
if os.path.exists(fn) and os.path.isfile(fn):
    bitcoin.loadTransactionFile(fn)
else:
    print "[-] no bitcoin.de transaction history found..."

#fn = args.havelock_csv_file
#if os.path.exists(fn) and os.path.isfile(fn):
#    havelock.loadTransactionFile(fn)
#else:
#    print "[-] no havelock transaction history found..."
 
fn = args.rate_file
if os.path.exists(fn) and os.path.isfile(fn):
    rates.load(fn)
else:
    print "[-] no rate file found..."

# get bitcoin infos
bitcoinInfo.update()

"""
# update transactions
havelock.fetchTransactions()
# get current prices
havelock.fetchPortfolio()
# get current Balance
havelock.fetchBalance()
"""
# fetch btc.de data, if available
r = bitcoin.fetchData()
if r is None and args.btc2eur is not None:
    bitcoin.btc2eur = args.btc2eur

"""
# set rates if needed
rates.addRate("BITCOIN", r)
for (name, rate) in havelock.currentPrices.items():
    rates.addRate(name, rate)
"""

# store new data back
#havelock.store(Config.hl_history)
bitcoin.store(Config.btc_de_history)
if rates is not None:
    rates.store(args.rate_file)

## handle only transactions starting from now back for 'args.secs_history' seconds
#if args.secs_history is not None:
#    havelock.setStartDate(time.time()-(int(args.secs_history)))
#    havelock.setEndDate(time.time())


#havelockBalance = havelock.getBalance()
bitcoinBalance = bitcoin.getBalance()
wallet = Config.wallet_balance
sumBtc = bitcoinBalance + wallet # + havelockBalance
sumEur = bitcoin.exchange(sumBtc)
invest = bitcoin.getInvest()

# maybe we want just a plain output
if args.plain:
    #havelock.plain()
    bitcoin.plain()
    print "[Sum]\ninvest:{:0.3f},sumBtc:{:0.3f},sumEur:{:0.3f},profit:{:0.3f}".format(invest, sumBtc, sumEur, sumEur+invest)
    sys.exit(0)

# some fancy output
#havelock.printPortfolio(btc2eur=bitcoin.btc2eur, allSymbols=args.show_all)
bitcoin.printBitcoin()

#havelock.printDetails(full=False, btc2eur=bitcoin.btc2eur)
print "Summary:"
print "-" * get_console_size()["width"]
#print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Havelock: ", havelockBalance, bitcoin.exchange(havelockBalance))
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Bitcoin: ", bitcoinBalance, bitcoin.exchange(bitcoinBalance))
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("local Wallet: ", wallet, bitcoin.exchange(wallet))
print "-" * get_console_size()["width"]
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Total Balance: ", sumBtc,sumEur)
print "{:<30s} | {:30s} | {:>25.2f} EUR |".format("Total sum of investment: ", "", invest)
print "-" * get_console_size()["width"]
print "{:<30s} | {:30s} | {:>25.2f} EUR |".format("Total profit: ", "", sumEur + invest)
print "-" * get_console_size()["width"]

analyse = [("3 Months", 3*31), \
        ("2 Months", 62), \
        ("1 Month", 31), \
        ("7 Days", 7)]

print "-" * get_console_size()["width"]
print " Time (days) |    Buy         |  EUR / BTC     |    Sell        |  EUR / BTC     |   Buy Now?"
print "-" * get_console_size()["width"]
for (label, days) in analyse:
    bTime = Bitcoin(Config)
    fn = args.btcde_csv_file
    bTime.loadTransactionFile(fn, days)
    bTime.btc2eur = bitcoin.btc2eur
    sumEur = bTime.exchange(bTime.getBalance())
    invest = bTime.getInvest()

    buys = bTime.transactions.getBuyQuantity()
    buyPrice = (bTime.transactions.getBuyAmount())
    if buys > 0:
        buyPerBtc = buyPrice / buys
    else:
        buyPrice = 0.0
    sellPrice = bTime.transactions.getSellAmount()
    sells = bTime.transactions.getSellQuantity()
    if sells > 0:
        sellPerBtc = sellPrice / sells
    else:
        sellPerBtc = 0.0
    sums = buys - sells
    sumPrice = sellPrice - buyPrice

    profit = bTime.exchange(buys) - buyPrice

    print " {:<11d} | {:>10.2f} BTC | {:>10.2f} EUR | {:>10.2f} BTC | {:>10.2f} EUR |  {:>10.2f} EUR".format(days, buys, buyPerBtc, sells, sellPerBtc, profit)
    print "-" * get_console_size()["width"]
