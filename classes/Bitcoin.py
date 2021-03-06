import requests
import json

import sys
import time
import datetime

try:
    from utils import get_console_size
except:
    # not needed in a testing environment
    pass

from Transactions import *

class BitcoinTransaction:
    def __init__(self):
        self.ts = time.time()
        self.symbol = "BITCOIN"
        self.type = None
        self.details = ""
        self.price = 0.0
        self.eurBefore = 0.0
        self.btcAfter = 0.0
        self.eurAfter = 0.0
        self.qty = 0.0
        self.amount = 0.0
        self.balance = 0.0
        #not used
        self.hid = 0

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

    def parse(self, line):
        raw = line.split(";")
        if raw[0] == "Datum":
            return False

        try:
            self.ts = int(time.mktime(datetime.datetime.strptime(raw[0].replace("\"",""), "%Y-%m-%d %H:%M:%S").timetuple()))
        
            if raw[1] == "Kauf":
                self.type = "buy"
            elif raw[1] == "Verkauf":
                self.type = "sell"
            elif raw[1] == "Auszahlung":
                self.type = "withdraw"
            elif raw[1] == "Einzahlung":
                self.type = "deposit"
            elif raw[1] == "Kurs":
                self.type = "rate"
            elif raw[1] == "\"Welcome Btc\"":
                self.type = "deposit"
                raw[2] = "0.1 BTC welcome bonus to bitcoin.de!"
            elif raw[1] == "Registrierung":
                return False
            else:
                self.type = raw[1]

            self.details = raw[2]

            if raw[3]:
                self.price = float(raw[3].replace(",", ""))
                if self.type == "rate" and self.price < 0.0001:
                    return False

            if raw[4]:
                self.eurBefore = float(raw[4].replace(",",""))
            
            if raw[5]:
                self.btcAfter = float(raw[5].replace(",",""))
            
            if raw[6]:
                self.eurAfter = float(raw[6].replace(",",""))

            if raw[7]:
                self.amount = float(raw[7].replace(",", ""))

            self.qty = float(raw[8].replace(",", ""))
            if self.type == "withdraw" or self.type == "sell":
                self.qty *= -1
            if self.type == "deposit" or self.type == "withdraw":
                self.amount = self.qty

            self.balance = float(raw[9].replace(",", ""))

            return True

        except Exception, e:
            print "failed to parse {:s}, error: {:s}".format(raw, str(e))
        
        return False

    def getHeader(self):
        return "Datum;Typ;Referenz;\"Kurs (EUR/BTC)\";\"BTC vor Gebuehr\";\"EUR vor Gebuehr\";\"BTC nach Gebuehr\";\"EUR nach Gebuehr\";\"Zu- / Abgang\";Kontostand"

    def __eq__(self, other):
        sameTs = (int(self.ts) == int(other.getTimestamp()))
        sameId = (self.symbol == other.getSymbol())
        return (sameTs and sameId)

    def __str__(self):
        qty = self.qty
        amount = self.amount
        if self.type == "sell" or self.type == "withdraw":
            qty *= -1

        t = "Kurs"
        if self.type == "sell":
            t = "Verkauf"
        elif self.type == "buy":
            t = "Kauf"
        elif self.type == "deposit":
            t = "Einzahlung"
        elif self.type == "withdraw":
            t = "Auszahlung"

        return "\"%s\";%s;%s;%f;%f;%f;%f;%f;%f;%f" % \
                (datetime.datetime.fromtimestamp(self.ts).strftime('%Y-%m-%d %H:%M:%S'), \
                t,\
                self.details,\
                self.price,\
                self.eurBefore,\
                self.btcAfter,\
                self.eurAfter,\
                amount,\
                qty,\
                self.balance)

class Bitcoin:
    def __init__(self, conf):
        self.conf = conf
        self.apiKey = self.conf.btc_de_api_key
        self.btc2eur = 0.0
        self.eur2btc = 0.0
        self.transactions = Transactions()

    def fetchData(self):
        try:
            r = requests.get("https://bitcoinapi.de/v1/%s/rate.json" % self.apiKey)
        except requests.exceptions.ConnectionError:
            print "failed to resolve bitcoinapi.de"
            return None
        try:
            j = json.loads(r.text)
            self.btc2eur = float(j["rate_weighted"])
            self.eur2btc = 1/self.btc2eur
        except Exception, e:
            print "failed to fetch bitcoin price"
            print str(e)
            return None

        return self.btc2eur

    def loadTransactionFile(self, filename, start=-1):
        f = open(filename, "r")
        content = f.read()
        f.close()
        transactions = []
        for line in content.split("\n"):
            if not line:
                continue
            b = BitcoinTransaction()
            current = int(time.time())
            if b.parse(line):
                if start < 0 or (current - b.getTimestamp())/(60*60*24)<start:
                    transactions.append(b)
        self.transactions.addTransactions(transactions)
        self.transactions.sortTransactions()

    def mergeTransactionFile(self, filename):
        # load file
        f = open(filename, "r")
        content = f.read()
        f.close()
        cnt = 0
        for line in content.split("\n"):
            if not line:
                continue
            b = BitcoinTransaction()
            if b.parse(line):
                if self.insertTransaction(b):
                    print "added transaction {:s}".format(str(b))
                    cnt +=1
        
        self.transactions.sortTransactions()
        print "merged {:d} transactions".format(cnt)

    def insertTransaction(self, transaction):
        if not transaction in self.transactions:
            self.transactions.addTransactions([transaction])
            return True
        return False
    
    def store(self, filename):
        content = "{:s}\n".format(BitcoinTransaction().getHeader())
        for t in self.transactions.transactions:
            content += "{:s}\n".format(t)

        f = open(filename, "w")
        f.write(content)
        f.close()

    def getBalance(self):
        buy = self.transactions.getBuyQuantity() 
        sel = self.transactions.getSellQuantity()
        wit = self.transactions.getWithdrawAmount()
        dep = self.transactions.getDepositAmount()
        return (dep+buy-wit-sel)

    def setEndDate(self, timestamp):
        self.transactions.setEndDate(timestamp)

    def getInvest(self):
        buy = self.transactions.getBuyAmount() 
        sel = self.transactions.getSellAmount()
        return sel - buy

    def exchange(self, btc):
        return btc * self.btc2eur

    def getBuyRate(self):
        amount = self.transactions.getBuyAmount() 
        buy = self.transactions.getBuyQuantity()
        if buy == 0:
            return 0.0
        return amount / buy
    
    def getTrend(self):
        rate = self.getBuyRate()
        if self.transactions.getBuyQuantity() == 0:
            return 0.0
        return ((self.btc2eur / rate) - 1.0) * 100

    def printBitcoin(self):
        console_width = get_console_size()["width"]
        
        print "Your Portfolio:"
        print "-" * console_width


        fmts =    [".2f", "s", "s", ".3f", ".5f", ".5f", ".3f"]
        header =  ["Trend (%)", "Buys (Price)", "", "Market (B)", 
                   "Divs (B)", "Mean (B)", "Win (B)"]
   
        fmts2 =   [".2f", "s", "d", ".3f", ".5f", ".5f", ".2f"]
        header2 = ["Overall (%)", "Sells (Price)", "Sum", "Book (B)", 
                   "Fee (B)", "Cur (B)", "Win (E)"]
    
        colwidth = (console_width / len(header)) - 3
        fill = " | "       

        print fill.join("{:>{}s}".format(h, colwidth) \
                for f, h in zip(fmts, header))
        print fill.join("{:>{}s}".format(h, colwidth) \
                for f, h in zip(fmts, header2))   
        
        fmts =    [".2f", ".2f", "s", ".2f", "s", ".5f", "s"]
        header =  ["Trend (%)", "Buys", "", "Market (B)", 
                   "Divs (B)", "Mean (B)", "Win (B)"]
   
        #fmts2 =   [".2f", "d", "d", "s", ".5f", ".5f", ".2f"]
        fmts2 =   ["s", ".2f", ".2f", ".2f", "s", ".5f", ".2f"]
        header2 = ["Overall (%)", "Sells", "Sum", "Book (B)", 
                   "Fee (B)", "Cur (B)", "Win (E)"]
    
        colwidth = (console_width / len(header)) - 3
        fill = " | "       

        print "-" * console_width
        _s = "{1:-^{0}}".format(console_width, "> Bitcoin <")
        print _s[console_width/5:] + _s[:console_width/5]
    

        data = [ self.getTrend(), self.transactions.getBuyQuantity(), 
                 "", self.exchange(self.getBalance()), "", 
                 self.getBuyRate(), "" ]
        print fill.join("{0:>{1}{2}}".format(d, colwidth, f) \
                 for f, d in zip(fmts, data))

        data2 = [ "", self.transactions.getSellQuantity(), self.getBalance(), 
                  self.transactions.getBuyAmount() - self.transactions.getSellAmount(), 
                  "", self.btc2eur, 
                  self.transactions.getSellAmount() + self.exchange(self.getBalance()) - self.transactions.getBuyAmount() ]
        print fill.join("{0:>{1}{2}}".format(d, colwidth, f) \
                 for f, d in zip(fmts2, data2))
        print "-" * console_width
        

    def printDetails(self, full=True):
        print "Bitcoin Account Details:" 
        print "------------------------------"
        buyAmount = self.transactions.getBuyAmount()
        selAmount = self.transactions.getSellAmount()
        if full:
            buy = self.transactions.getBuyQuantity() 
            print "total buys:\t\t%d BTC for %0.2f EUR (rate: %0.4f EUR)" % (buy, buyAmount, self.getBuyRate())

            sel = self.transactions.getSellQuantity()
            if sel == 0:
                mean = 0.0
            else:
                mean = selAmount / sel
            print "total sells:\t\t%d BTC for %0.2f EUR (rate: %0.4f EUR)" % (sel, selAmount, mean)

            wit = self.transactions.getWithdrawAmount()
            print "total withdraw:\t\t%f BTC" % wit
            dep = self.transactions.getDepositAmount()
            print "total deposit:\t\t%f BTC" % dep
            print "------------------------------"

        print "current rate: %f EUR (Trend: %0.2f%%)" % (self.btc2eur, self.getTrend())
        val = self.getBalance()
        print "current balance: %f BTC (%0.2f EUR)" % (val, self.exchange(val))
        value = self.exchange(val) + selAmount - buyAmount
        print "in sum your profit is:\t%f EUR" % value

    def plain(self):
        print "[Bitcoin.de]\nrate:{:0.2f},trend:{:0.2f},balance:{:0.6f}".format(self.btc2eur, self.getTrend(), self.getBalance())

if __name__ == "__main__":
    # ugly, but only for testing puporse 
    import sys, os
    sys.path.append(os.path.dirname("../"))
    from config import Config

    b = Bitcoin(Config)
    #b.fetchData()
    b.loadTransactionFile(sys.argv[1])
    
    b.printDetails()

    if len(sys.argv) == 3:
        mf = sys.argv[2]
        print "merge csv file: {:s}".format(mf)
        b.mergeTransactionFile(mf)
        b.printDetails()
        b.store(sys.argv[1])

