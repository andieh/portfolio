import requests
import json

import time
import base64
import hmac
import hashlib

# hard stuff, check this:
# https://gist.github.com/jordanbaucke/5812039

class Bitfinex:
    def __init__(self, conf):
        self.conf = conf
        self.apiKey = self.conf.bitfinex_api_key
        self.secret = self.conf.bitfinex_secret
        self.url = "https://api.bitfinex.com/v1"

    def fetchData(self):
        key = "balances"
        try:
            # json data object
            data = {}
            data["request"] = "/v1/{:s}".format(key)
            data["nonce"] = str(time.time())
            data["options"] = {}
            dataj = json.dumps(data)

            #encode with base64
            datab = base64.b64encode(bytes(dataj), "utf-8")

            # encrypt using secret key
            datae = hmac.new(self.secret, datab, hashlib.sha384).hexdigest()

            # create header
            header = {}
            header["X-BFX-APIKEY"] = self.apiKey
            header["X-BFX-PAYLOAD"] = datab
            header["X-BFX-SIGNATURE"] = datae

            r = requests.get("{:s}/{:s}".format(self.url, key), data={}, headers=header)
        except requests.exceptions.ConnectionError:
            print "failed to resolve bitfinex.com"
        try:
            j = json.loads(r.text)
        except Exception, e:
            print "failed to fetch data from bitfinex.com"
            print str(e)
        return j

if __name__ == "__main__":
    # ugly, but only for testing puporse 
    import sys, os
    sys.path.append(os.path.dirname("../"))
    from config import Config

    bitfinex = Bitfinex(Config)
    print "fetch wallet"
    wallets = bitfinex.fetchData()
    print wallets
