import time
import datetime

import operator

class Transaction:
    def __init__(self):
        """
        2014-09-09 11:01:06,buy,13,0.00061871,PETA,0.00804323,1.09358245,
        """
        self.ts = int(time.time())
        self.qty = 0
        self.price = 0.0
        self.symbol = None
        self.type = None
        self.details = ""
        self.amount = 0.0
        self.hid = 0
        self.balance = 0.0

    def __eq__(self, other):
        # id should be enough, but transaction export to csv has no id!
        sameId = (self.getId() == other.getId())
        if self.getId() != 0:
            return sameId

        sameTs = (int(self.getTimestamp()) == int(other.getTimestamp()))
        sameSymbol = (self.getSymbol() == other.getSymbol())
        sameType = (self.getType() == other.getType())
        sameQuantity = (self.getQuantity() == other.getQuantity())
        """if (sameTs and sameSymbol and sameType) and other.getType() == "sell":
            print "check {:s} and {:s}".format(self, other)
            print "check ts {:d} with {:d}: {:b}".format(int(self.getTimestamp()), int(other.getTimestamp()), sameTs)
            print "check symbol {:s} with {:s}: {:b}".format(self.getSymbol(), other.getSymbol(), sameSymbol)
            print "check {:b}".format((sameTs and sameSymbol))"""
        equal = (sameTs and sameSymbol and sameType and sameQuantity)
        if equal:
            self.setId(other.getId())
        return equal

    def __lt__(self, other):
        return self.ts < other.ts

    def getSymbol(self):
        return self.symbol

    def getType(self):
        return self.type

    def getTimestamp(self):
        return self.ts

    def getPrice(self):
        return self.price

    def setId(self, hid):
        self.hid = hid

    def getId(self):
        return self.hid

    def getAmount(self):
        return self.amount

    def getQuantity(self):
        return self.qty

    def getDetails(self):
        return self.details
    
    def getBalance(self):
        return self.balance

    def parse(self, raw):
        if type(raw) == type(""):
            #Date/Time,Type,Quantity,Price,Symbol,Amount,Balance,Details
            r = raw.split(",")

            if r[0] == "Date/Time":
                return False

            if len(r) == 8: # old format
                offset = 0
            elif len(r) == 9: # new format with id in front
                offset = 1
            else:
                #print "wrong size of array"
                return False


            #2014-09-09 09:10:22
            self.ts = int(time.mktime(datetime.datetime.strptime(r[offset+0], "%Y-%m-%d %H:%M:%S").timetuple()))
            #print "got time %s" % r[0]
            #print "to ts %d" % self.ts
            #print "revert %s" % datetime.datetime.fromtimestamp(self.ts).strftime('%Y-%m-%d %H:%M:%S')
            self.type = r[offset+1]
            if r[offset+2]:
                self.qty = int(r[offset+2])
            else:
                self.qty = 0
            if r[offset+3]:
                self.price = float(r[3+offset])
                if self.price < 0:
                    self.price *= -1
            if r[4+offset] != '':
                self.symbol = r[4+offset]
                if self.symbol == "None":
                    self.symbol = None
            if r[5+offset]:
                self.amount = float(r[5+offset])
                st = self.type
                if (st == "fee" or st == "buy" or st == "buyipo" or st == "withdraw") and self.amount < 0:
                    self.amount *= -1
            if r[6+offset]:
                self.balance = float(r[offset+6])
            self.details = r[7+offset]

            return True
        else:
            #{u'name': u'Bitcoin Difficulty Derivative - MINE', u'symbol': u'B.MINE', u'ts': u'1415725237', u'amount': u'0.00317450', u'details': None, u'units': None, u'dt': u'2014-11-11 12:00:37', u'balance': u'0.12712561', u'type': u'dividend', u'id': u'9070646'}
            if raw["symbol"] is not None:
                self.symbol = str(raw["symbol"])

            self.type = str(raw["type"])
            self.ts = int(time.mktime(datetime.datetime.strptime(raw["dt"], "%Y-%m-%d %H:%M:%S").timetuple()))
            self.hid = int(raw["id"])
            self.amount = float(raw["amount"])
            if self.type == "buy" and self.amount < 0:
                self.amount *= -1

            self.balance = float(raw["balance"])
            if raw["units"] is not None:
                self.qty = int(raw["units"])
            else:
                self.qty = 0
            if raw["details"] is None:
                self.details = ""
            else:
                self.details = str(raw["details"])
            # price is not included???
            # price == amount / units... pfff
            if self.qty != 0:
                self.price = -1*self.amount / float(self.qty)

            return True

    def getHeader(self):
        return "Date/Time,Type,Quantity,Price,Symbol,Amount,Balance,Details"

    def __str__(self):
        #Date/Time,Type,Quantity,Price,Symbol,Amount,Balance,details
        return "%d,%s,%s,%d,%f,%s,%f,%f,%s" %\
                (self.hid,\
                datetime.datetime.fromtimestamp(self.ts).strftime('%Y-%m-%d %H:%M:%S'), \
                self.getType(),\
                self.getQuantity(),\
                self.getPrice(),\
                self.getSymbol(),\
                self.getAmount(),\
                self.getBalance(),\
                self.getDetails())

class Transactions:
    def __init__(self):
        self.transactions = []
        self.allTransactions = {}
        self.symbols = []
        self.types = []
        self.highestHid = 0
        self.minTimestamp = 1*10e10
        self.maxTimestamp = -1
        self.endDate = None
        self.startDate = 0

    def setStartDate(self, startDate):
        self.startDate = startDate

    def setEndDate(self, endDate):
        self.endDate = endDate

    def getNewTransactions(self, transactions):
        # first sort them by timestamp
        transactions.sort(key=operator.attrgetter('ts'))
        new = []
        for t in transactions:
            found = False
            for it in self.transactions:
                if t == it:
                    found = True
                    break
            if not found:
                new.append(t)

        return new

    def __iter__(self):
        for transaction in self.transactions:
            yield transaction

    def __contains__(self, obj):
        for t in self:
            if t == obj:
                return True

        return False

    def getTransactions(self, symbol=None, start=None, end=None):
        # return all if nothing was selected
        if symbol is None and start is None and end is None:
            return self.transactions

        if start is None:
            start = self.minTimestamp

        if end is None:
            end = self.maxTimestamp

        tes = []
        for t in self.transactions:
            ts = t.getTimestamp()
            if ts >= start and ts <= end:
                if symbol is None or t.getSymbol() == symbol:
                    tes.append(t)
        return tes

    def addTransactions(self, transactions):
        for t in transactions:
            self.addTransaction(t, parse=False)

        self.sortTransactions()

    def sortTransactions(self):
        self.transactions.sort(key=operator.attrgetter('ts'))

    def addTransaction(self, raw, parse=True):
        if parse:
            t = Transaction()
            res = t.parse(raw)
            if not res:
                return False
        else:
            t = raw

        if t.getId() > self.highestHid:
            self.highestHid = t.getId()

        #handle buyback and transferin stuff
        if t.getType() == "buyback"  and not t.getDetails():
            if len(self.symbols) != 1:
                print "calculating fake value for buyback and symbol {:s}".format(t.getSymbol())
                t.amount = self.getBuyAmount(t.getSymbol())
                t.details = "mean value calculated by portfolio"
                qty = t.getQuantity()
                for ot in self.transactions:
                    if ot.getType() == "transferin" and ot.getQuantity() == qty:
                        print "found according transferin for symbol {:s}".format(ot.getSymbol())
                        ot.amount = t.amount
                        ot.details = t.getDetails()

        self.transactions.append(t)

        s = t.getSymbol()
        tt = t.getType()
        if s in self.allTransactions:
            if not tt in self.allTransactions[s]:
                self.allTransactions[s][tt] = [t]
            else:
                self.allTransactions[s][tt].append(t)
        else:
            self.allTransactions[s] = {}
            self.allTransactions[s][tt] = [t]

        if t.getTimestamp() < self.minTimestamp:
            self.minTimestamp = t.getTimestamp()

        if t.getTimestamp() > self.maxTimestamp:
            self.maxTimestamp = t.getTimestamp()

        if not t.getSymbol() in self.symbols and not t.getSymbol() is None and t.getSymbol():
            self.symbols.append(t.getSymbol())

        if not t.getType() in self.types and not t.getType() is None:
            self.types.append(t.getType())

        return True

    def getTimestamps(self):
        tes = []
        for t in self.transactions:
            if t.getType() != "rate":
                tes.append(t.getTimestamp())

        return tes

    def getType(self, tp, symbol=None):
        if symbol is None:
            symbols = self.allTransactions.keys()
            #if None in symbols:
            #    symbols.remove(None)
        else:
            symbols = [symbol]

        ret = []
        for s in symbols:
            if tp in self.allTransactions[s]:
                ret += self.allTransactions[s][tp]

        ret.sort(key=operator.attrgetter('ts'))

        if self.endDate is not None:
            ret2 = []
            for r in ret:
                if r.getTimestamp() > self.endDate:
                    break
                if r.getTimestamp() > self.startDate:
                    ret2.append(r)
            return ret2


        return ret

    def getBuy(self, symbol=None):
        buys       = self.getType("buy", symbol)
        ipos       = self.getType("buyipo", symbol)
        transferin = self.getType("transferin", symbol)
        ret = buys + ipos + transferin
        ret.sort(key=operator.attrgetter('ts'))
        return ret

    def getSell(self, symbol=None):
        sells      = self.getType("sell", symbol)
        buyback    = self.getType("buyback", symbol)
        ret = sells + buyback
        ret.sort(key=operator.attrgetter('ts'))
        return ret

    def getBuyback(self, symbol=None):
        buyback = self.getType("buyback", symbol)
        return buyback

    def getDividend(self, symbol=None):
        return self.getType("dividend", symbol)

    def getDeposit(self):
        return self.getType("deposit")

    def getEscrow(self, symbol=None):
        return self.getType("escrow", symbol)

    def getFee(self, symbol=None):
        return self.getType("fee", symbol)

    def getWithdraw(self):
        return self.getType("withdraw")
    
    def getRate(self):
        return self.getType("rate")

   
    def sumAmount(self, array):
        return sum(x.getAmount() for x in array)

    def getBuybackAmount(self, symbol=None):
        return self.sumAmount(self.getBuyback(symbol))

    def getSellAmount(self, symbol=None):
        return self.sumAmount(self.getSell(symbol))

    def getBuyAmount(self, symbol=None):
        return self.sumAmount(self.getBuy(symbol))

    def getDividendAmount(self, symbol=None):
        return self.sumAmount(self.getDividend(symbol))

    def getDepositAmount(self):
        return self.sumAmount(self.getDeposit())

    def getWithdrawAmount(self):
        return self.sumAmount(self.getWithdraw())
    
    def getFeeAmount(self, symbol=None):
        return self.sumAmount(self.getFee(symbol))

    def getEscrowAmount(self, symbol=None):
        return self.sumAmount(self.getEscrow(symbol))

    def getBookAmount(self, symbol=None):
        buys = self.getBuyAmount(symbol)
        sells = self.getSellAmount(symbol)
        fees = self.getFeeAmount(symbol)

        return buys - sells + fees


    def sumQuantity(self, array):
        sum = 0
        for t in array:
            sum += t.getQuantity()
        return sum

    def getSellQuantity(self, symbol=None):
        return self.sumQuantity(self.getSell(symbol))

    def getBuyQuantity(self, symbol=None):
        return self.sumQuantity(self.getBuy(symbol))

    def getShareQuantity(self, symbol=None):
        return self.getBuyQuantity(symbol) - self.getSellQuantity(symbol)




    def getSymbols(self):
        return self.symbols

    def getBalance(self):
        deposits = self.getDepositAmount()
        withdraws = self.getWithdrawAmount()
        fees = self.getFeeAmount()
        buys = self.getBuyAmount()
        sells = self.getSellAmount()
        dividends = self.getDividendAmount()

        return deposits + dividends + sells - withdraws - fees - buys

