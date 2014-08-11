v 0.0 

INTRODUCTION:
BTConnect is a python program designed to connect to the bitcoin network, talk to peers, and gather information. 
It is not a full node, as it does not have any knowledge regarding the blockchain. Some of the code in btconnect.py 
is taken from Caesure by Sam Rushing (https://github.com/samrushing/caesure). This software is a work in progress...

Tested only with Python 2.7 under Ubuntu 12.04 

FEATURES:
Connect to Bitcoin nodes 
Keep track of transactions that are broadcast
Broadcast transactions 

USAGE:
python txsend.py <transaction1 in hex> <transaction2 in hex> ...

This will connect to bitcoin nodes and broadcast the transactions in hex. Note that there is no check done on 
the transaction's validity, so this is useful for sending some transactions that would be labeled as invalid by
bitcoind (tx's utilizing OP_RETURN). It will run indefinitely , so should be manually closed after transaction has
been broadcast to several nodes.

TODO:
put peer version information in database
