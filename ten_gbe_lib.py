# module with useful functions for ROACH networking and development
#Author: Louis P. Dartez
import corr,sys,pcapy,datetime,struct,dpkt
from time import strftime,sleep,time
#import unpack_data as ud
import unpack_dat as ud1

######################################################
def ipStr2Bin(ip):
    ip = ip.split('.')
    ip.reverse()
    dest_ip=0
    for i in range(len(ip)):
        dest_ip += 2**(i*8) * int(ip[i])
    return dest_ip
######################################################
def pcapy_setup(): #deprecated
    BUFFER_SIZE= 9000
    DEV = 'eth2'
    PROMISCUOUS = 1
    READ_TIMEOUT = 100
    PCAP_FILTER ="ip proto \\udp"
    MAX_PKTS = 2048
    MAX_LEN = BUFFER_SIZE
    cap = pcapy.open_live(DEV,MAX_LEN,PROMISCUOUS,READ_TIMEOUT)
    cap.setfilter(PCAP_FILTER)
    sleep(.1)
    return cap
######################################################

def get_packet(sock,MAX_PKTS):
	#									SET UP VARS								#
	pkt_array = []																#
	NUM_BYTES = 9000	#MTU													#
	print "Starting capture of " + str(MAX_PKTS) +"Packet(s) \n"							#
	start = time()																#
	for i in range(MAX_PKTS):													#
	    pkt_array.append(sock.recv(NUM_BYTES))	#     acquire packets			#
	fin = time() #end capture										            #
#	sock.close()  #close network socket											#
	capture_time = fin-start													#
	print "done! packet capture took " + str(capture_time) + "s"				#
	return pkt_array,capture_time

######################################################

def config(fpga=''):
    # Configuration parameters for ROACH
    HOST = '192.168.4.21'
    
    
    #config for 10gbe interface
    FABRIC_IP = '192.168.4.10' # IP for 10GbE on ROACH
    FABRIC_IP = ipStr2Bin(FABRIC_IP)
    FABRIC_PORT = 60000 #UDP PORT for 10Gbe on ROACH
    DEST_PORT = 60001
    DEST_IP = '192.168.4.11' #IP for 10GbE NIC on Pest Control
    DEST_IP = ipStr2Bin(DEST_IP)
    # 10GbE settings
    #tx_core_name = 'ten_Gbe_v2' #simulink name
    tx_core_name = 'gbe0' #simulink name
    mac_base = (2<<40) + (2<<32)
    
    
    
    success = 0
    while success == 0:
        try:
    
            print 'FPGA Register: ', fpga.listdev()
            sleep(.5)
            print "Configuring 10GbE Packet Transmitter..."
            fpga.write_int('tx_dest_ip',DEST_IP)
            fpga.write_int('tx_dest_port',DEST_PORT)
            sleep(0.1)
        
        
        
            print "Starting 10GbE core"
            gbe0_link=bool(fpga.read_int('gbe0_linkup'))
            if gbe0_link != True:
                print "ERROR: to cable connected to CX-4 Port 0!"
            else:
                print "Cable verified connected to port 0."
        
            print "core_name %s" % tx_core_name
            print "mac_base: %i" %mac_base
            print "fabric_ip: %i"%FABRIC_IP
            print "mac_base+fabric_ip: %i" % ((int) (mac_base) + (int) (FABRIC_IP))
            print "fabric_port: %i" % FABRIC_PORT
            sys.stdout.flush()
            #fpga.tap_start(self,tap_dev,device,mac,ip,port)
            fpga.tap_start('gbe0',tx_core_name,mac_base+FABRIC_IP,FABRIC_IP,FABRIC_PORT)
        
            print "Enabling packetizer to...",
            fpga.write_int('en_packetizer',1)
            sleep(.1)
            print fpga.read_uint('en_packetizer')

            print "Setting sync_sel to ",
            fpga.write_int('sync_sel',1)
            sleep(.1)
            print fpga.read_uint('sync_sel')
            
            print "Setting sync_mux to ",
            fpga.write_int('sync_mux',1)
            sleep(.1)
            print fpga.read_uint('sync_mux')


            print "Setting packet size to ",
            fpga.write_int('packet_size',8192)
            sleep(.1)
            print fpga.read_int('packet_size')," bytes"

            print "Resetting 10GbE"
            fpga.write_int('10gbe_rst',1)
            sleep(0.1)
            fpga.write_int('10gbe_rst',0)
            sleep(.1) 


            success = 1
        except:
            pass
######################################################

def start_gbe(fpga=''):
    if fpga=='':

        fpga=corr.katcp_wrapper.FpgaClient('192.168.4.21')
        sleep(2)
    
    success = 0
    while success == 0:
        try:
    
            print "Resetting 10GbE"
            fpga.write_int('10gbe_rst',1)
            sleep(0.1)
            fpga.write_int('10gbe_rst',0)
            sleep(.1) 
            print "Enabling packetizer"
            fpga.write_int('en_packetizer',1)
            sleep(.1)
            fpga.write_int('sync_en',1)
            success == 1
        except:
            pass

######################################################

def print_sitrep(fpga):
    #fpga=corr.katcp_wrapper.FpgaClient('192.168.4.21')
    #sleep(2)
    success = 0
    while success==0:

        try:
    
            listdev = fpga.listdev()
            for reg in listdev:
                print reg,": ",fpga.read_uint(reg)
            success=1
        
        
        except RuntimeError:
            print "There has been a runtime error."
            pass
        except:
            print "Client not connected."
            pass

######################################################

def gbe_sitrep():

    fpga=corr.katcp_wrapper.FpgaClient('192.168.4.21')
    sleep(.2)
    #config for 10gbe snap block diagnostics
    brams = ['bram_msb','bram_lsb','bram_oob'] # snap 10gbe block diagnostics
    tx_snap = 'snap_10gbe_tx'
    fpga.write_int(tx_snap+'_ctrl',1)
    fpga.write_int(tx_snap+'_ctrl',0)

    tx_size=fpga.read_int(tx_snap+'_addr')+1
    ip_prefix = '10. 0. .0.'
    ip_mask = (2**(24+5)) -(2**5)
    
    tx_bram_dmp=dict()
    for bram in brams:
        bram_name = tx_snap+'_'+bram
        print "Reading %i values from bram %s..." %(tx_size,bram_name)
        tx_bram_dmp[bram]=fpga.read(bram_name,tx_size*4)
        sys.stdout.flush()
        print 'ok'
        sleep(1)

    #unpack data
    print 'Unpacking TX packet stream'
    tx_data=[]
    for i in range(0,tx_size):
        data_64bit = struct.unpack('>Q',tx_bram_dmp['bram_msb'][(4*i):(4*i)+4]+tx_bram_dmp['bram_lsb'][(4*i):(4*i)+4])[0]
        oob_32bit = struct.unpack('>L',tx_bram_dmp['bram_oob'][(4*i):(4*i)+4])[0]
        print '[%4i]: data: %16X'%(i,data_64bit),
        ip_mask = (2**(8+5)) -(2**5)
        print 'IP: %s%3d'%(ip_prefix,(oob_32bit&(ip_mask))>>5),
        if oob_32bit&(2**0): print '[TX overflow]',
        if oob_32bit&(2**1): print '[TX almost full]',
        if oob_32bit&(2**2): print '[TX LED]',
        if oob_32bit&(2**3): print '[Link up]',
        if oob_32bit&(2**4): print '[eof]',
        tx_data.append(data_64bit)
        print ''

######################################################

def monitor(MAX_PKTS,file_name):
    #setup capture interface
    print "Setting up capture interface..."
    cap = pcapy_setup()
    out_file = open(file_name,'wb')
    data_array = []
    print "Starting packets capture!"

    for i in range(MAX_PKTS):
        data_array.append(get_packet(cap))

    print "Capture finished!"

    #write data to disk
    for pkt in data_array:
        out_file.write(pkt)
    out_file.close()
######################################################

def check_ack(MAX_PKTS):
    dat_array=[]
    cap = pcapy_setup()
    for i in range(MAX_PKTS):
        dat_array.append(get_packet(cap))
        
    print_acks(MAX_PKTS,dat_array)
######################################################

def print_acks(MAX_PKTS,raw_dat_array):
    new_array = raw_dat_array
    for i in range(MAX_PKTS):
        new_array[i] = ud1.lofasm_packet(new_array[i])
        print "%2i: " % (i+1),
        print new_array[i].ack_num
######################################################
