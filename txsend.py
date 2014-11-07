# USAGE:
# python txsend.py <crypto> <transaction1 in hex> <transaction2 in hex> ...
#

import sys
import socket
import cryptoconfig
import peersockets

def txsend(crypto,tx_list):
    if crypto not in cryptoconfig.SUPPORTED_CRYPTOS:
        raise Exception("Crypto {} not supported, suppored cryptos are {}".format(crypto,cryptoconfig.SUPPORTED_CRYPTOS))
 
    handler=peersockets.PeerSocketsHandler(tx_list)
    for address in cryptoconfig.DNS_SEEDS[crypto]:
        handler.create_peer_socket(address)

    while 1:
        handler.run()
 
def main():

    crypto = sys.argv[1].lower()
    tx_list=[]
    if len(sys.argv)>2:
        for i in range(2,len(sys.argv)):
            tx_list.append(sys.argv[i])        
    
    txsend(crypto,tx_list)

if __name__ == "__main__":
    main()
