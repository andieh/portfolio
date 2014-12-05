from Transactions import *

class Symbol(Transactions):
    def __init__(self, name):
        Transactions.__init__(self)
        self.symbol = name

    def getMeanPrice(self):
        pr = self.getBuyAmount() - self.getSellAmount() + self.getFeeAmount()
        am = self.getBuyQuantity() - self.getSellQuantity()
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
    def __init__(self, epsilon=1e-12):
        self.symbols = {}
        self.currentPrices = {}
        self.epsilon = epsilon

    def isEqual(self, val, target):
        x = val - target
        return -self.epsilon <= x <= self.epsilon

    def addSymbol(self, symbol):
        if symbol == None:
            return

        if symbol in self.symbols:
            print "[+] symbol already registered, ignoring new data"
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
        if type(symbols) == str:
            symbols = [symbols]

        if symbols is None:
            symbols = self.symbols.keys()

        value = 0.0
        for symbol in symbols:
            value += self.symbols[symbol].getShareQuantity() * self.currentPrices[symbol]
        return value
    
    def getBookValue(self, symbols=None):
        """
        move to transactions?
        """
        if type(symbols) == str:
            symbols = [symbols]

        if symbols is None:
            symbols = self.symbols.keys()

        buys = 0.0
        sels = 0.0
        fees = 0.0
        for s in symbols:
            sym = self.getSymbol(s)
            buys += sym.getBuyAmount()
            sels += sym.getSellAmount()
            fees += sym.getFeeAmount()

        return buys - sels + fees

    def getTrend(self, symbol):
        if self.symbols[symbol].getMeanPrice() == 0:
            return 0

        return ((self.getCurrentPrice(symbol) / self.symbols[symbol].getMeanPrice()) - 1.0) * 100
    
    def getOverallTrend(self, symbol):
        p = self.getBookValue(symbol)
        if self.isEqual(p, 0.0):
            return float("NaN")

        c = self.getCurrentWin(symbol)
        return ((c / p)) * 100.0

    def getSymbols(self):
        return self.symbols

    def getSymbol(self, symbol):
        if not symbol in self.symbols:
            return None
        return self.symbols[symbol]

    def getCurrentWin(self, symbol):
        sym = self.symbols[symbol]
        book = self.getBookValue(symbol)
        value = self.getCurrentValue(symbol)
        dividend = sym.getDividendAmount()
        return value + dividend - book

    def addTransactions(self, transactions, sy=None):
        """ 
        this function sucks!
        needs cleanup
        """
        if sy == "None":
            return

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
