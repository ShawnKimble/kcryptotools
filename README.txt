BTConnect is a python program designed to connect to the bitcoin network, talk to peers, and gather information. 
It is not a full node, as it does not have any knowledge regarding the blockchain. Some of the code in btconnect.py 
is taken from Caesure by Sam Rushing (https://github.com/samrushing/caesure)

PeerSocket class represents a connection to a peer

PeerSocketsHandler handles multiple PeerSocket objects in an asynchronous manner

XXXX_MemDB are in-memory database classes that store relevant information in memory
    and dumps them to disk when necessary

BTConnect_DB is the in disk memory class 

TODO:
put tx broadcast capability 
put peer version information in database
