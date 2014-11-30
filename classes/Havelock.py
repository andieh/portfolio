import requests
import json

from Transactions import *
from Portfolio import *

class Havelock:
    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.currentPrices = {}
        self.transactions = Transactions()
        self.portfolio = Portfolio()

    def fetchData(self, dataType):
        payload = {'key': self.apiKey}
        if dataType == "portfolio" or "balance":
            url = "https://www.havelockinvestments.com/r/%s" % dataType
        elif dataType == "transactions":
            url = "https://www.havelockinvestments.com/r/%s" % dataType
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
            if not __debug__: print "fetched lastprice %f for symbol %s" % (self.currentPrices[d["symbol"]], d["symbol"])
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
        print "havelock balance: %f BTC" % self.havelockBalance

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

        
    def printDetails(self, full=True):
        print "Havelock Account Details:" 
        print "------------------------------"
        wit = self.transactions.getWithdrawAmount()
        dep = self.transactions.getDepositAmount()
        if full:
            print "total buys:\t\t\t%d shares" % self.transactions.getBuyQuantity()
            print "total sells:\t\t\t%d shares" % self.transactions.getSellQuantity()
            print "total dividend received:\t%f BTC" % self.transactions.getDividendAmount()
            print "total withdraw:\t\t\t%f BTC" % wit
            print "total deposit:\t\t\t%f BTC" % dep
            print "total fees:\t\t\t%f BTC" % self.transactions.getFeeAmount()
            print "------------------------------"

        self.printPortfolio()
        print "------------------------------"
        bal = self.transactions.getBalance()
        print "current balance:\t%f BTC" % bal
        por = self.portfolio.getCurrentValue()
        print "portfolio value:\t%f BTC" % por
        print "in sum your profit is:\t%f BTC" % (wit + por + bal - dep)

    def printPortfolio(self):
        print "this portfolio saw %d symbols:" % len(self.portfolio.symbols)
        for s in self.portfolio.symbols:
            t = self.portfolio.symbols[s]
            print "%s: %s%% (overall: %s%%)" % ('{:<7}'.format(s), '{:>+6.2f}'.format(self.portfolio.getTrend(s)), '{:>+6.2f}'.format(self.portfolio.getOverallTrend(s)))
            print "\t buys: %d, sells: %d, sum: %d, value %f BTC" % (t.getBuyQuantity(), t.getSellQuantity(), t.getShareQuantity(), self.portfolio.getCurrentValue(s))
            print "\t total dividend: %f BTC, fees: %f BTC" % (t.getDividendAmount(), t.getFeeAmount())
            print "\t mean price: %f BTC, current price: %f BTC" % (t.getMeanPrice(), self.portfolio.getCurrentPrice(s))

    def store(self):
        content = "%s\n" % Transaction().getHeader()
        for t in self.transactions.transactions:
            content += "%s\n" % t

        f = open("test.csv", "w")
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
            portfolio = Portfolio()
            prices = {}
            for s in allTrans.getSymbols():
                portfolio.addTransactions(allTrans.getTransactions(symbol=s), s)
                prices[s] = portfolio.symbols[s].getLastPrice()
            portfolio.setCurrentPrices(prices)
            val = portfolio.getCurrentValue()

            ret.append((t, bal+val+wit-dep))


        return ret

