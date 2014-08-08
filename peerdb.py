import sqlite3
import time 

DEFAULT_DISK_DB_LOCATION='peerdatabase.db'


# This contains information about connections to peer, when they were opened/initialized/closed

class PeerMemDB(object):
    def __init__(self):
        # dict with address as key and a list containing tuple
        # (timestamp,int key,info string), 
        # int key:0=closed, 1=initialized, 2=opened
        # timestamp - when event happened
        # info string - reason for the event happening (NOT IMPLEMENTED)
        self.address_dict={}
     
        self.conn=sqlite3.connect(DEFAULT_DISK_DB_LOCATION)
        self.cursor=self.conn.cursor()
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS connections (address,timestamp,opened)')
        self.conn.commit()

    def get_address_from_disk(self): 
        self.cursor.execute('SELECT DISTINCT address FROM connections')
        return self.cursor.fetchall()
    def add_initialized_address(self,address):

        self._add_address(address,time.time(),1)

    def add_opened_address(self,address):
        self._add_address(address,time.time(),2)

    def add_closed_address(self,address):
        self._add_address(address,time.time(),0)

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
            return self.address_dict[address][-1][1]==0
 
    def is_initialized(self,address):
        if address not in self.address_dict:
            return False
        else:
            #return the last open status of the address
            return self.address_dict[address][-1][1]==1
 
    def is_open(self,address):
        if address not in self.address_dict:
            return False
        else:
            #return the last open status of the address
            return self.address_dict[address][-1][1]==2
  
    # we want to remove all currently closed addresses to disk
    # and trim opened and initialized ones to the last entry
    def dump_to_disk(self):
        for address in self.address_dict:
            for status_tuple in self.address_dict[address]:
                int_key=status_tuple[1]
                timestamp=status_tuple[0]
                self.cursor.execute('INSERT INTO connections VALUES (?,?,?)',
                    (address,timestamp,int_key))
            #remove all but the most up to date element in the address_dict 
            self.address_dict[address]= self.address_dict[address][-1] 
    
        self.conn.commit()

class BlockMemDB(object):
    def __init__(self):
        self.block_dict={} 

# Stores Tx hash by address and earliest timestamp 
class TxMemDB(object):
    def __init__(self):
        #dict where first key is address,second key is tx hash
        #value is timestamp when the tx was first received
        self.tx_dict={}

        self.conn=sqlite3.connect(DEFAULT_DISK_DB_LOCATION)
        self.cursor=self.conn.cursor()
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS tx_broadcasts (address,timestamp,tx_hash)') 
        self.conn.commit()
 
    #only earliest timestamp is stored, newer timestamps will overwrite
    #older timestamps
    def add(self,address,tx_hash):
        timestamp=time.time()
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

    # dump data to disk and clear internal contents
    # when dumping data to disk,the disk will remove any 
    # tx that is a duplicate 
    def dump_to_disk(self):
        for tx_tuple in self.tx_dict:
            address=tx_tuple[0]
            tx_hash=tx_tuple[1]
            timestamp=self.tx_dict[tx_tuple]
            self.cursor.execute('INSERT INTO tx_broadcasts VALUES (?,?,?)',
                    (address,timestamp,tx_hash))
      
        self.conn.commit()
        #erase tx_dict
        self.tx_dict={}

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
    def add_opened_connection(self,address):
        timestamp=time.time()
        self.cursor.execute('INSERT INTO connections VALUES (?,?,?)',
            (address,timestamp,True))
    def add_closed_connection(self,address):
        timestamp=time.time()
        self.cursor.execute('INSERT INTO connections VALUES (?)',
            (address,timestamp,False))     
    def commit(self):
        self.conn.commit()
        
    # a peer broadcast of a tx 
    def add_tx_brodcast(self,address,timestamp,tx_hash):
        self.cursor.execute('INSERT INTO connections VALUES (?,?,?)',(address,timestamp,tx_hash))
