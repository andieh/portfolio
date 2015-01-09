#-*- coding: utf-8 -*-
import requests
import json

from Transactions import *
from Portfolio import *
import time

# set maximum api rate
# this is limited by havelock
# calls / 600
MAX_API_RATE_CALLS = 300

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
        self.havelockBalance = None
        self.havelockBalanceAvailable = None
        self.apiRate = [] # calls in the last 600 s

    def checkApiRate(self):
        self.apiRate.append(time.time())
        self.apiRate = [x for x in self.apiRate if x > (time.time() - 600)]
        l = len(self.apiRate)
        if l < 2:
            return

        diff = self.apiRate[-1] - self.apiRate[0]
        current = diff / 600.0
        ok = MAX_API_RATE_CALLS / 600.0

        if current > (0.9*ok):
            time.sleep(ok)

        if l > (0.8 * MAX_API_RATE_CALLS) and current > (0.9*ok):
            time.sleep(5)
            print "{} api calls in the last 600s (rate: {} == OK), current rate {}, sleeped {}".format(l, ok, current, 5)

        elif l > (0.99 * MAX_API_RATE_CALLS) and current > (0.99*ok):
            sl = 600 - diff
            time.sleep(sl)
            print "CRITICAL: {} api calls in the last 600s (rate: {} == OK), current rate {}, sleeped {}".format(l, ok, current, 5)
        
    def fetchData(self, dataType, post=None):
        payload = {}

        # use post to update the payload
        if post is not None:
            assert isinstance(post, dict), "'post' arg must be an dict"
            payload.update(post)

        url = "https://www.havelockinvestments.com/r/{:s}".format(dataType)

        if dataType == "portfolio" or "balance":
            payload["key"] = self.apiKey
            
        elif dataType.startswith("orderbook"):
            assert "symbol" in post

        elif dataType == "ordercreate":
            payload['key'] = self.apiKey

        elif dataType == "ordercancel":
            payload['key'] = self.apiKey

        elif dataType == "orders":
            payload['key'] = self.apiKey

        elif dataType == "transactions":
            payload['key'] = self.apiKey
            payload["limit"] = 300
            # add sinceid to payload

        else:
            print "data Type not known!" 
            return None

        try:
            self.checkApiRate()

            r = requests.post(url, data=payload)
            j = json.loads(r.text)
            if j["status"] == "error":
                print "Havelock - API error message: ", j["message"]
            if j["status"] != "ok":
                print "failed to fetch data ({})".format(dataType)
                return None

        except requests.exceptions.ConnectionError:
            print "failed to resolve havelockinvestments.com!"
            return None
        except ValueError:
            print "failed to get data from havelock"
            return None

        return j

    def fetchOrderbook(self, symbol, full=False):
        """ get orderbook """
        dtype = "orderbookfull" if full else "orderbook"
        j = self.fetchData(dtype, {"symbol": symbol})
        if j is None: 
            return None 

        return j["asks"], j["bids"]

    def fetchOrders(self):
        """ fetch open orders """ 
        j = self.fetchData("orders")
        if j is None:
            return None
        return j["orders"]

    def createOrder(self, symbol, action, price, units):
        """ create new order """ 
        assert action in ["buy", "sell"]
        d = {"symbol": symbol, "action": action, "price": price, "units": units}
        j = self.fetchData("ordercreate", d)
        return j

    def cancelOrder(self, order_id):
        """ cancel order """ 
        d = {"id": order_id}
        j = self.fetchData("ordercancel", d)
        return j is not None

    def fetchPortfolio(self):
        """ get portfolio """
        j = self.fetchData("portfolio")
        if j is None:
            return None

        portfolio = j["portfolio"]
        ts = time.time()
        for d in portfolio:
            self.currentPrices[d["symbol"]] = float(d["lastprice"])
            if not __debug__: print "fetched lastprice {} for symbol {}".format(
                    (self.currentPrices[d["symbol"]], d["symbol"]))
        self.portfolio.setCurrentPrices(self.currentPrices)

    def fetchBalance(self):
        """ get balance """
        j = self.fetchData("balance")
        if j is None:
            return None

        balance = j["balance"]
        self.havelockBalance = float(balance["balance"])
        self.havelockBalanceAvailable = float(balance["balanceavailable"])
        #print "havelock balance: {:f} BTC".format(self.havelockBalance)

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

        self.mergeTransactions(ts)

    def loadTransactionFile(self, filename):
        f = open(filename, "r")
        raw = f.read()
        f.close()

        # first havelock transaction file load is in wrong order
        lines = raw.split("\n")
        try:
            first = lines[1].split(",")[0]
            first = int(time.mktime(datetime.datetime.strptime(first, "%Y-%m-%d %H:%M:%S").timetuple()))
            last = lines[-2].split(",")[0]
            last = int(time.mktime(datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S").timetuple()))
            if first > last:
                lines.reverse()
        except:
            pass

        for line in lines:
            self.transactions.addTransaction(line)
        self.buildPortfolio()

    def buildPortfolio(self):
        for s in self.transactions.getSymbols():
            self.portfolio.addTransactions(self.transactions.getTransactions(symbol=s), s)

    def setStartDate(self, timestamp):
        self.transactions.setStartDate(timestamp)
        for s in self.portfolio.getSymbols().values():
            s.setStartDate(timestamp)

    def setEndDate(self, timestamp):
        self.transactions.setEndDate(timestamp)
        for s in self.portfolio.getSymbols().values():
            s.setEndDate(timestamp)

    def getBalance(self, includePortfolio=True):
        if self.havelockBalance is None:
            bal = self.calculateBalance(includePortfolio)
        else:
            bal = self.havelockBalanceAvailable#+self.havelockBalance
        if not includePortfolio:
            return bal

        por = self.portfolio.getCurrentValue()
        return (bal+por)

    def calculateBalance(self, includePortfolio=True):
        bal = self.transactions.getBalance()
        if not includePortfolio:
            return bal

        por = self.portfolio.getCurrentValue()
        return (bal+por)
        
    def mergeTransactionFile(self, filename):
        f = open(filename)
        content = f.read()
        f.close()
        ts = []
        for tr in content.split("\n"):
            t = Transaction()
            if t.parse(tr):
                ts.append(t)
        self.mergeTransactions(ts)

    def mergeTransactions(self, transactions):
        cnt = 0
        for t in transactions:
            if self.insertTransaction(t):
                cnt += 1

        self.transactions.sortTransactions()
        self.portfolio.sortTransactions()
        if cnt > 0:
            print "merge {:d} new transactions".format(cnt)

    def insertTransaction(self, transaction):
        if not transaction in self.transactions:
            self.transactions.addTransactions([transaction])
            self.portfolio.addTransactions([transaction], transaction.getSymbol())
            return True
        
        return False

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
        bal = self.getBalance(includePortfolio=False)
        
        print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("current balance: ", bal, bal*btc2eur)
        por = self.portfolio.getCurrentValue()
        
        print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("portfolio value: ", por, por*btc2eur)
        print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("total deposit: ", dep, dep*btc2eur)
        summ = wit + por + bal - dep
        print "{:<30s} | {:>26f} BTC | {:>25.2f} EUR |".format("in sum: ", summ, summ*btc2eur)
        print "-" * get_console_size()["width"]

    def printPortfolio(self, btc2eur=None, allSymbols=True):
        p = self.portfolio
        console_width = get_console_size()["width"]
        
        print "Your Portfolio:"
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
            if not allSymbols and t.getShareQuantity() == 0:
                continue
               
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

    def plain(self):
        p = self.portfolio
        for s in self.portfolio.symbols:
            t = p.getSymbol(s)
            print "[{:s}]\nshares:{:d},value:{:0.3f},rate:{:0.6f},trend:{:0.2f}".format(t.getName(), t.getShareQuantity(), p.getCurrentValue(s), p.getCurrentPrice(s), p.getTrend(s))
        wit = self.transactions.getWithdrawAmount()
        dep = self.transactions.getDepositAmount()
        bal = self.getBalance(includePortfolio=False)
        por = self.portfolio.getCurrentValue()
        summ = wit + por + bal - dep
        print "[Havelock]\nsum:{:0.5f}".format(summ)

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

    if len(sys.argv) == 4:
        print "check a symbol"
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

        print "balance: {:f}".format(havelock.getBalance(includePortfolio=False))
        print "balance (with Portfolio): {:f}".format(havelock.getBalance())

    elif len(sys.argv) == 3:
        havelock.loadTransactionFile(sys.argv[1])
        print "balance: {:f}".format(havelock.getBalance(includePortfolio=False))
        print "balance (with Portfolio): {:f}".format(havelock.getBalance())

        havelock.mergeTransactionFile(sys.argv[2])
        print "balance: {:f}".format(havelock.getBalance(includePortfolio=False))
        print "balance (with Portfolio): {:f}".format(havelock.getBalance())

        havelock.store(sys.argv[1])

    else:
        print "test this script:"
        print "\t- test a symbol:"
        print "\t  python2 Havelock.py <transactionfile> <symbol> <price>"
        print "\t- merge a new transaction file"
        print "\t  python2 Havelock.py <transactionfile> <mergeFile>"
        sys.exit(1)
