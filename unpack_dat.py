import struct,sys
import numpy as np
import ten_gbe_lib as tg



class lofasm_packet:
    
            
    def __init__(self,ack=0,pkt=0):
        if pkt==0:
            #if no data, then pad with zeros
            self.iDataStream = [1e-16]*2048
            self.qDataStream = [1e-16]*2048
            self.typeOfPacket = "Zero Padding"
            #print "Adding " + self.typeOfPacket
            self.hdr_version = 600
            
            
            self.ack_num = ack + 100 #code for "this is a padded packet"
        else:   
            self.word_array = word_array = self.extract_words(pkt)
            self.typeOfPacket = "Data Packet"
            #print "Adding " + self.typeOfPacket
            self.iDataStream = []
            self.qDataStream = []
            self.stream_record = []
            iStream = []
            qStream = []
            for word in word_array:
                input_stream = word.get_stream_id()
                self.stream_record.append(input_stream)
                if input_stream == 0:
                    iStream.extend(word.get_data())
                else:
                    qStream.extend(word.get_data())
            self.ack_num = (word_array[0]).get_ack_num()
  
            self.hdr_version = (word_array[0]).get_hdr_version()
            self.iDataStream = iStream
            self.qDataStream = qStream

    def extract_words(self,pkt):
        pkt_len = len(pkt)
        num_words = (pkt_len / 8 )-1
        word_array = []
        word_array.append(lofasm_word(pkt[:8])) #1st word
        for i in range(num_words):
            index = (i+1)*8
            next_word = pkt[index:index+8]
            word_array.append(lofasm_word(next_word))
        
        return word_array

            
                        
            
class lofasm_word:
    def __init__(self,word=0):
        if word==0:
            self.stream_id = 0
            self.hdr_version = 0
            self.ack_num = 0
            self.dsamp1 = 0
            self.dsamp2 = 0
            self.dsamp3 = 0
            self.dsamp4 = 0
        else:
            stream_id,hdr_ver,ack_cnt,data = parseWord(word)
            self.stream_id = stream_id
            self.hdr_version = hdr_ver
            self.ack_num = ack_cnt
            self.dsamp1 = data[0]
            self.dsamp2 = data[1]
            self.dsamp3 = data[2]
            self.dsamp4 = data[3]           

    def get_data(self):
        return[self.dsamp1,self.dsamp2,self.dsamp3,self.dsamp4]
    def get_ack_num(self):
        return self.ack_num
    def get_hdr_version(self):
        return self.hdr_version
    def get_stream_id(self):
        return self.stream_id
def toggle(bit):
    if bit:
        return 0
    else:
        return 1
def num2bit(word,bit_len=16):
    bit_check=[]
    for i in range(bit_len):
        bit_check.append(2**(bit_len-i-1))
    
    bit_stat = []
    for bit in bit_check:
        val = bit & word
        if val:
            bit_stat.append(1)
        else: bit_stat.append(0)
    return bit_stat
          
def bit2num(word,bit_len=16,twos_comp = 1):
    num=0
    if not twos_comp:    
        for i in range(bit_len):
            if word[i]:
                num += 2**(bit_len - (i+1))
        return num 
    else:
        sign = word[0]
        if sign==0:
            return bit2num(word[1:],bit_len=bit_len-1,twos_comp=0)
        word=word[1:] #get rid of the sign bit
        togg_stop = None
        togg_set = 0
        bit_len -= 1
        #index of -1 is equal to index of bit_len-1
        i=0
        while not togg_set:
            #print "i",i
            sys.stdout.flush()
            
            j=-1*(i+1)
            #print "j",j
            #print 'word[j]',word[j]
            if word[j]: 
                togg_stop = bit_len + j
                togg_set = 1
            i+=1
        
        if togg_stop == 0:
            return -1*bit2num(word,bit_len = len(word),twos_comp=0)
        else:
            for i in range(togg_stop):
                word[i] = toggle(word[i])
            return -1*bit2num(word,bit_len = len(word),twos_comp=0)
                
def parseWord(word):
    #bit map
    #0: stream id
    #1-3: hdr_ver
    #4-7: ack_cnt
    #8-63: data
    word_num = np.array(struct.unpack('>Q',word)) 
    word_bitmap = num2bit(word_num,bit_len=64)
    hdr_bitmap = word_bitmap[:8]
    data_bitmap = word_bitmap[8:]
    
    stream_id = hdr_bitmap[0]
    hdr_ver_bitmap = hdr_bitmap[1:4]
    ack_cnt_bitmap = hdr_bitmap[4:]
    snap_bitmap = []
    snap_bitmap.append(data_bitmap[:14])
    snap_bitmap.append(data_bitmap[14:28])
    snap_bitmap.append(data_bitmap[28:42])
    snap_bitmap.append(data_bitmap[42:])

    #print stream_id
    #print hdr_ver_bitmap
    #print ack_cnt_bitmap
    #print len(snap_bitmap[0])
    hdr_ver = bit2num(hdr_ver_bitmap,bit_len=3,twos_comp=0)
    ack_cnt = bit2num(ack_cnt_bitmap,bit_len=4,twos_comp=0)
    data=[[]]*4
    
    for i in range(4):
        data[i] = bit2num(snap_bitmap[i],bit_len=14)
    return stream_id,hdr_ver,ack_cnt,data
####################################################
def gen_next_ack(curr_ack,lo_ack=0,hi_ack=15): 
    if curr_ack >= hi_ack:
        return lo_ack
    else:
        return curr_ack + 1
def gen_prev_ack(curr_ack,lo_ack=0,hi_ack=15):
    if curr_ack == lo_ack:
        return hi_ack
    else:
        return curr_ack - 1
def get_ack_diff(prev_ack,curr_ack,lo_ack=0,hi_ack=15):
    if curr_ack == gen_next_ack(prev_ack,lo_ack,hi_ack):
        return 0
    else:
        mis_pkts = 0
        done=0
        prev_ack = gen_next_ack(prev_ack,lo_ack,hi_ack)
        while (not done):
            if prev_ack == curr_ack:
                done = 1
            else:
                prev_ack = gen_next_ack(prev_ack,lo_ack,hi_ack)
                mis_pkts+=1
        return mis_pkts
def gen_padded_array(pkt_array):
    padded_arr = []
    padded_arr.append(pkt_array[0]) #get first packet
    prev_ack = padded_arr[0].ack_num
    pkt_array_len = len(pkt_array)
    for i in range(pkt_array_len - 1):
        index = i+1
        cur_ack = pkt_array[index].ack_num
        ack_diff = get_ack_diff(prev_ack,cur_ack)
        if (not ack_diff): #if ack_diff==0; no missed pkts
            padded_arr.append(pkt_array[index])
            prev_ack = gen_next_ack(prev_ack)
        elif bool(ack_diff):
            for j in range(ack_diff):
                padded_arr.append(lofasm_packet(gen_next_ack(prev_ack)))
                prev_ack = gen_next_ack(prev_ack)
            padded_arr.append(pkt_array[index])
            prev_ack = gen_next_ack(prev_ack)
    return padded_arr

def gen_pkt_streams(pkt_array):
    data=[[],[]]    
    ilen = 0
    qlen = 0
    
    for pkt in pkt_array:
        (data[0]).extend(pkt.iDataStream)
        (data[1]).extend(pkt.qDataStream)
        ilen+=len(pkt.iDataStream)
        qlen+=len(pkt.qDataStream)
    print "Generated I-Stream: %i Values" % ilen
    print "Generated Q-stream: %i Values" % qlen
    #print str(len(data[0]))+" "+str(len(data[1]))
    return data
