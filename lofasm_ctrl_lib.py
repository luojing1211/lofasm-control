#!/opt/python2.7/bin/python2.7

import corr,time,struct,sys,logging,matplotlib
import spect_lib as SpectCtrl
import ten_gbe_lib as tg
import socket as SKT
import unpack_dat as ud
import numpy as np
import lofasm_anal as la
import matplotlib.pyplot as plt

def bbr_config(fpga):
    tg.config(fpga)
    print 'Setting up socket inteface'
    sock = SKT.socket(SKT.AF_INET,SKT.SOCK_DGRAM)
    sock.bind(('192.168.4.11',60001))
    return sock
    
def bbr_snap(sock,MAX_PKTS,rec=0):
    #acquire network packets
    pkt_array, capture_time = tg.get_packet(sock,MAX_PKTS)

   # if not rec:
    if 1:
        print 'Converting raw data into LoFASM Packets...\n',
        N=len(pkt_array)
        j=1 #progress bar
        for i in range(N):
            if j==10:
                percent_complete = ((i+1.0)/N)*100.0
                print "\r %2.2f" % percent_complete,
                print "% complete"
                j=1
            else:
                j+=1

            sys.stdout.flush()
            
            #conversion to LoFASM Packet takes place here
            pkt_array[i] = ud.lofasm_packet(pkt=pkt_array[i])
        #endfor
        
        #by now pkt_array now contains LoFASM Packets
        #instead of raw data packets
        padded_pkt_array = ud.gen_padded_array(pkt_array)

        total_packets = len(padded_pkt_array)
        num_padded = float(la.getNumPad(padded_pkt_array))
        num_data = total_packets - num_padded
        percent_dropped = (num_padded/total_packets)*100
        print "Total Packets:   %i          Dropped Packets: %i" % (total_packets,num_padded)
        print "Percent Dropped: %f" % percent_dropped
    
        #extract I & Q data streams from LoFASM Packet
        streams = ud.gen_pkt_streams(padded_pkt_array)

    
#    elif rec:
#        prefix = time.strftime("data/bbr/BBR_%b_%d_%Y_%H%M_")
#        fileStamp = time.strftime(prefix+"RAW.dat")
#        file_hndl = open(fileStamp,'w')

#        for i in range(len(pkt_array)):
#            file_hndl.write(pkt_array[i])
        
    return streams #[idata,qdata]

def bbr_run(MAX_PKTS,sock,rec=0):
    print "Starting BaseBand Recorder"

    streams = bbr_snap(sock,MAX_PKTS,rec)
    y_eye = np.array(streams[0])
    y_que = np.array(streams[1])
    #eye_spect = la.getSpectrum(y_eye)
    #que_spect = la.getSpectrum(y_que)
    
    #perform averaging
    fft_len = 2048
    eye_spect_avg = la.getFFTavg(y_eye,fft_len)
    que_spect_avg = la.getFFTavg(y_que,fft_len)
    freqs = np.linspace(0,100,fft_len/2.0)
    #print 'exiting from bbr_run().'
    #exit()
    #begin plotting madness
    
    eye_timeseries = y_eye[:100]
    que_timeseries = y_que[:100]
    
    plt.ion()
    fig = plt.figure(1)

    ax_eye_spect = fig.add_subplot(321)
    plt.title('I: Power Spectrum (linear scale)')
    ax_eye_spect_log  = fig.add_subplot(323)
    plt.title('I: Power Spectrum (log scale)')
    ax_que_spect = fig.add_subplot(322)
    plt.title('Q: Power Spectrum (linear scale)')
    ax_que_spect_log = fig.add_subplot(324)
    plt.title('Q: Power Spectrum (log scale)')
   
    line_eye_spect_log, = ax_eye_spect_log.plot(freqs,10*np.log10(eye_spect_avg),'b-')
    line_que_spect_log, = ax_que_spect_log.plot(freqs,10*np.log10(que_spect_avg),'g-')
    line_eye_spect, = ax_eye_spect.plot(freqs,(eye_spect_avg),'b-')
    line_que_spect, = ax_que_spect.plot(freqs,(que_spect_avg),'g-')

    ax_eye_timeseries = fig.add_subplot(325)
    plt.title('I: Time Series')
    ax_que_timeseries = fig.add_subplot(326)
    plt.title('Q: Time Series')

    line_eye_timeseries, = ax_eye_timeseries.plot(eye_timeseries,'*')
    line_que_timeseries, = ax_que_timeseries.plot(que_timeseries,'*')
    raw_input('Press ENTER to continue..')
    fig.canvas.draw()
    #print "input I:",min(10*np.log10(eye_spect_avg)),":",max(10*np.log10(eye_spect_avg)) 

    if rec: #this is the end of the road if we want to write to disk...for now
        raw_input('press enter to continue.')
        exit()
    else:
        pass

    while True:
        try:
            streams = bbr_snap(sock,MAX_PKTS)
            
            y_eye = np.array(streams[0])
            y_que = np.array(streams[1])
            #print 'yI: ',str(y_eye[:10])
            #print 'yQ: ',str(y_que[:10])
            #eye_spect = la.getSpectrum(y_eye)
            #que_spect = la.getSpectrum(y_que)

            #perform averaging
            
            eye_spect_avg = la.getFFTavg(y_eye,fft_len)
            que_spect_avg = la.getFFTavg(y_que,fft_len)
            eye_timeseries = y_eye[:100]
            que_timeseries = y_que[:100]

            #update plot data
            line_eye_spect.set_ydata(eye_spect_avg)
            line_eye_spect_log.set_ydata(10*np.log10(eye_spect_avg))
            line_que_spect.set_ydata(que_spect_avg)
            line_que_spect_log.set_ydata(10*np.log10(que_spect_avg))
            line_eye_timeseries.set_ydata(eye_timeseries)
            line_que_timeseries.set_ydata(que_timeseries)

            #print "input I:",min(10*np.log10(eye_spect_avg)),":",max(10*np.log10(eye_spect_avg)) 
            fig.canvas.draw()
            time.sleep(3)
        except KeyboardInterrupt:
            print "Detected KeyboardInterrupt!\nExiting now!"
            sock.close()
            exit()





def spect_config(fpga,acc_len=262144,gain=int(0xffffffff),rec=0):
    #katcp_port = 7147
    
    #roach = '192.168.4.21' #ROACH board IP Address
    #fpga=corr.katcp_wrapper.FpgaClient(roach)
    #time.sleep(1)

    if fpga.is_connected():
        print 'SUCCESSFUL\n'
    else:
        print 'ERROR: not able to connect to ROACH Board (%s:%i).\n' %(roach,katcp_port)
        return
    print '-------------------------------'
    print ('Configuring accumulation length to %i...' % acc_len),
    fpga.write_int('acc_len',acc_len)
    print ' SUCCESSFUL\n'
    
    print '-------------------------------'
    print 'Resetting Counters...',
    fpga.write_int('cnt_rst',1) #toggle counter reset
    fpga.write_int('cnt_rst',0) 
    print 'SUCCESSFUL\n'

    print '-------------------------------'
    print 'Setting digital gain to %i...' % gain
    fpga.write_int('gain',gain)
    print 'SUCCESSFUL\n'
    
    if rec:
        #open files to write in and return the handle
        prefix = time.strftime("%b_%d_%Y_%H%M_")
        fileStamp = [time.strftime(prefix+"even.dat"),time.strftime(prefix+"odd.dat")]
        even_hndl = open(fileStamp[0],'w')
        odd_hndl = open(fileStamp[1],'w')
        return even_hndl,odd_hndl
    else:
        pass
def get_spect_data(fpga,evenHandles=[],oddHandles=[]):
    acc_n = fpga.read_uint('acc_cnt')
    even_i = fpga.read('even_i',1024*4,0)
    odd_i = fpga.read('odd_i',1024*4,0)

    print 'get_spect_data: evenHandles = ',type(evenHandles)
    if evenHandles != []:
        print 'NOT EMPTY!'
        evenHandles.write(even_i)
        oddHandles.write(odd_i)

    a_0 = struct.unpack('>1024L',even_i)
    a_1 = struct.unpack('>1024L',odd_i)

    interleave_a = []

    for i in range(1024):
        interleave_a.append(a_0[i])
        interleave_a.append(a_1[i])

    return acc_n, interleave_a


def run_spect(fpga,gain,evenHandles=[],oddHandles=[]):
    plt.ion()
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    #fig.canvas.manager.window.after(100,plot_spect(fpga,gain))
    acc_n, interleave_a = get_spect_data(fpga,evenHandles,oddHandles)

    for i in range(len(interleave_a)):
        interleave_a[i] = (((1e-7)/0.00286990776725)*float(interleave_a[i])  / (gain)+10**-20)

    freqs = np.arange(2048)*100.0/2048

    plt.title('LoFASM Spectrometer: INITIALIZING')
    
    line1, = plt.plot(freqs,10*np.log10(interleave_a),'k.-')
    plt.ylabel('Power (dBm)    RBW = 48.8 kHz')
    plt.xticks(range(0,100,10))
    plt.grid()
    plt.xlabel('Frequency (MHz)')
    fig.canvas.draw()
    time.sleep(2)
    try:
        while(1):
            acc_n,interleave_a = get_spect_data(fpga,evenHandles,oddHandles)
            for i in range(len(interleave_a)):
                interleave_a[i] = (((1e-7)/0.00286990776725)*float(interleave_a[i])  / (gain)+10**-20)
            line1.set_ydata(10*np.log10(interleave_a))
            plt.title('LoFASM Spectrometer: %i' % acc_n)
            fig.canvas.draw()
 
 
    except KeyboardInterrupt:
        print 'LoFASM Controller has detected a KeyboardInterrupt!\nExiting now!'
        if evenHandles != []:
            evenHandles.close()
            oddHandles.close()
        exit()


class GeneralError:
    def __init__(self,msg):
        self.msg = msg

