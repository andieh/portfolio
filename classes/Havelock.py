#-*- coding: utf-8 -*-
import requests
import json

from Transactions import *
from Portfolio import *

try:
    from utils import get_console_size
except:
    print "can't find utils class, maybe running this script standalone?"

class Havelock:
    def __init__(self, conf):
        self.conf = conf
        self.apiKey = self.conf.hl_api_key
        self.currentPrices = {}
        self.transactions = Transactions()
        self.portfolio = Portfolio(self.conf.epsilon)

    def fetchData(self, dataType):
        payload = {'key': self.apiKey}
        if dataType == "portfolio" or "balance":
            url = "https://www.havelockinvestments.com/r/{:s}".format(dataType)
        elif dataType == "transactions":
            url = "https://www.havelockinvestments.com/r/{:s}".format(dataType)
            payload["limit"] = 300
            # add sinceid to payload
        else:
            print "data Type not known!" 
            return None

        try:
            r = requests.post(url, data=payload)
            j = json.loads(r.text)
            if j["status"] != "ok":
                print "failed to fetch Havelock Portfolio!"
                return None

        except requests.exceptions.ConnectionError:
            print "failed to resolve havelockinvestments.com!"
            return None
        except ValueError:
            print "failed to get data from havelock"
            return None

        return j

    def fetchPortfolio(self):
        j = self.fetchData("portfolio")
        if j is None:
            return None

        portfolio = j["portfolio"]
        ts = time.time()
        tes = []
        for d in portfolio:
            self.currentPrices[d["symbol"]] = float(d["lastprice"])
            if not __debug__: print "fetched lastprice {} for symbol {}".format(
                    (self.currentPrices[d["symbol"]], d["symbol"]))
            t = Transaction()
            t.type = "rate"
            t.symbol = d["symbol"]
            t.price = float(d["lastprice"])
            t.ts = int(ts)
            tes.append(t)
        self.portfolio.setCurrentPrices(self.currentPrices)
        self.transactions.addTransactions(tes)
        self.portfolio.addTransactions(tes)

    def fetchBalance(self):
        """ get balance """
        print "get balance from havelock"
        j = self.fetchData("balance")
        if j is None:
            return None

        balance = j["balance"]
        self.havelockBalance = float(balance["balance"])
        self.havelockBalanceAvailable = float(balance["balanceavailable"])
        print "havelock balance: {:f} BTC".format(self.havelockBalance)

    def fetchTransactions(self):
        """ get history """
        j = self.fetchData("transactions")
        if j is None:
            return None

        transactions = j["transactions"]
        ts = []
        for tr in transactions:
            t = Transaction()
            if t.parse(tr):
                ts.append(t)
        new = self.transactions.getNewTransactions(ts)
        self.transactions.addTransactions(new)
        self.portfolio.addTransactions(new)

    def loadTransactionFile(self, filename):
        f = open(filename, "r")
        raw = f.read()
        f.close()

        for line in raw.split("\n"):
            self.transactions.addTransaction(line)

        self.buildPortfolio()

    def buildPortfolio(self):
        for s in self.transactions.getSymbols():
            self.portfolio.addTransactions(self.transactions.getTransactions(symbol=s), s)
    
    def getBalance(self, includePortfolio=True):
        bal = self.transactions.getBalance()
        if not includePortfolio:
            return bal

        por = self.portfolio.getCurrentValue()
        return (bal+por)

        
    def printDetails(self, full=True, btc2eur=None):

        btc2eur = btc2eur or 1.0

        print "Havelock Account Details:" 
        print "-" * get_console_size()["width"]
        wit = self.transactions.getWithdrawAmount()
        dep = self.transactions.getDepositAmount()
        if full:
            print "total buys:              {:>20d} shares".format(
                    self.transactions.getBuyQuantity())
            print "total sells:             {:>20d} shares".format(
                    self.transactions.getSellQuantity())
            print "total dividend received: {:>20f} BTC".format(
                    self.transactions.getDividendAmount())
            print "total withdraw:          {:>20f} BTC".format(wit)
            print "total deposit:           {:>20f} BTC".format(dep)
            print "total fees:              {:>20f} BTC".format(
                    self.transactions.getFeeAmount())
            print "-" * get_console_size()["width"]

            self.printPortfolio(btc2eur=btc2eur)
            print "-" * get_console_size()["width"]
        bal = self.transactions.getBalance()
        
        print "current balance:\t{:>29f} BTC".format(bal)
        por = self.portfolio.getCurrentValue()
        
        print "portfolio value:\t{:>29f} BTC".format(por)
        print "in sum your profit is:{:>31f} BTC".format(wit + por + bal - dep)
        print "-" * get_console_size()["width"]

    def printPortfolio(self, btc2eur=None):
        p = self.portfolio
        console_width = get_console_size()["width"]
        
        print "your portfolio:"
        print "-" * console_width


        fmts =    [".2f", "d", "s", ".3f", ".5f", ".5f", ".3f"]
        header =  ["Trend (%)", "Buys", "", "Market (B)", 
                   "Divs (B)", "Mean (B)", "Win (B)"]
   
        fmts2 =   [".2f", "d", "d", ".3f", ".5f", ".5f", ".2f"]
        header2 = ["Overall (%)", "Sells", "Sum", "Book (B)", 
                   "Fee (B)", "Cur (B)", "Win (E)"]
    
        colwidth = (console_width / len(header)) - 3
        fill = " | "       

        print fill.join("{:>{}s}".format(h, colwidth) \
                for f, h in zip(fmts, header))
        print fill.join("{:>{}s}".format(h, colwidth) \
                for f, h in zip(fmts, header2))

        for s in self.portfolio.symbols:
            t = p.symbols[s]
               
            print "-" * console_width
            _s = "{1:-^{0}}".format(console_width, "> " + s + " <")
            print _s[console_width/5:] + _s[:console_width/5]

            data =  [p.getTrend(s), t.getBuyQuantity(), "", 
                     p.getCurrentValue(s), t.getDividendAmount(), 
                     t.getMeanPrice(), p.getCurrentWin(s) ]

            data2 = [p.getOverallTrend(s), t.getSellQuantity(), 
                     t.getShareQuantity(), p.getBookValue(s), t.getFeeAmount(),
                     p.getCurrentPrice(s), p.getCurrentWin(s) * btc2eur] 

            print fill.join("{0:>{1}{2}}".format(d, colwidth, f) \
                     for f, d in zip(fmts, data))

            print fill.join("{0:>{1}{2}}".format(d, colwidth, f) \
                     for f, d in zip(fmts2, data2))

    def store(self, filename):
        content = "{:s}\n".format(Transaction().getHeader())
        for t in self.transactions.transactions:
            content += "{:s}\n".format(t)

        f = open(filename, "w")
        f.write(content)
        f.close()

    def getData(self, sym):
        s = self.portfolio.symbols[sym]

        ts = s.getTimestamps()
        ret = []
        for t in ts:
            tes = s.getTransactions(end=t)
            allTrans = Transactions()
            allTrans.addTransactions(tes)

            buys = allTrans.getBuyAmount()
            sells = allTrans.getSellAmount()
            dividend = allTrans.getDividendAmount()
            try:
                val = allTrans.getShareQuantity() * self.currentPrices[sym]
            except:
                val = allTrans.getShareQuantity() * s.getMeanPrice()


            ret.append((t, val+dividend+sells-buys))

        return ret

    def getActivity(self):
        # get all timestamps where something happens
        ts = self.transactions.getTimestamps()
        ret = []
        for t in ts:
            trans = self.transactions.getTransactions(end=t)
            allTrans = Transactions()
            allTrans.addTransactions(trans)

            bal = allTrans.getBalance()
            dep = allTrans.getDepositAmount()
            wit = allTrans.getWithdrawAmount()
            portfolio = Portfolio(self.conf.epsilon)
            prices = {}
            for s in allTrans.getSymbols():
                portfolio.addTransactions(allTrans.getTransactions(symbol=s), s)
                prices[s] = portfolio.symbols[s].getLastPrice()
            portfolio.setCurrentPrices(prices)
            val = portfolio.getCurrentValue()

            ret.append((t, bal+val+wit-dep))


        return ret


if __name__ == "__main__":
    # ugly, but only for testing puporse 
    import sys, os
    sys.path.append(os.path.dirname("../"))
    from config import Config

    havelock = Havelock(Config)

    if len(sys.argv) < 4:
        print "test this script with python2 Havelock.py <transactionfile> <symbol> <price>"
        sys.exit(1)
    
    havelock.loadTransactionFile(sys.argv[1])
    sym = sys.argv[2]
    print "watch symbol {:s}".format(sym)
    s = havelock.portfolio.getSymbol(sym)
    if s is None:
        print "symbol not found"
        sys.exit(1)
    havelock.portfolio.setCurrentPrices({sym : float(sys.argv[3])})

    print "total buy ({:d}): {:f}".format(s.getBuyQuantity(), s.getBuyAmount())
    print "total sell ({:d}): {:f}".format(s.getSellQuantity(), s.getSellAmount())
    print "total dividend: {:f}".format(s.getDividendAmount())
    print "total fee: {:f}".format(s.getFeeAmount())
    print "total escrow: {:f}".format(s.getEscrowAmount())
    print "mean price: {:f}, current price: {:f}".format(s.getMeanPrice(), havelock.portfolio.getCurrentPrice(sym))

    print 

    print "total book: {:f}".format(havelock.portfolio.getBookValue(sym))
    print "total value: {:f}".format(havelock.portfolio.getCurrentValue(sym))
    print "current win: {:f}".format(havelock.portfolio.getCurrentWin(sym))
    print "trend: {:f}%".format(havelock.portfolio.getTrend(sym))
    print "overall trend: {:f}%".format(havelock.portfolio.getOverallTrend(sym))

    print

    print "balance (with Portfolio): {:f}".format(havelock.getBalance())
    print "balance (with Portfolio): {:f}".format(havelock.getBalance(includePortfolio=False))
