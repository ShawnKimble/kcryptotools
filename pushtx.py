# USAGE:
# python pushtx.py <crypto> <number of peers to send tx to> <transaction1 in hex> <transaction2 in hex> ...
#

import sys
import socket
import cryptoconfig
import peersockets

def pushtx(crypto,num_peers_to_send,tx_list):
    if crypto not in cryptoconfig.SUPPORTED_CRYPTOS:
        raise Exception("Crypto {} not supported, suppored cryptos are {}".format(crypto,cryptoconfig.SUPPORTED_CRYPTOS))
 
    handler=peersockets.PeerSocketsHandler(tx_list)
    for address in cryptoconfig.DNS_SEEDS[crypto]:
        handler.create_peer_socket(address)

    while 1:
        handler.run()
        if handler.get_num_active_peers() >= num_peers_to_send:
            return 
def main():

    crypto              = sys.argv[1].lower()
    num_peers_to_send   = int(sys.argv[2])
    tx_list=[]
    if len(sys.argv)>3:
        for i in range(3,len(sys.argv)):
            tx_list.append(sys.argv[i])        
    
    pushtx(crypto,num_peers_to_send,tx_list)

if __name__ == "__main__":
    main()
