import sys

from classes import Havelock
from classes import Bitcoin


if __name__ == "__main__":
    bitcoin = Bitcoin("xxx")
    if len(sys.argv) == 3:
        bitcoin.loadTransactionFile(sys.argv[2])
    else:
        print "tip: run this script with python2 %s <havelock-csv-file> <bitcoin-csv-file> to get an initial state" % sys.argv[0]

    havelock = Havelock("xxx")
    if len(sys.argv) == 2:
        havelock.loadTransactionFile(sys.argv[1])
    else:
        print "tip: run this script with python2 %s <havelock-csv-file> to get an initial state" % sys.argv[0]


    while 1:
        # update transactions
        havelock.fetchTransactions()
        # get current prices
        havelock.fetchPortfolio()
        havelock.printDetails(full=False)

        havelockBalance = havelock.getBalance()

        havelock.store()
        
        print 

        bitcoin.fetchData()
        bitcoin.printDetails(full=False)
        
        print 

        bitcoinBalance = bitcoin.getBalance()

        print "Summery:"
        print "------------------------------"
        sumBtc = bitcoinBalance + havelockBalance
        sumEur = bitcoin.exchange(sumBtc)
        print "Total sum: %f BTC (%0.2f EUR)" % (sumBtc, sumEur)
        invest = bitcoin.getInvest()
        print "Total sum of invest: %0.2f EUR" % invest
        print "in sum your profit is: %0.2f EUR" % (sumEur + invest)
        break

        time.sleep(10)


    """
    # debug win / loss shit
    data = havelock.getActivity()
    cnt = 0
    data2 = []
    for (ts, balance) in data:
        data2.append((cnt, balance))
        cnt +=1

    data3 = havelock.getData("B.MINE")
    data4 = havelock.getData("AMHASH1")
    data5 = havelock.getData("SCRYPT")
    data6 = havelock.getData("PETA")

    import numpy as np
    import matplotlib.pyplot as plot

    fig = plot.figure()
    ax = fig.add_subplot(111)
    (xes, yes) = zip(*data3)
    ax.plot(xes, yes, 'b-')
    (xes, yes) = zip(*data4)
    ax.plot(xes, yes, 'r-')
    (xes, yes) = zip(*data5)
    ax.plot(xes, yes, 'k-')
    (xes, yes) = zip(*data6)
    ax.plot(xes, yes, 'y-')
    plot.show()"""

