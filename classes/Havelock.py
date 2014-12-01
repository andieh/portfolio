import requests
import json

from Transactions import *
from Portfolio import *

from utils import get_console_size

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

        
    def printDetails(self, full=True, btc2eur=None, width=None):
        print "Havelock Account Details:" 
        print "-" * get_console_size()["width"]
        wit = self.transactions.getWithdrawAmount()
        dep = self.transactions.getDepositAmount()
        if full:
            print "total buys:\t\t\t%d shares" % self.transactions.getBuyQuantity()
            print "total sells:\t\t\t%d shares" % self.transactions.getSellQuantity()
            print "total dividend received:\t%f BTC" % self.transactions.getDividendAmount()
            print "total withdraw:\t\t\t%f BTC" % wit
            print "total deposit:\t\t\t%f BTC" % dep
            print "total fees:\t\t\t%f BTC" % self.transactions.getFeeAmount()
            print "-" * get_console_size()["width"]

        self.printPortfolio(btc2eur=btc2eur, width=width)
        print "-" * get_console_size()["width"]
        bal = self.transactions.getBalance()
        
        print "current balance:\t%f BTC" % bal
        por = self.portfolio.getCurrentValue()
        
        print "portfolio value:\t%f BTC" % por
        print "in sum your profit is:\t%f BTC" % (wit + por + bal - dep)

    def printPortfolio(self, btc2eur=None, width=None):
        p = self.portfolio
        print "this portfolio saw {} symbols:".format(len(p.symbols))
        for s in self.portfolio.symbols:
            t = p.symbols[s]

            header =  ["  Trend (%)", " Buys", "   ", "Market Value (BTC)", "Dividends (BTC)", "Mean Price (BTC)", "Win (BTC)"]
            header2 = ["Overall (%)", "Sells", "Sum", "  Book Value (BTC)", "     Fees (BTC)", " Cur Price (BTC)", "Win (EUR)"]
        
            space, sep = 1, 1
            needed = max(sum(len(k) + space + sep for k in header), 
                         sum(len(k) + space + sep for k in header2))
            
            while needed < width:
                needed += len(header) * 2
                space += 1

            if needed > width:
                needed -= len(header) * 2
                space -= 1

            print
            print "{1:-^{0}}".format(needed, "> " + s + " <")
            
            fill = (" " * space) + "|" + (" " * space)
            print fill.join(header)
            print fill.join(header2)
            
            print "-" * needed 

            data =  [p.getTrend(s), t.getBuyQuantity(), None, 
                     p.getCurrentValue(s), t.getDividendAmount(), 
                     t.getMeanPrice(), p.getCurrentWin(s)]
            data2 = [p.getOverallTrend(s), t.getSellQuantity(), 
                     t.getShareQuantity(), None, t.getFeeAmount(),
                     p.getCurrentPrice(s), p.getCurrentWin(s) * btc2eur] 

            line_tmpl = fill.join(header).split("|")
            fill = " |"
            print fill.join("{:>{}.{}f}".format(d, len(t)-1, self.conf.d_eps) \
                    if d is not None else (" " * (len(t)-1)) \
                        for t, d in zip(line_tmpl, data))
            print fill.join("{:>{}.{}f}".format(d, len(t)-1, self.conf.d_eps) \
                    if d is not None else (" " * (len(t)-1)) \
                        for t, d in zip(line_tmpl, data2))

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
            portfolio = Portfolio(self.conf.epsilon)
            prices = {}
            for s in allTrans.getSymbols():
                portfolio.addTransactions(allTrans.getTransactions(symbol=s), s)
                prices[s] = portfolio.symbols[s].getLastPrice()
            portfolio.setCurrentPrices(prices)
            val = portfolio.getCurrentValue()

            ret.append((t, bal+val+wit-dep))


        return ret

