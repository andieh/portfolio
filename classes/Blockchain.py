import requests

class Blockchain:
    def __init__(self):
        self.data = {}
    
    def printDetails(self):
        for (key, value) in self.data.items():
            print "{:<15s} : {:<40s}".format(key, value)

    def query(self):
        """
        getdifficulty - Current difficulty target as a decimal number
        getblockcount - Current block height in the longest chain
        latesthash - Hash of the latest block
        bcperblock - Current block reward in BTC
        totalbc - Total Bitcoins in circulation (delayed by up to 1 hour])
        probability - Probability of finding a valid block each hash attempt
        hashestowin - Average number of hash attempts needed to solve a block
        nextretarget - Block height of the next difficulty retarget
        avgtxsize - Average transaction size for the past 1000 blocks. Change the number of blocks by passing an integer as the second argument e.g. avgtxsize/2000
        avgtxvalue - Average transaction value (1000 Default)
        interval - average time between blocks in seconds
        eta - estimated time until the next block (in seconds)
        avgtxnumber - Average number of transactions per block (100 Default)
        """
        names = ["getdifficulty", "getblockcount", "latesthash", "bcperblock", "totalbc", "probability", "hashestowin", "nextretarget", "avgtxsize", "avgtxvalue", "interval", "eta", "avgtxnumber"]
        for name in names:
            self.data[name] = self.fetchData(name)


    def fetchData(self, name):
        try:
            s = "https://blockchain.info/q/%s" % name
            r = requests.get(s)
        except requests.exceptions.ConnectionError:
            print "failed to resolve blockchain.info"
            return None
        return r.text

if __name__ == "__main__":
    b = Blockchain()

    b.query()

    b.printDetails()


