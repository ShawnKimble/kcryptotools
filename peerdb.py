import sqlite3


class PeerMemDB(object):
    def __init__(self):
        # dict with address as key and a list containing tuple
        # (int_key,timestamp), int key:0=initialized, 1=open, 2=closed
        self.address_dict={}
    def add_initialized_address(self,address,timestamp):
        self._add_address(address,timestamp,0)

    def add_opened_address(self,address,timestamp):
        self._add_address(address,timestamp,1)

    def add_closed_address(self,address,timestamp):
        self._add_address(address,timestamp,2)

    def _add_address(self,address,timestamp,opened):
         if address in self.address_dict:
            self.address_dict[address].append((timestamp,opened))
         else:
            self.address_dict[address]=[(timestamp,opened)]
    def is_closed(self,address):
        if address not in self.address_dict:
            return True
        else:
            #return the last open status of the address
            return self.address_dict[address][-1][1]==2
 
    def is_initialized(self,address):
        if address not in self.address_dict:
            return False
        else:
            #return the last open status of the address
            return self.address_dict[address][-1][1]==0
 
    def is_open(self,address):
        if address not in self.address_dict:
            return False
        else:
            #return the last open status of the address
            return self.address_dict[address][-1][1]==1
  


# Stores Tx hash by address and earliest timestamp 
class TxMemDB(object):
    def __init__(self):
        #dict where first key is address,second key is tx hash
        #value is timestamp when the tx was first received
        self.tx_dict={}

    #only earliest timestamp is stored, newer timestamps will overwrite
    #older timestamps
    def add(self,address,tx_hash,timestamp):
        tx_dict_key = (address,tx_hash)
        if tx_dict_key in self.tx_dict:
            if self.tx_dict[tx_dict_key] > timestamp:
                self.tx_dict[tx_dict_key] =timestamp
        else:
            self.tx_dict[(address,tx_hash)]=timestamp
    # return true if address and tx_hash is contained in TxMemDB,
    # false otherwise
    def has(self,address,tx_hash): 
        return (address,tx_hash) in self.tx_dict

    #dump data to peerDB and clear internal contents
    def dump(self,peerdb):
        self.tx_dict={}
        pass

class PeerDB(object):
    
    def __init__(self):
        self.conn=sqlite3.connect('peerdatabase.db')
        self.cursor=self.conn.cursor()
        #This contains all record of opened and closed connections to peers
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS connections (address,timestamp,opened)')
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS tx_broadcasts (address,timestamp,tx_hash')
        self.conn.commit()
    def __del__(self):
        self.conn.close()
    def add_opened_connection(self,address,timestamp):
        self.cursor.execute('INSERT INTO connections VALUES (?,?,?)',
            (address,timestamp,True))
    def add_closed_connection(self,address,timestamp):
        self.cursor.execute('INSERT INTO connections VALUES (?)',
            (address,timestamp,False))     
    def commit(self):
        self.conn.commit()
        
    # a peer broadcast of a tx 
    def add_tx_brodcast(self,address,timestamp,tx_hash):
        self.cursor.execute('INSERT INTO connections VALUES (?,?,?)',(address,timestamp,tx_hash))
