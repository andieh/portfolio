import requests
import json

import sys
import time
import datetime

from Transactions import *

class BitcoinTransaction:
    def __init__(self):
        self.ts = time.time()
        self.symbol = "BITCOIN"
        self.type = None
        self.details = ""
        self.price = 0.0
        self.qty = 0.0
        self.amount = 0.0
        self.balance = 0.0

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
        self.ts = int(time.mktime(datetime.datetime.strptime(raw[0].replace("\"",""), "%Y-%m-%d %H:%M:%S").timetuple()))
    
        if raw[1] == "Kauf":
            self.type = "buy"
        elif raw[1] == "Verkauf":
            self.type = "sell"
        elif raw[1] == "Auszahlung":
            self.type = "withdraw"
        elif raw[1] == "Einzahlung":
            self.type = "deposit"
        else:
            self.type = raw[1]

        self.details = raw[2]
        if raw[3]:
            self.price = float(raw[3])

        self.qty = float(raw[8])
        if self.type == "withdraw" or self.type == "sell":
            self.qty *= -1


        if raw[7]:
            self.amount = float(raw[7])
        self.balance = float(raw[9])

        if self.type == "deposit" or self.type == "withdraw":
            self.amount = self.qty

    def __str__(self):
        return "%s,%s,%s,%f,%f,%f,%f" % \
                (datetime.datetime.fromtimestamp(self.ts).strftime('%Y-%m-%d %H:%M:%S'), \
                self.type,\
                self.details,\
                self.price,\
                self.qty,\
                self.amount,\
                self.balance)

class Bitcoin:
    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.btc2eur = 0.0
        self.eur2btc = 0.0
        self.transactions = Transactions()

    def fetchData(self):
        r = requests.get("https://bitcoinapi.de/v1/%s/rate.json" % self.apiKey)
        try:
            j = json.loads(r.text)
            self.btc2eur = float(j["rate_weighted"])
            self.eur2btc = 1/self.btc2eur
        except Exception, e:
            print "failed to fetch bitcoin price"
            print str(e)

        return self.btc2eur

    def loadTransactionFile(self, filename):
        f = open(filename, "r")
        content = f.read()
        f.close()
        transactions = []
        for line in content.split("\n"):
            if not line:
                continue
            raw = line.split(";")
            if raw[0] == "Datum":
                continue
            b = BitcoinTransaction()
            b.parse(raw)
            transactions.append(b)

        self.transactions.addTransactions(transactions)

    def getBalance(self):
        buy = self.transactions.getBuyQuantity() 
        sel = self.transactions.getSellQuantity()
        wit = self.transactions.getWithdrawAmount()
        dep = self.transactions.getDepositAmount()
        return (dep+buy-wit-sel)

    def getInvest(self):
        buy = self.transactions.getBuyAmount() 
        sel = self.transactions.getSellAmount()
        return sel - buy

    def exchange(self, btc):
        return btc * self.btc2eur

    def printDetails(self, full=True):
        print "Bitcoin Account Details:" 
        print "------------------------------"
        buyAmount = self.transactions.getBuyAmount()
        selAmount = self.transactions.getSellAmount()
        if full:
            buy = self.transactions.getBuyQuantity() 
            mean = buyAmount / buy
            print "total buys:\t\t%d BTC for %0.2f EUR (rate: %0.4f EUR)" % (buy, buyAmount, mean)

            sel = self.transactions.getSellQuantity()
            mean = selAmount / sel
            print "total sells:\t\t%d BTC for %0.2f EUR (rate: %0.4f EUR)" % (sel, selAmount, mean)

            wit = self.transactions.getWithdrawAmount()
            print "total withdraw:\t\t%f BTC" % wit
            dep = self.transactions.getDepositAmount()
            print "total deposit:\t\t%f BTC" % dep
            print "------------------------------"

        print "current rate: %f EUR" % self.btc2eur 
        val = self.getBalance()
        print "current balance: %f BTC (%0.2f EUR)" % (val, self.exchange(val))
        value = self.exchange(val) + selAmount - buyAmount
        print "in sum your profit is:\t%f EUR" % value

if __name__ == "__main__":
    b = Bitcoin("***REMOVED***")
    b.fetchData()
    b.loadTransactionFile(sys.argv[1])
    
    b.printDetails()

