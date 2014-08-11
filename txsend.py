import sys
from peersockets import *

def main():

    # resolve seeds 
    address_list=[]
    for seed in DNS_SEEDS:
        try:
            cur_address=socket.gethostbyname(seed)
            address_list.append(cur_address)
        except:
            print("failed to resolve {}".format(seed))

    tx_list=[]
    if len(sys.argv)>=2:
        for i in range(1,len(sys.argv)):
            tx_list.append(sys.argv[i])        
 
    handler=PeerSocketsHandler(tx_list)
    for address in address_list:
        handler.create_peer_socket(address)

    while 1:
        handler.run()

if __name__ == "__main__":
    main()
