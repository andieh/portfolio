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
 


# update transactions
havelock.fetchTransactions()
# get current prices
havelock.fetchPortfolio()
# get current Balance
havelock.fetchBalance()

# fetch btc.de data, if available
if bitcoin.fetchData() == 0.0 and args.btc2eur is not None:
    bitcoin.btc2eur = args.btc2eur


# some fancy output
havelock.printPortfolio(btc2eur=bitcoin.btc2eur)
havelock.store(Config.hl_history)

bitcoin.printBitcoin()
bitcoin.store(Config.btc_de_history)

havelock.printDetails(full=False, btc2eur=bitcoin.btc2eur)
havelockBalance = havelock.getBalance()
bitcoinBalance = bitcoin.getBalance()

print "Summary:"
print "-" * get_console_size()["width"]
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Havelock: ", havelockBalance, bitcoin.exchange(havelockBalance))
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Bitcoin: ", bitcoinBalance, bitcoin.exchange(bitcoinBalance))
print "-" * get_console_size()["width"]
sumBtc = bitcoinBalance + havelockBalance
sumEur = bitcoin.exchange(sumBtc)
print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("Total Balance: ", sumBtc,sumEur)
invest = bitcoin.getInvest()
print "{:<30s} | {:30s} | {:>25.2f} EUR |".format("Total sum of investment: ", "", invest)
print "-" * get_console_size()["width"]
print "{:<30s} | {:30s} | {:>25.2f} EUR |".format("Total profit: ", "", sumEur + invest)
print "-" * get_console_size()["width"]



