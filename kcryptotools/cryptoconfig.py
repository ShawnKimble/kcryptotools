# Contains crypto specific parameters 


SUPPORTED_CRYPTOS   = ['bitcoin','litecoin','dogecoin']
PROTOCOL_VERSION    = {'bitcoin': 70001,'litecoin': 70002,'dogecoin':70003}
MSG_MAGIC_BYTES     = {'bitcoin':'\xf9\xbe\xb4\xd9','litecoin':'\xfb\xc0\xb6\xdb','dogecoin':'\xc0\xc0\xc0\xc0'} 
PORT                = {'bitcoin':8333,'litecoin':9333,'dogecoin':22556}
                       # from net.cpp / bitcoin source
DNS_SEEDS           = {'bitcoin' : ['dnsseed.bluematt.me','bitseed.xf2.org','seed.bitcoin.sipa.be','dnsseed.bitcoin.dashjr.org'],
                       # from net.cpp / litecoin souce  
                       'litecoin': ["dnsseed.litecointools.com","dnsseed.litecoinpool.org","dnsseed.ltc.xurious.com",
                                    "dnsseed.koin-project.com","dnsseed.weminemnc.com"],
                       # from chainparams.cpp / dogecoin source 
                       'dogecoin': ["seed.dogecoin.com","seed.mophides.com","seed.dglibrary.org","seed.dogechain.info"]
                      }

