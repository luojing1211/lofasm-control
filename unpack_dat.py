#filename: unpack_dat.py
#unpack_dat.py is meant to be a library of functions to be used to unpack and reduce 
# the raw network data being dumped by the LoFASM ROACH board's LoFASM Baseband Recording
# Firmware. 

import struct,sys
import numpy as np
import ten_gbe_lib as tg


#############################################################3
#Begin class:lofasm_packet
class lofasm_packet:
    
            
    def __init__(self,ack=0,pkt=0):
        # When an instance of lofasm_packet is created with the default setting of pkt
        #   then the class 'constructor' will simulate a LoFASM Packet instance 
        #   with the data array filled with zeros. I expect that instead of zeros
        #   we will want to perform padding with something more statistically significant
        if pkt==0:
            #if no data, then pad with zeros
            #currently, a LoFASM network packet contains two 'streams'
            #with 2048 elements in each.
            self.iDataStream = [1e-16]*2048
            self.qDataStream = [1e-16]*2048
            self.typeOfPacket = "Zero Padding"
            self.hdr_version = 600
            self.ack_num = ack + 100 #code for "this is a padded packet"

        else: #pkt != 0
            #if pkt is populated then real data exists that needs to be converted to 
            # our LoFASM data type
            
            #extract each 64bit word into an array
            #self.word_array = word_array = self.extract_words(pkt) #type <list> : 
            word_array = self.extract_words(pkt)                #var_type : <list>
            self.typeOfPacket = "Data Packet"                   #set packet type
            
            #iStream = []                                        #set to empty list
            #qStream = []                                        #set to empty list..to be appended to below
            self.iDataStream = []                               #set to empty list
            self.qDataStream = []                               #set to empty list...i don't think these are needed
            self.stream_record = []                             #save stream id's for debugging purposes
                                                                   #we can probably do away with this 
                                                                   #or implement a smoother solution
            
            self.ack_num = (word_array[0]).get_ack_num()        #get packet's ack number from first word
  
            self.hdr_version = (word_array[0]).get_hdr_version() #get header version from first packet
            
            
            for word in word_array:                                
                                                                    #   currently [0,1] -> [I,Q]
                new_data = word.get_data()
                self.iDataStream.extend(new_data[:2])
                self.qDataStream.extend(new_data[2:])
            #ENDFOR


    def extract_words(self,pkt):
        pkt_len = len(pkt)                                  #determine packet length
        num_words = int(np.floor( float(pkt_len) / 8 ) - 1)    #num_words = N-1 since the first word 
                                                            #   will be handled individually
        word_array = []
        word_array.append(lofasm_word(pkt[:8]))             #1st word: extract first 8bytes or 64bits or one 'word'

        for i in range(num_words):
            index = (i+1)*8                                 #start at 1 and progress at 8byte intervals
            next_word = pkt[index:index+8]                  #obtain next 'word'
            word_array.append(lofasm_word(next_word))       #append new LoFASM Word to word_array
        
        return word_array                                   #return word_array type: <list> with each element being a lofasm_word instance

#end of class: lofasm_packet            
#################################################################3
#Begin class:lofasm_word

class lofasm_word:                                          #class to facilitate handling of a single 8byte word
    def __init__(self,word=0):
        if word == 0:                                         #if there is no data to process make everything zero
                                                                #this mode is not yet used in the current implementation
            self.hdr_version    = 0
            self.ack_num        = 0
            self.dsamp1         = 0
            self.dsamp2         = 0
            self.dsamp3         = 0
            self.dsamp4         = 0
        else:
            hdr_ver,ack_cnt,data =   parseWord(word)    #parse raw word and extract encapsulated info
            self.hdr_version     =   hdr_ver
            self.ack_num         =   ack_cnt
            self.dsamp1          =   data[0]                      #make sampled data part of the object
            self.dsamp2          =   data[1]
            self.dsamp3          =   data[2]
            self.dsamp4          =   data[3]           

    def get_data(self):                                         #interface methods for lofasm_word class
        return[self.dsamp1,self.dsamp2,self.dsamp3,self.dsamp4]

    def get_ack_num(self):
        return self.ack_num

    def get_hdr_version(self):
        return self.hdr_version

# end of class: lofasm_word
#####################################################################
#begin toggle
def toggle(bit):                                            #toggle a single bit
    if bit:
        return 0
    else:
        return 1
#endof: toggle

##################################################################
#begin num2bit
def num2bit(word,bit_len=16):
    '''Convert integer number to bitmap array. \nUsage: num2bit(int[,bit_len=16])
    This function returns a list (<list>).'''
    
    bit_check=[]                            #populates an array containing the value each bit reperesents
                                                #the MSB (LHS) represents 2^(N-1), where N is the number of bits.
                                                #if bit_len == 3 then bit_check == [4,2,1].
    for i in range(bit_len):
        bit_check.append(2**(bit_len-i-1))
    
    bit_stat = []                           #bitmap array to store the status of each bit.
    
    #begin for loop
    for bit in bit_check:                      
        val = bit & word                    #use AND to determine whether or not corresponding bit should be set
        if val:
            bit_stat.append(1)              #append bit status as element in bitmap array
        else: bit_stat.append(0)
    #end for loop

    return bit_stat                         #type: <list>
#endof num2bit
###################################################################
#begin bit2num
def bit2num(word,bit_len=16,twos_comp = 1):
    '''
    Convert a bitmap to an integer number. Two's Complement is assumed by default.
    Usage: bit2num(int[,bit_len=16[,twos_comp =1]])
    Returns: signed int
    '''
    num=0
    if not twos_comp:                                   #if not in two's complement form then our job is easy   
        #begin forloop
        for i in range(bit_len):                        #iterate through bitmap and assign each bit its value and add
            if word[i]:
                num += 2**(bit_len - (i+1))
        #end forloop

        return num                                      #type <int>
    elif twos_comp:                                               #if in two's complement... work a bit harder
        
        sign = word[0]                                  #retrieve sign bit
        
        
        if sign==0:                                     #if sign is unset then our job is easy again :)
            return bit2num(word[1:],bit_len=bit_len-1,twos_comp=0)


        word=word[1:]                                   #get rid of the sign bit
        bit_len -= 1                                    #bit_len decreases by one since we removed the sign bit
        
        togg_stop = None                                #stopping index for toggle sweep
        togg_set = 0                                    #var to determine whether a toggle stop point has been set
        
        i=0                                             #counter used to iterate word
        
        #begin whileloop
        while not togg_set:
            
            j=-1*(i+1)                                  #set index to LSB (right) and traverse towards MSB (left)
            
            
            if word[j]:                                 #if bit is set then record current index in togg_stop
                togg_stop = bit_len + j                 # convert to positive index
                togg_set = 1                            #toggle stop point has been set
            i+=1                                        #increment counter
        #end whileloop

        if togg_stop == 0:                              #then return 0
            #return -1*bit2num(word,bit_len = len(word),twos_comp=0)
            return 0
        else:
            for i in range(togg_stop):                  #iterate word up to the toggle stop point
                word[i] = toggle(word[i])               #flip bit
            return -1*bit2num(word,bit_len = len(word),twos_comp=0)
#end bit2num
###################################################################################  
#begin parseWord

def parseWord(word):
    '''
    Parse and extract LoFASM data from an 8 byte (64bit) binary word.
    parseWord's input, word, should be a 64bit binary string.
    parseWord assumes the following bitmap for each word:

        Zero-Based Bit Number                                  Meaning
                [00:03]                               Header/DataFormat Version               *Part of Header
                [04:07]                         ACK Number (a.k.a. Packet Identification)     *Part of Header 
                [08:63]                                         Data                          *Payload
    
    Usage: hdr_ver, ack_cnt, data = parseWord(word)
    '''
    word_num = np.array(struct.unpack('>Q',word))               #unpack data as unsigned long long (one large number)
    b14_max = long(16383) #(2**14) - 1
    b04_max = long(15)    #(2**4) - 1

    #generate bit masks data extraction
    mask={}
    mask['dsamp4'] = b14_max                   
    mask['dsamp3'] = mask['dsamp4']    << 14
    mask['dsamp2'] = mask['dsamp3']    << 14
    mask['dsamp1'] = mask['dsamp2']    << 14
    mask['ack']    = b04_max           << 56
    mask['hdr']    = mask['ack']       << 4

    #apply masks and "heterodyne" back down to sensible values
    hdr_ver_raw = (word & mask['hdr'])     >> 60
    ack_num_raw = (word & mask['ack'])     >> 56
    dsamp1_raw  = (word & mask['dsamp1'])  >> 42 
    dsamp2_raw  = (word & mask['dsamp2'])  >> 28
    dsamp3_raw  = (word & mask['dsamp3'])  >> 14
    dsamp4_raw  = (word & mask['dsamp4'])  >> 00

    hdr_ver = convert_twoscomp2int(hdr_ver_raw,4)
    ack_num = convert_twoscomp2int(ack_num_raw,4)
    dsamp1  = convert_twoscomp2int(dsamp1_raw,14)
    dsamp2  = convert_twoscomp2int(dsamp2_raw,14)
    dsamp3  = convert_twoscomp2int(dsamp3_raw,14)
    dsamp4  = convert_twoscomp2int(dsamp4_raw,14)

    data = [dsamp1,dsamp2,dsamp3,dsamp4]
    return hdr_ver,ack_cnt,data

#end parseWord
####################################################
#begin gen_next_ack
def gen_next_ack(curr_ack,lo_ack=0,hi_ack=15):                  #16bit counter -> [0,15]  
    if curr_ack >= hi_ack:                                      #if at max or higher than max allowed value, reset to low val
        return lo_ack                       
    else:
        return curr_ack + 1                                     #otherwise: increment number
#end gen_next_ack
#####################################################
#begin gen_prev_ack
def gen_prev_ack(curr_ack,lo_ack=0,hi_ack=15):                  
    if curr_ack == lo_ack:                                      #if at the lowest possible value then previous ack was max
        return hi_ack
    else:                                                       #otherwise: decrement
        return curr_ack - 1
#end gen_prev_ack
#####################################################
#begin get_ack_diff
def get_ack_diff(prev_ack,curr_ack,lo_ack=0,hi_ack=15):
    '''
    Calculate the difference (in units of ack #'s) between 
    any two ack numbers.

    get_ack_diff(prev_ack,curr_ack,lo_ack=0,hi_ack=15)
    '''
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
#end get_ack_diff
#####################################################
def gen_padded_array(pkt_array):
    padded_arr = []
    padded_arr.append(pkt_array[0])                                     #get first packet
    prev_ack = padded_arr[0].ack_num
    pkt_array_len = len(pkt_array)
    for i in range(pkt_array_len - 1):
        index = i+1
        cur_ack = pkt_array[index].ack_num
        ack_diff = get_ack_diff(prev_ack,cur_ack)
        if (not ack_diff):                                      #if ack_diff==0; no missed pkts
            padded_arr.append(pkt_array[index])
            prev_ack = gen_next_ack(prev_ack)
        elif bool(ack_diff):
            for j in range(ack_diff):
                padded_arr.append(lofasm_packet(gen_next_ack(prev_ack)))
                prev_ack = gen_next_ack(prev_ack)
            padded_arr.append(pkt_array[index])
            prev_ack = gen_next_ack(prev_ack)
    return padded_arr

#####################################################
#Begin gen_pkt_streams
def gen_pkt_streams(pkt_array):
    '''
    Iterate through pkt_array (array of lofasm_packet objects) and separate the I & Q data streams in each
    packet (each packet is an element in pkt_array) into contiguous 
    arrays of their own.

    gen_pkt_streams(pkt_array)
    '''
    data=[[],[]]    
    ilen = 0                                    # length of I data array
    qlen = 0                                    # length of Q data array
                
    for pkt in pkt_array:                       
        (data[0]).extend(pkt.iDataStream)       #extract and append I Data Stream
        (data[1]).extend(pkt.qDataStream)       #extract and append Q Data Stream
        ilen+=len(pkt.iDataStream)              #increment lengths
        qlen+=len(pkt.qDataStream)
    #print "Generated I-Stream: %i Values" % ilen
    #print "Generated Q-stream: %i Values" % qlen
    #print str(len(data[0]))+" "+str(len(data[1]))
    return data
#end: gen_pkt_streams
#####################################################
#begin convert_twoscomp2int
def convert_twoscomp2int(word,num_bits):
    try:
        mask = [2**i for i in range(num_bits)]
    
        #get MSbit value first
        total = -1 * isset(mask[num_bits-1]&word) * (2**(num_bits-1)) \
         + sum([(isset(mask[i] & word) * (2**i)) for i in range(num_bits-1)])
    except GeneralError as err:
        print "unpack_dat/binParseWordTC: excepted GeneralError!"
    return total
#end convert_twoscomp2int
#####################################################
#begin isset
def isset(val):
    return 1 if val>0 else 0
#end isset
#####################################################