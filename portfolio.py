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

args = cp.parse_args()

bitcoin = Bitcoin(Config)
havelock = Havelock(Config)

bitcoinInfo = Info()
rates = Rates()

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
 
fn = args.rate_file
if os.path.exists(fn) and os.path.isfile(fn):
    rates.load(fn)
else:
    print "[-] no rate file found..."

# get bitcoin infos
bitcoinInfo.update()

# update transactions
havelock.fetchTransactions()
# get current prices
havelock.fetchPortfolio()
# get current Balance
havelock.fetchBalance()

# fetch btc.de data, if available
r = bitcoin.fetchData()
if r is None and args.btc2eur is not None:
    bitcoin.btc2eur = args.btc2eur

# set rates if needed
rates.addRate("BITCOIN", r)
for (name, rate) in havelock.currentPrices.items():
    rates.addRate(name, rate)

# store new data back
havelock.store(Config.hl_history)
bitcoin.store(Config.btc_de_history)
if rates is not None:
    rates.store(args.rate_file)

# handle only transactions starting from now back for 'args.secs_history' seconds
if args.secs_history is not None:
    havelock.setStartDate(time.time()-(int(args.secs_history)))
    havelock.setEndDate(time.time())


havelockBalance = havelock.getBalance()
bitcoinBalance = bitcoin.getBalance()
sumBtc = bitcoinBalance + havelockBalance
sumEur = bitcoin.exchange(sumBtc)
invest = bitcoin.getInvest()

# maybe we want just a plain output
if args.plain:
    havelock.plain()
    bitcoin.plain()
    print "[Sum]\ninvest:{:0.3f},sumBtc:{:0.3f},sumEur:{:0.3f},profit:{:0.3f}".format(invest, sumBtc, sumEur, sumEur+invest)
    sys.exit(0)

print "Details:"
console_width = get_console_size()["width"]
print "-" * console_width
fmts =   ["s", "d", ".2f", "g", "g"]
header = ["Next diff change at", "Next diff change in (d)",  
           "Diff change (%)", "current Diff", "estimated Diff"]
colwidth = (console_width / len(header)) - 3
fill = " | "       
print fill.join("{:>{}s}".format(h, colwidth) \
    for f, h in zip(fmts, header))

ndc = bitcoinInfo.getNextDifficultyChangeAt()
ndcStr = datetime.datetime.fromtimestamp(ndc).strftime('%Y-%m-%d')
current = int(time.time())
ndcDays = int(math.ceil((ndc - current) / float(60*60*24)))
currentDiff = bitcoinInfo.getDifficulty()
estimatedDiff = bitcoinInfo.getDifficultyEstimate()
data = [ndcStr, ndcDays, bitcoinInfo.getNextDifficultyChange(), currentDiff, estimatedDiff]
print fill.join("{0:>{1}{2}}".format(d, colwidth, f) \
    for f, d in zip(fmts, data))

print "-" * get_console_size()["width"]

# some fancy output
havelock.printPortfolio(btc2eur=bitcoin.btc2eur, allSymbols=args.show_all)
bitcoin.printBitcoin()

havelock.printDetails(full=False, btc2eur=bitcoin.btc2eur)

print "Summary:"
print "-" * get_console_size()["width"]
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Havelock: ", havelockBalance, bitcoin.exchange(havelockBalance))
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Bitcoin: ", bitcoinBalance, bitcoin.exchange(bitcoinBalance))
print "-" * get_console_size()["width"]
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Total Balance: ", sumBtc,sumEur)
print "{:<30s} | {:30s} | {:>25.2f} EUR |".format("Total sum of investment: ", "", invest)
print "-" * get_console_size()["width"]
print "{:<30s} | {:30s} | {:>25.2f} EUR |".format("Total profit: ", "", sumEur + invest)
print "-" * get_console_size()["width"]



