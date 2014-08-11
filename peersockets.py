import struct 
import socket
import select
import time
from hashlib import sha256
import peerdb

VERSION=70001
BITCOIN_MAGIC = '\xf9\xbe\xb4\xd9'
NONCE = 1 
SOCKET_BLOCK_SECONDS=0 #None means blocking calls, 0 means non blocking calls
PORT=8333
TCP_RECV_PACKET_SIZE=4096
MSGHEADER_SIZE=24
DNS_SEEDS=['dnsseed.bluematt.me','bitseed.xf2.org','seed.bitcoin.sipa.be','dnsseed.bitcoin.dashjr.org']
USER_AGENT='/BTCONNECT:0001/'#BIP 14

# Handle multiple peer sockets
class PeerSocketsHandler(object):
    
    # tx_broadcast_list is a list of transactions in hex string (i.e, '03afb8..')
    def __init__(self,tx_broadcast_list=[]):
        self.peer_memdb=peerdb.PeerMemDB()
        self.tx_memdb=peerdb.TxMemDB()

        self.my_ip=self._get_my_ip()
        self.poller =select.poll()
        self.fileno_to_peer_dict={}
        self.tx_dict={} #dict of received transcations, key = hash , value=tuple(timestamp first recieved,address)
        self.tx_broadcast_list=tx_broadcast_list #list of tx to broadcast          

    def __del__(self):
        self.peer_memdb.dump_to_disk()
        self.tx_memdb.dump_to_disk()

    # function to get my current ip, 
    def _get_my_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("gmail.com",80))
        out= s.getsockname()[0]
        s.close()
        #for connecting to bitcoind on same machine
        #out= socket.gethostbyname(socket.gethostname())
        return out

    #create new peer socket at address
    def create_peer_socket(self,address):
        try:
            peer=PeerSocket()
            peer.connect(address)
            print("establishing connection to:",address)
        except IOError as e:
            print ("I/O error({0}): {1}".format(e.errno, e.strerror))
            print("could not connect to:",address)
            return False  
        self.fileno_to_peer_dict[peer.get_socket().fileno()]=peer 
        self.peer_memdb.add_initialized_address(address)
        eventmask=select.POLLIN|select.POLLPRI|select.POLLOUT|select.POLLERR|select.POLLHUP|select.POLLNVAL
        self.poller.register( peer.get_socket().fileno(),eventmask)
        return True 
      
    def remove_peer_socket(self,peer):
        #unregister and remove from dictionary 
        fileno=peer.get_socket().fileno()
        address=peer.get_address()
        self.poller.unregister(fileno)
        self.peer_memdb.add_closed_address(address)
        del self.fileno_to_peer_dict[fileno]
   
    def get_num_active_peers(self):
        return len(self.fileno_to_peer_dict)


    # poll peer sockets and do stuff if there is data
    def run(self): 
        events=self.poller.poll()
        for event in events:
            poll_result=event[1]
            fileno=event[0]
            current_peer=self.fileno_to_peer_dict[fileno]
            if(poll_result & select.POLLOUT): #ready for write (means socket is connected)
                print(fileno," ready to write")
                self.peer_memdb.add_opened_address(current_peer.get_address())
                #don't check for POLLOUT anymore, since we know it is connected 
                self.poller.modify(fileno,
                    select.POLLIN|select.POLLPRI|select.POLLERR|select.POLLHUP|select.POLLNVAL) 
                # initialize by sending version 
                if not current_peer.get_is_active():
                    print("connection established to",current_peer.address)
                    current_peer.send_version(self.my_ip)
                    current_peer.set_is_active(True)
                    print("Sent version")
                    print("active peers:",self.get_num_active_peers())
                # broadcast tx 
                for tx in self.tx_broadcast_list:
                    was_broadcast=current_peer.broadcast(tx)# this will not broadcast more than once
                    if was_broadcast:
                        print("Tx has been broadcast: {}".format(tx))

            if(poll_result & select.POLLIN):#ready for read( packet is available)
                current_peer.recv()
            
                #check new addresses we got from the peer and try to connect 
                while len(current_peer.peer_address_list) > 0 :
                    address=current_peer.peer_address_list.pop()
                    if( self.peer_memdb.is_closed(address)):
                        self.create_peer_socket(address)
                    else:
                        print("found already connected peer")
                #check new tx and add to db 
                while len(current_peer.tx_hash_list) > 0 :
                    tx_hash=current_peer.tx_hash_list.pop()
                    self.tx_memdb.add(current_peer.get_address(),tx_hash)

            if(poll_result & select.POLLPRI): #urgent data to read
                print("URGENT READ")
            if(poll_result & select.POLLERR): #Error condition
                print("ERROR CONDITION on %d"%(fileno))
            if(poll_result & select.POLLHUP): #hung up
                print("HUNG UP detected on %d"%(fileno))
                print('valid bytes:', current_peer.total_valid_bytes_received,
                    'junk bytes:',current_peer.total_junk_bytes_received)            
                self.remove_peer_socket(current_peer)
            if(poll_result & select.POLLNVAL): #invalid request, unopen descriptor
                print("INVALID REQUEST")
                self.remove_peer_socket(current_peer)

class PeerSocket(object):
    
    def __init__(self):
        self.is_active=False
        self.address=''
        self.peer_address_list=[]
        self.tx_hash_list=[] #list of received tx hashes
        #dictionary where key is hash of tx we want to broadcast and value is tx
        #only contains tx's that have been broacast already using broadcast() function 
        self.broadcast_tx_dict={} 
        self.recv_buffer=''
        self.expected_msg_size=0
        self.version=''
        self.total_valid_bytes_received=0 
        self.total_junk_bytes_received=0

    def __del__(self):
        self.my_socket.close()

    def set_is_active(self,truefalse):
        self.is_active=truefalse

    def get_address(self):
        return self.address

    def connect(self,address):
        self.address=address
        if('.' in address):
            socket_type=socket.AF_INET
        elif(':' in address):
            socket_type=socket.AF_INET6
        else:
            raise Exception("Unexpected address: "+address)
        self.my_socket=socket.socket(socket_type, socket.SOCK_STREAM)
        self.my_socket.settimeout(SOCKET_BLOCK_SECONDS)
        try:
            if(socket_type==socket.AF_INET): 
                self.my_socket.connect((address,PORT)) 
            else:
                self.my_socket.connect((address,PORT,0,0))
        except IOError as e:
            # 115 == Operation now in progress EINPROGRESS, this is expected
            if e.errno !=115: 
                return False
        return True 

    def get_socket(self):
        return self.my_socket
  
    def get_packet(self):

        if( len(self.recv_buffer) >= MSGHEADER_SIZE):
            data_length=get_length_msgheader(self.recv_buffer)
            self.expected_msg_size=data_length+MSGHEADER_SIZE
            #if valid command is not contained, packet will be thrown out 
            if check_if_valid_command(self.recv_buffer)==False:
                print('Invalid command:',get_command_msgheader(self.recv_buffer))
                self.total_junk_bytes_received+=len(self.recv_buffer)
                self.expected_msg_size=0
                self.recv_buffer=''
                return '' 
        try:
            self.recv_buffer+=self.my_socket.recv(TCP_RECV_PACKET_SIZE)
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
            return ''  

        #if entire message is assembled exactly, return it
        if(len(self.recv_buffer) >= self.expected_msg_size and self.expected_msg_size !=0):
            self.total_valid_bytes_received+=self.expected_msg_size
            out=self.recv_buffer[0:self.expected_msg_size]
            self.recv_buffer=self.recv_buffer[self.expected_msg_size:]
            self.expected_msg_size=0            
            return out 
            
        #otherwise output is not ready, return empty string
        else:
            return '' 
           
    def get_is_active(self):
        return self.is_active 

    #send a ping pong to verify connection
    def verify_connection(self):
        data = struct.pack('<Q',NONCE)
        self._send_packet('ping',data)
        data=self.my_socket.recv(1024)
        
        return process_pong(data)

    def send_version(self,my_ip):
        data = struct.pack ('<IQQ', VERSION, 1, int(time.time()))
        data += pack_net_addr ((1, (my_ip, PORT)))
        data += pack_net_addr ((1, (self.address, PORT)))
        data += struct.pack ('<Q',NONCE)
        data += pack_var_str (USER_AGENT)
        start_height = 0
        #ignore bip37 for now - leave True
        data += struct.pack ('<IB', start_height, 1)
        self._send_packet ('version', data)

    def _send_packet(self,command, payload):
        lc = len(command)
        assert (lc < 12)
        cmd = command + ('\x00' * (12 - lc))
        h = dhash (payload)
        checksum, = struct.unpack ('<I', h[:4])
        packet = struct.pack ('<4s12sII',
            BITCOIN_MAGIC,cmd,len(payload),checksum) + payload
        try:
            self.my_socket.send (packet)
        except IOError as e:
            print("Send packet I/O error({0}): {1}".format(e.errno, e.strerror))
            return False
        return True

    # unused
    def send_getaddr(self):
        self.send_getaddr_packet(self.my_socket)  

    # unused
    def send_getaddr_packet(conn):
        data = struct.pack('0c')
        self._send_packet('getaddr',data)   

    def _send_tx(self,tx_hash):
        # send only if we have tx_hash 
        if tx_hash in self.broadcast_tx_dict:

            print("send_tx initialized")
            data=self.broadcast_tx_dict[tx_hash]
            self._send_packet('tx',data)
       
    def recv(self):
        data=self.get_packet()
        if(len(data)!=0):
            self.process_data(data)
            return True
        else:
            return False

    # return True, if we broadcast, False if already has been
    # broadcast. tx is expected to be a hex string, i.e. '02aba8...'
    def broadcast(self,tx):
        tx=tx.decode('hex')
        tx_hash=dhash(tx) #need to hash here
        # we only broadcast if tx is new 
        if tx_hash not in self.broadcast_tx_dict:
            self.broadcast_tx_dict[tx_hash]=tx
            data =  pack_var_int(1) 
            data += struct.pack('<I32s',1,tx_hash) #MSG_TX
            self._send_packet('inv',data)
            return True
            # we will receive getdata (make sure we have hash) 
            # and process_ata will send_tx
        return False

    def process_data(self,data):
        if compare_command(data,"getaddr"): #get known peers
            pass
        elif compare_command(data,"addr"):#in reponse to getaddr
            self._process_addr(data)
        elif compare_command(data,"version"):
            pass
        elif compare_command(data,"verack"):
            pass
        elif compare_command(data,"inv"): #advertise knowledge of tx or block
            self._process_inv(data)
        elif compare_command(data,"getblocks"):#request an inv packet for blocks
            pass
        elif compare_command(data,"getheaders"):#request headers
            pass
        elif compare_command(data,"headers"):#return header in reponse to getheader
            pass
        elif compare_command(data,"getdata"):#get data from peer after broadcasting tx via inv
            self._process_get_data(data)  
        elif compare_command(data,"notfound"):#not found is sent after getdata recieved
            pass
        elif compare_command(data,"block"):#describe a block in reponse to getdata
            pass
        elif compare_command(data,"tx"):#describe a transaction in repones to getdata
            pass
        elif compare_command(data,"pong"):#response to ping
            pass
        elif compare_command(data,"ping"):#query if tcp ip is alive
            pass
        else:
            print("unhandled command recieved:",get_command_msgheader(data))

    def _process_get_data(self,data):
        payload         =   get_payload(data)
        varint_tuple    =   read_varint(payload)
        num_invs        =   varint_tuple[0]
        varint_size     =   varint_tuple[1]
        inv_data        =   payload[varint_size:]         
        for i in range(0,num_invs):
            begin_index=i*36
            end_index=begin_index+36
            inv_type = struct.unpack('<I',inv_data[begin_index:begin_index+4])[0]
            inv_hash = struct.unpack('32c',inv_data[begin_index+4:begin_index+36])
            if(inv_type ==0):#error
                pass
            elif(inv_type==1):#tx
                tx_hash=''.join(inv_hash) #convert tuple to string
                print("type inv_hash",type(inv_hash))
                print("type tx_hash",type(tx_hash))
                print("getdata received for tx hash:{}".format(tx_hash))
                self._send_tx(tx_hash)
            elif(inv_type==2):#block
                pass 
            else:
                print("unknown inv")

    def _process_addr(self,data):
        payload         =   get_payload(data)
        varint_tuple    =   read_varint(payload)
        num_ips         =   varint_tuple[0]
        varint_size     =   varint_tuple[1]
        ip_data         =   payload[varint_size:] 
        for i in range(0,num_ips):
            begin_index=i*30
            end_index=begin_index+30
            timestamp = struct.unpack('<I',ip_data[begin_index:begin_index+4])[0]
            services = struct.unpack('<Q',ip_data[begin_index+4:begin_index+12])[0]
            ipv6= struct.unpack('16c',ip_data[begin_index+12:begin_index+28])[0]
            ipv4= struct.unpack('4c',ip_data[begin_index+24:begin_index+28])[0]
            port=struct.unpack('!H',ip_data[begin_index+28:begin_index+30])[0]
            print("recieved address:", socket.inet_ntop(socket.AF_INET,ip_data[begin_index+24:begin_index+28]))    
            self.peer_address_list.append(socket.inet_ntop(socket.AF_INET,ip_data[begin_index+24:begin_index+28])) 

    def _process_inv(self,data):
        payload         =   get_payload(data)
        varint_tuple    =   read_varint(payload)
        num_invs        =   varint_tuple[0]
        varint_size     =   varint_tuple[1]
        inv_data        =   payload[varint_size:]
        for i in range(0,num_invs):
            begin_index=i*36
            end_index=begin_index+36
            inv_type = struct.unpack('<I',inv_data[begin_index:begin_index+4])[0]
            inv_hash = struct.unpack('32c',inv_data[begin_index+4:begin_index+36])
            if(inv_type ==0):#error
                pass
            elif(inv_type==1):#tx
                self._process_inv_tx(inv_hash)
            elif(inv_type==2):#block
                self._process_inv_block(inv_hash)
            else:
                print("unknown inv")

    def _process_inv_tx(self,inv_hash):
        self.tx_hash_list.append(inv_hash) 
    def _process_inv_block(self,inv_hash):
        pass


def dhash (s):
    return sha256(sha256(s).digest()).digest()

def pack_ip_addr (addr):
    # only v4 right now
    # XXX this is probably no longer true, the dns seeds are returning v6 addrs
    return socket.inet_pton (socket.AF_INET6, '::ffff:%s' % (addr,))

def pack_var_int (n):
    if n < 0xfd:
        return chr(n)
    elif n < 1<<16:
        return '\xfd' + struct.pack ('<H', n)
    elif n < 1<<32:
        return '\xfe' + struct.pack ('<I', n)
    else:
        return '\xff' + struct.pack ('<Q', n)

def pack_var_str (s):
    return pack_var_int (len (s)) + s

def pack_net_addr ((services, (addr, port))):
    addr = pack_ip_addr (addr)
    port = struct.pack ('!H', port)
    return struct.pack ('<Q', services) + addr + port


#return tuple with the integer and size of varint object
def read_varint(data):
    b1=struct.unpack('<B',data[0])
    b1=b1[0]
    if(b1<0xfd):
        return (b1,1)
    elif(b1==0xfd):
        b2=struct.unpack('<H',data[1:3])
        return(b2[0],3)
    elif(b1==0xfe):
        b3=struct.unpack('<I',data[1:5])
        return(b3[0],5)
    elif(b1==0xff): #b1==0xff
        b4=struct.unpack('<Q',data[1:9])
        return(b4[0],9)
    else:
        raise Exception("varint read failed") 

def check_if_valid_command(data):
    out = (compare_command(data,"getaddr") | compare_command(data,"addr") |
        compare_command(data,"inv") | compare_command(data,"getblocks") |
        compare_command(data,"headers") | compare_command(data,"getheaders") |
        compare_command(data,"getdata") | compare_command(data,"notfound") |
        compare_command(data,"block") | compare_command(data,"tx") |
        compare_command(data,"pong") | compare_command(data,"ping") |
        compare_command(data,"version") | compare_command(data,"verack"))
        
    return out

def compare_command(data, string):  
    tuple_start=get_command_msgheader(data)
    for index,char in enumerate(string):
        if( tuple_start[index]!=char):
            return False
        
    return True


#Function to process recieved messages #

def get_magic_msgheader(data):
    return struct.unpack('<I',data[0:4])[0]
def get_command_msgheader(data):
    return struct.unpack('12c',data[4:16])
def get_length_msgheader(data):
    if(len(data)<20):
      raise Exception("data must be of length 20 at least, length is:%d"%len(data))
    return struct.unpack('<I',data[16:20])[0]
def get_checksum_msgheader(data):
    return struct.unpack('<I',data[20:24])[0]
def get_payload(data):
    return data[24:] 

#########################################
def process_pong(data):
    if(compare_command(data,"pong")):
        return True
    else:
        return False 

def process_version_handshake(socket):
    data=socket.recv(1024)
    if(compare_command(data,"version")):
        print("version message recieved")
    else:
        print("unexpected message recieved")

    data=socket.recv(1024)
    out_tuple=struct.unpack('<I12c',data[0:16]) 
    if(compare_command(data,"verack")):
        print("verack message recieved")
    else: 
        print("message type:",out_tuple[1:])


