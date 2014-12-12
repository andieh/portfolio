import requests
import time

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
        hashrate - Estimated network hash rate in gigahash
        """
        names = ["getdifficulty", "getblockcount", "latesthash", \
                 "bcperblock", "totalbc", "probability", "hashestowin", \
                 "nextretarget", "avgtxsize", "avgtxvalue", "interval", \
                 "eta", "avgtxnumber", "hashrate" ]
        for name in names:
            self.data[name] = self.fetchData(name)
            time.sleep(10)


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

    #b.query()

    diff = float(b.fetchData("getdifficulty"))
    print "{:<30s} {:<40g}".format("current diff is", diff)
    time.sleep(1)

    eta = float(b.fetchData("interval"))
    print "{:<30s} {:<10f}".format("avg time between blocks (s):", eta)
    # negative time? wtf?
    time.sleep(1)

    gHashrate = float(b.fetchData("hashrate"))
    print "{:<30s} {:<40f}".format("network hashrate (GHs/s):", gHashrate)

    #difficulty=((Time for a block to be found in seconds)*(hashes per second))/2^32
    diffN = (eta * gHashrate * 10e9) / 2**32
    print "{:<30s} {:<40g}".format("estimated hashrate:", diffN)
    print "{:<30s} {:<10f}%".format("estimated increase:",(diffN/diff-1)*100)

    #newDifficulty=currentDifficulty*600/averageTimeBetweenBlocksSinceLastDifficultyChange;
    #powerInHashesPerSecond=currentDifficulty*2^32/averageTimeBetweenBlocks
    #averageTimeBetweenBlocks=currentDifficulty*2^32/powerInHashesPerSecond

    # this is just one block, we need the block since the last difficulty change!
    # and what is 600? ahh ok, this must be the time 
    diffN2 = diff * 600 / eta
    print "{:<30s} {:<40g}".format("estimated hashrate2:", diffN2)
    print "{:<30s} {:<10f}%".format("estimated increase:",(diffN2/diff-1)*100)

    # maybe this:
    # The network sets the difficulty to the value that would have most likely caused the prior 2016 blocks to take two weeks to complete, given the same computational effort (according to the timestamps recorded in the blocks).
    timeFor2016 = 2016 * eta
    weeks = timeFor2016
    secondsForTwoWeeks = 60*60*24*14
    print "one week has {:d} s, 2016 blocks need {:f} s".format(secondsForTwoWeeks, timeFor2016)
    print "{:<30s} {:<10f}%".format("estimated increase:",((secondsForTwoWeeks/timeFor2016)-1)*100)


    b.printDetails()


