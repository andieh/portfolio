import time
import sys

from Transactions import *
from Bitcoin import *

class Rate:
    def __init__(self, name):
        self.name = name
        self.rates = {}

    def addRate(self, timestamp, rate):
        self.rates[int(timestamp)] = rate

    def findPreviousRate(self, timestamp):
        ts = sorted(self.rates.keys())

        for (tid, t) in enumerate(ts):
            if t >= timestamp:
                break

        if tid == 0:
            return 0.0
        else:
            return self.rates[ts[tid-1]]

    def getRate(self, timestamp):
        timestamp = int(timestamp)
        if timestamp in self.rates:
        # exact timestamp known
            return self.rates[timestamp]
        else:
            # interpolate
            return self.findPreviousRate(timestamp)

    def getMinTimestamp(self):
        return min(self.rates.keys())

    def getMaxTimestamp(self):
        return max(self.rates.keys())

    def __str__(self):
        c = ""
        for ts in sorted(self.rates.keys()):
            try:
                c += "{:s},{:d},{:f}\n".format(self.name, ts, self.rates[ts])
            except:
                print "uuu wrong format"

        return c

class Rates:
    def __init__(self):
        self.rates = {}

    def hasSymbol(self, name):
        return name in self.rates

    def addSymbol(self, name):
        #print "add new symbol {:s}".format(name)
        self.rates[name] = Rate(name)

    def getMinTimestamp(self, symbol=None):
        if symbol is None:
            ts = []
            for s in self.rates.keys():
                ts.append(self.rates[s].getMinTimestamp())
            return min(ts)

        return self.rates[symbol].getMinTimestamp()

    def getMaxTimestamp(self, symbol=None):
        if symbol is None:
            ts = []
            for s in self.rates.keys():
                ts.append(self.rates[s].getMaxTimestamp())
            return max(ts)

        return self.rates[symbol].getMaxTimestamp()

    def getRate(self, name, timestamp):
        if name not in self.rates.keys():
            print "no values for symbol {:s}".format(name)
            return None
        return self.rates[name].getRate(timestamp)

    def addRate(self, name, rate, timestamp=None):
        if timestamp is None:
            timestamp = int(time.time())

        if name not in self.rates:
            self.addSymbol(name)

        self.rates[name].addRate(timestamp, rate)

    def store(self, filename):
        try:
            f = open(filename, "w")
        except:
            print "failed to open filename {:s}".format(filename)
            return None

        c = ""
        for symbol in self.rates.values():
            c += str(symbol)
        f.write(c)
        f.close()

    def load(self, filename):
        try:
            f = open(filename, "r")
        except:
            print "failed to load rates from {:s}".format(filename)
            return None

        c = f.read().split("\n")
        f.close()

        for line in c:
            values = line.split(",")
            if len(values) != 3:
                continue
            try:
                name = values[0]
                timestamp = int(values[1])
                rate = float(values[2])
            except:
                print "failed to parse line {:s}".format(line)
                continue

            self.addRate(name, rate, timestamp)

    def loadHavelockFile(self, filename):
        f = open(filename, "r")
        raw = f.read()
        f.close()
        transactions = Transactions()

        for line in raw.split("\n"):
            transactions.addTransaction(line)

        self.loadTransactions(transactions)

    def loadBitcoinFile(self, filename):
        f = open(filename, "r")
        raw = f.read()
        f.close()

        transactions = Transactions()

        ts = []
        for line in raw.split("\n"):
            if not line:
                continue
            b = BitcoinTransaction()
            if b.parse(line):
                ts.append(b)
        transactions.addTransactions(ts)
        
        self.loadTransactions(transactions)

    def loadTransactions(self, transactions):
        inserted = 0
        for trans in transactions.transactions:
            t = trans.getType()
            if t == "buyipo" or t == "rate" or t == "buy" or t == "sell":
                self.addRate(trans.getSymbol(), trans.getPrice(), trans.getTimestamp())
                inserted += 1
        print "loaded {:d} rates".format(inserted)



if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "run this script with:"
        print "- {:s} havelock-transactions-file bitcoin-transaction-file".format(sys.argv[0])
        print "  to read rates from havelock and bitcoin file"
        print "  store to rates.prf"
        print "- {:s} rate-file".format(sys.argv[0])
        print "  to read a rate file"
        sys.exit(0)

    rates = Rates()
    
    if len(sys.argv) == 3:
        rates.loadHavelockFile(sys.argv[1])
        rates.loadBitcoinFile(sys.argv[2])

        rates.store("rates.prf")

    if len(sys.argv) == 2:
        rates.load(sys.argv[1])

        print rates.getRate("AMHASH1", 1418419807)
        print rates.getRate("AMHASH1", 1018419807)
        print rates.getRate("AMHASH1", 1418419808)
        print rates.getRate("AMHASH1", 1418419809)
