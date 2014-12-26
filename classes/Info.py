import requests
import time
import datetime
import math

class Info:
    def __init__(self):
        self.data = {}
        self.lastDiffChange = 1417734000 #2014-12-05 00:00:00
    
    def getNextDifficultyChangeAt(self):
        nextTs = self.lastDiffChange
        current = int(time.time())
        while nextTs < current:
            nextTs += 14*24*60*60 # diff change every 14 days

        return nextTs

    def getNextDifficultyChange(self):
        currentDiff = self.data["getdifficulty"]
        nextDiff    = self.data["estimate"]
        return ((nextDiff / currentDiff) - 1.0)*100

    def printDetails(self):
        for (key, value) in self.data.items():
            print "{:<15s} : {:<40s}".format(key, str(value))
        ndc = self.getNextDifficultyChangeAt()
        ndcStr = datetime.datetime.fromtimestamp(ndc).strftime('%Y-%m-%d')
        current = int(time.time())
        ndcDays = int(math.ceil((ndc - current) / float(60*60*24)))

        print "next diffchange at {:s} ({:d} days): {:0.2f}%".format(ndcStr, ndcDays, self.getNextDifficultyChange())

        self.getNextDifficultyChange()

    def fetchData(self, name):
        try:
            s = "https://blockexplorer.com/q/{:s}".format(name)
            r = requests.get(s)
        except requests.exceptions.ConnectionError:
            print "failed to resolve blockchain.info"
            return None
        return r.text

    def update(self):
        keys = ["getdifficulty", "estimate", "totalbc"]
        for key in keys:
            data = float(self.fetchData(key))
            if data is not None:
                self.data[key] = data

if __name__ == "__main__":
    b = Info()

    b.update()

    b.printDetails()


