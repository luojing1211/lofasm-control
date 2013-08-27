#module with usefull fnctions for ROACH networking and development
# Author: Louis P. Dartez
import corr,sys,pcapy,datetime,struct,dpkt
from time import strftime,sleep,time
import unpack_dat as ud

######################
def ipStr2Bin(ip):
    ip = ip.split('.')
    ip.reverse()
    dest_ip = 0
    for i in range(len(ip)):
        dest_ip += 2**(i*8) * int(ip[i])
    return dest_ip

######################
def get_packet(sock,NUM_PKTS):
    pkt_array = []                  #set to empty list
    NUM_BYTES = 9000                #MTU
    print "Starting capture of " + str(NUM_PKTS) + " Packet(s).\n"
    start = time()
    for i in range(NUM_PKTS):
        pkt_array.append(sock.recv(NUM_BYTES))  #acquire packets from network
    finish = time()
    capture_time = finish - start
    print "DONE!...Packet capture took " + str(capture_time) + " seconds."
    return pkt_array,capture_time

######################
def config(fpga=''):
    HOST = '192.168.4.21'

    #config for 10GbE interface
    FABRIC_IP = '192.168.4.10'
    FABRIC_IP = ipStr2Bin(FABRIC_IP)
    FABRIC_PORT = 60000
    DEST_PORT = 60001
    DEST_IP = '192.168.4.11'
    DEST_IP = ipStr2Bin(DEST_IP)
    tx_core_name = 'gbe0'       #simulink name
    mac_base = (2<<40) + (2<<32)


    
    end_while_loop = 0
    while end_while_loop == 0:
        try:
            print 'FPGA Registers: ', fpga.listdev()
            sleep(.5)
            print "Configuring 10GbE Packet Transmitter..."
            fpga.write_int('tx_dest_ip',DEST_IP)
            fpga.write_int('tx_dest_port',DEST_PORT)
            sleep(0.1)


            print "Starting 10GbE core..."
            gbe0_link = bool(fpga.read_int('gbe0_linkup'))

            if gbe0_link != True:
                print "ERROR: No cable is connected to CS-4 Port 0!"
            else:
                print "Cable verified connected to port 0."

            print "core_name %s" % tx_core_name
            print "mac_base: %i" % mac_base
            print "fabric_ip: %i" % FABRIC_IP
            print "mac_base+fabric_ip: %i" % ((int) (mac_base) + (int) (FABRIC_IP))
            print "fabric_port: %i" % FABRIC_PORT
            sys.stdout.flush()

            fpga.tap_start('gbe0',tx_core_name,mac_base+FABRIC_IP,FABRIC_IP,FABRIC_PORT)

            print "Enabling packetizer to...",
            fpga.write_int('en_packetizer',1)
            sleep(.1)
            print fpga.read_uint('en_packetizer')


            try:
                print "Setting sync_mux to "
                fpga.write_int('sync_mux',1)
                sleep(0.1)
                print fpga.read_uint('sync_mux')
            except RuntimeError:
                print 'writing to sync_mux failed'
                pass


            print "Setting packet size to ",
            fpga.write_int('packet_size',8192)
            sleep(.1)
            print fpga.read_uint('packet_size'), " bytes"

            print "Resetting 10GbE"
            fpga.write_int('10gbe_rst',1)
            sleep(0.1)
            fpga.write_int('10gbe_rst',0)
            sleep(.1)
            
            print "Enabling BBR"
            fpga.write_int('en_bbr',1)
            sleep(.1)
            end_while_loop = 1
        except:
            if not bool(int(raw_input('there was an error...try again?'))):
                end_while_loop = 1

######################
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
            success = 1
        except:
            pass

######################

def gbe_sitrep():
    fpga = corr.katcp_wrapper.FpgaClient('192.168.4.21')
    sleep(.2)

    #config for 10gbe diagnostic snap blocks
    brams = ['bram_msb','bram_lsb','bram_oob']
    tx_snap = 'snap_10gbe_tx'
    fpga.write_int(tx_snap+'_ctrl',1)
    fpga.write_int(tx_snap+'_ctrl',0)

    tx_size = fpga.read_int(tx_snap+'_addr')+1
    ip_prefix = '10. 0. .0.'
    ip_mask = (2**(25+5)) - (2**5)

    tx_bram_dmp = dict()
    for bram in brams:
        bram_name = tx_snap + '_' + bram
        print "Reading %i values from bram %s..." % (tx_size, bram_name)
        tx_bram_dmp[bram] = fpga.read(bram_name,tx_size*4)
        sys.stdout.flush()
        print 'ok'
        sleep(1)

    #unpack data
    print 'Unpacking TX packet stream'
    tx_data = []
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

##############################
def print_acks(NUM_PKTS,raw_dat_array):
    new_array = raw_dat_array
    for i in range(NUM_PKTS):
        new_array[i] = ud.lofasm_packet(new_array[i])
        print "%2i: " % (i+1),
        print new_array[i].ack_num
