from Transactions import *

class Symbol(Transactions):
    def __init__(self, name):
        Transactions.__init__(self)
        self.symbol = name

    def getMeanPrice(self):
        tes = self.getBuy()
        pr = 0.0
        am = 0
        for t in tes:
            am += t.getQuantity()
            pr += t.getAmount()
        if am == 0:
            return 0.0

        return (pr / am)

    def getLastPrice(self):
        buys = self.getBuy()
        sells = self.getSell()
        lb = buys[-1]
        if len(sells):
            if lb.getTimestamp() < sells[-1].getTimestamp():
                return sells[-1].getPrice()
        return buys[-1].getPrice()

class Portfolio:
    def __init__(self):
        self.symbols = {}
        self.currentPrices = {}

    def addSymbol(self, symbol):
        if symbol in self.symbols:
            print "symbol already registered, ignoring new data"
            return
        self.symbols[symbol] = Symbol(symbol)
        #self.currentPrices[symbol] = 0.0

    def setCurrentPrices(self, prices):
        for s in self.symbols:
            if s in prices:
                #print "set current price for symbol %s to %f BTC" % (s, prices[s])
                self.currentPrices[s] = prices[s]

    def getCurrentPrice(self, symbol):
        return self.currentPrices[symbol]

    def getCurrentValue(self, symbols=None):
        if type(symbols) == type(""):
            symbols = [symbols]

        if symbols is None:
            symbols = self.symbols.keys()

        value = 0.0
        for symbol in symbols:
            value += self.symbols[symbol].getShareQuantity() * self.currentPrices[symbol]
        return value
    
    def getTrend(self, symbol):
        if self.symbols[symbol].getMeanPrice() == 0:
            return 0

        return ((self.getCurrentPrice(symbol) / self.symbols[symbol].getMeanPrice()) - 1.0) * 100
    
    def getOverallTrend(self, symbol):
        p = self.symbols[symbol].getBuyAmount() - self.symbols[symbol].getSellAmount()
        if p == 0:
            return 0

        c = self.symbols[symbol].getShareQuantity() * self.getCurrentPrice(symbol) + self.symbols[symbol].getDividendAmount()
        return ((c/p)-1.0)*100

    def addTransactions(self, transactions, sy=None):
        new = None
        if sy is None:
            for t in transactions:
                if t.getSymbol() is None:
                    continue
                if not t.getSymbol() in self.symbols:
                    self.addSymbol(t.getSymbol())
                    new = t.getSymbol()

                self.symbols[t.getSymbol()].addTransaction(t, parse=False)
                self.symbols[t.getSymbol()].transactions.sort(key=operator.attrgetter('ts'))
        else:
            if not sy in self.symbols:
                self.addSymbol(sy)
                new = sy
                

            for t in transactions:
                self.symbols[sy].addTransaction(t, parse=False)

        if new is not None:
            #print "new symbol added, assuming mean value for prices"
            self.currentPrices[new] = self.symbols[new].getMeanPrice()
