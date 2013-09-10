#!/opt/python2.7/bin/python2.7

import corr,time,struct,sys,logging,matplotlib
import spect_lib as SpectCtrl
import ten_gbe_lib as tg
import socket as SKT
import unpack_dat as ud
import numpy as np
import lofasm_anal as la
import matplotlib.pyplot as plt
import logging




def set_dev(fpga,dev,val):
    curr_val = fpga.read_int(dev)
    if curr_val is not val:
        fpga.write_int(dev,val)

#raw implementation of spect header
def get_spect_hdr():
    TELESCOPE = raw_input('Telescope name: ')
    MODE = 'spect'#raw_input('Mode: ')
    OBSERVER = raw_input('Observer: ')
    NCHAN = '2048'#raw_input('Number of channels: ')
    BW = '200'#raw_input('bandwidth (MHz): ')
    CENTER_FREQ = '100'#raw_input('center frequency (MHz): ')
    DATE = raw_input('Date: YYYYMMDD')
    COMMENT = raw_input('Comments?')
    return TELESCOPE, MODE, OBSERVER, NCHAN, BW, CENTER_FREQ, DATE, COMMENT

def fmt_hdr_entry(entry_val):
    #format header entries to 8byte strings
    entry_val = str(entry_val)
    if len(entry_val) < 8:
        padding = 8 - len(entry_val)
        entry_val = entry_val + padding*' '
    else:
        entry_val = entry_val[:8]
    return entry_val


def bbr_config(fpga):
    tg.config(fpga)
    print 'Setting up socket interface'
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
        #j=1 #progress bar
        for i in range(N):
            #conversion to LoFASM Packet takes place here
            pkt_array[i] = ud.lofasm_packet(pkt=pkt_array[i])  #[ud.lofasm_packet(x) for x in pkt_array]
        #ENDFOR
#        print 'hi'        
        #by now pkt_array now contains LoFASM Packets
        #instead of raw data packets
        padded_pkt_array = ud.gen_padded_array(pkt_array)
 #       print 'lo'
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
    fft_len = 8192#2048
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
    plt.ylim(80,130)
    plt.grid()
    ax_que_spect = fig.add_subplot(322)
    plt.title('Q: Power Spectrum (linear scale)')
    ax_que_spect_log = fig.add_subplot(324)
    plt.title('Q: Power Spectrum (log scale)')
    plt.ylim(80,130)
    plt.grid()
   
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





def spect_config(fpga,acc_len=262144,gain=int(268416),rec=0):
    #katcp_port = 7147
    
    #roach = '192.168.4.21' #ROACH board IP Address
    #fpga=corr.katcp_wrapper.FpgaClient(roach)
    #time.sleep(1)

    if fpga.is_connected():
        print 'Connected to ROACH\n'
    else:
        print 'ERROR: not able to connect to ROACH Board (%s:%i).\n' %(roach,katcp_port)
        return
    print '-------------------------------'
    time.sleep(2)
    print ('Configuring accumulation length to %i...' % acc_len),
    #fpga.write_int('acc_len',acc_len)
    set_dev(fpga,'acc_len',acc_len)
    print ' SUCCESSFUL\n'
    
    print '-------------------------------'
    print 'Resetting Counters...',
    fpga.write_int('cnt_rst',1) #toggle counter reset
    fpga.write_int('cnt_rst',0) 
    print 'SUCCESSFUL\n'

    print '-------------------------------'
    print 'Setting I input gain to %i...' % gain
    set_dev(fpga,'spect_gain_i',gain)
    print 'SUCCESSFUL\n'
  
    print '-------------------------------'
    print 'Setting Q input gain to %i...' % gain
    set_dev(fpga,'spect_gain_q',gain)
    print 'SUCCESSFUL\n'
    
    print '-------------------------------'
    print 'Setting Re(Vi*Vq) gain to %i...' % gain
    set_dev(fpga,'xpow_gain_real',gain)
    print 'SUCCESSFUL\n'
    
    print '-------------------------------'
    print 'Setting Im(Vi*Vq) input gain to %i...' % gain
    set_dev(fpga,'xpow_gain_imag',gain)
    print 'SUCCESSFUL\n'
    
    print '-------------------------------'
    print 'Setting sync_sel to 1...',
    fpga.write_int('sync_sel',1)
    print 'SUCCESSFUL\n'

    print '-------------------------------'
    print 'Setting sync_mux to 1...',
    fpga.write_int('sync_mux',1)
    print 'SUCCESSFUL\n'

    print '-------------------------------' 
    print 'Setting sync_mux to 0...',
    fpga.write_int('sync_mux',0)
    print 'SUCCESSFUL\n'


    print '-------------------------------'
    print 'Setting volt_gain_i to 1...',
    fpga.write_int('volt_gain_i',1)
    print 'SUCCESSFUL\n'
    
    print '-------------------------------'
    print 'Setting volt_gain_q to 1...',
    fpga.write_int('volt_gain_q',1)
    print 'SUCCESSFUL\n'
    
    
    if rec:
        #open files to write in and return the handle
        TELESCOPE, MODE, OBSERVER, NCHAN, BW, CENTER_FREQ, DATE, COMMENT = get_spect_hdr()
        TELESCOPE = fmt_hdr_entry(TELESCOPE)
        MODE = fmt_hdr_entry(MODE)
        OBSERVER = fmt_hdr_entry(OBSERVER)
        NCHAN = fmt_hdr_entry(NCHAN)
        BW = fmt_hdr_entry(BW)
        CENTER_FREQ = fmt_hdr_entry(CENTER_FREQ)
        DATE = fmt_hdr_entry(DATE)
        COMMENT = fmt_hdr_entry(COMMENT)
        HEADER = TELESCOPE+MODE+OBSERVER+NCHAN+BW+CENTER_FREQ+DATE+COMMENT
        
        prefix = time.strftime("%Y_%b_%d_%H%M_")
        fileStamp_I = [time.strftime(prefix+"I_even.dat"),time.strftime(prefix+"I_odd.dat")]
        fileStamp_Q = [time.strftime(prefix+"Q_even.dat"),time.strftime(prefix+"Q_odd.dat")]
        
        fileStamp_sum = [time.strftime(prefix+"sum_even.dat"),time.strftime(prefix+"sum_odd.dat")]
        fileStamp_diff = [time.strftime(prefix+"diff_even.dat"),time.strftime(prefix+"diff_odd.dat")]
        
        even_hndls = [open('data_20130819/'+fileStamp_I[0],'wb'),
                open('data_20130819/'+fileStamp_Q[0],'wb'),
                open('data_20130819/'+fileStamp_sum[0],'wb'),
                open('data_20130819/'+fileStamp_diff[0],'wb')]

        odd_hndls = [open('data_20130819/'+fileStamp_I[1],'wb'), 
                open('data_20130819/'+fileStamp_Q[1],'wb'),
                open('data_20130819/'+fileStamp_sum[1],'wb'),
                open('data_20130819/'+fileStamp_diff[1],'wb')]

        #write header
        even_hndls[0].write(HEADER+'even    '+'I       ')
        even_hndls[1].write(HEADER+'even    '+'Q       ')
        even_hndls[2].write(HEADER+'even    '+'SUM     ')
        even_hndls[3].write(HEADER+'even    '+'DIFF    ')
        odd_hndls[0].write(HEADER+'odd     '+'I       ')
        odd_hndls[1].write(HEADER+'odd     '+'Q       ')
        odd_hndls[2].write(HEADER+'odd     '+'SUM     ')
        odd_hndls[3].write(HEADER+'odd     '+'DIFF    ')
        
        return even_hndls,odd_hndls
    else:
        pass

def just_record(fpga, evenHandles=[], oddHandles=[]):

    try:
        while(1):

            acc_n = fmt_hdr_entry(int(fpga.read_uint('acc_cnt')))
            eye_even = fpga.read('even_i',1024*4,0)
            eye_odd = fpga.read('odd_i',1024*4,0)
            que_even = fpga.read('even_q',1024*4,0)
            que_odd = fpga.read('odd_q',1024*4,0)
            #print struct.unpack('>1024L',eye_even)
            
            #Vi*Vq
            real_even = fpga.read('even_sum',1024*4,0)
            real_odd = fpga.read('odd_sum',1024*4,0)
            imag_even = fpga.read('even_diff',1024*4,0)
            imag_odd = fpga.read('odd_diff',1024*4,0)

            print "Writing to I: acc: %s" % acc_n
            evenHandles[0].write(acc_n+eye_even)
            oddHandles[0].write(acc_n+eye_odd)
            print "Wriitng to Q: acc: %s" % acc_n
            evenHandles[1].write(acc_n+que_even)
            oddHandles[1].write(acc_n+que_odd)
            
            print "Writing to Re(Vi*Vq): acc: %s" % acc_n
            evenHandles[2].write(acc_n+real_even)
            oddHandles[2].write(acc_n+real_odd)
            print "Wriitng to Im(Vi*Vq): acc: %s" % acc_n
            evenHandles[3].write(acc_n+imag_even)
            oddHandles[3].write(acc_n+imag_odd)
            
            #exit()
    except KeyboardInterrupt:
        print 'LoFASM Controller has detected a KeyboardInterrupt!\nExiting now!'
        if evenHandles != []:
            for hand in evenHandles: hand.close()
            for hand in oddHandles: hand.close()
        exit()


def get_spect_data(fpga):
    acc_n = fpga.read_uint('acc_cnt')
    eye_even = fpga.read('even_i',1024*4,0)
    eye_odd = fpga.read('odd_i',1024*4,0)
    que_even = fpga.read('even_q',1024*4,0)
    que_odd = fpga.read('odd_q',1024*4,0)
    
    sum_even = fpga.read('even_real',1024*4,0)
    sum_odd = fpga.read('odd_real',1024*4,0)
    dif_even = fpga.read('even_imag',1024*4,0)
    dif_odd = fpga.read('odd_imag',1024*4,0)
    #sum_even = fpga.read('even_real',1024*4,0)
    #sum_odd = fpga.read('odd_real',1024*4,0)
    #dif_even = fpga.read('even_imag',1024*4,0)
    #dif_odd = fpga.read('odd_imag',1024*4,0)

    eye_0 = struct.unpack('>1024L',eye_even)
    eye_1 = struct.unpack('>1024L',eye_odd)
    que_0 = struct.unpack('>1024L',que_even)
    que_1 = struct.unpack('>1024L',que_odd)

    sum_0 = struct.unpack('>1024l',sum_even)
    sum_1 = struct.unpack('>1024l',sum_odd)
    dif_0 = struct.unpack('>1024l',dif_even)
    dif_1 = struct.unpack('>1024l',dif_odd)
    
    
    interleave_i = []
    interleave_q = []
    interleave_s = [] #sum
    interleave_d = [] #dif

#interleave spectra
    for i in range(1024):
        interleave_i.append(eye_0[i])
        interleave_i.append(eye_1[i])
        interleave_q.append(que_0[i])
        interleave_q.append(que_1[i])

        interleave_s.append(sum_0[i])
        interleave_s.append(sum_1[i])
        interleave_d.append(dif_0[i])
        interleave_d.append(dif_1[i])

    return acc_n, interleave_i, interleave_q, interleave_s, interleave_d


def run_spect(fpga,gain):
    #get data for ADC I
    #acc_n, interleave_i = get_spect_data(fpga, 'i', evenHandles, oddHandles) 
    #get data for ADC Q
    #_, interleave_q = get_spect_data(fpga, 'q', evenHandles, oddHandles)
    
    acc_n, interleave_i, interleave_q, interleave_sum, interleave_dif = get_spect_data(fpga)

    for i in range(len(interleave_i)):
        interleave_i[i] = (((1e-7)/0.00286990776725)*float(interleave_i[i])  / (gain)+10**-20)
        interleave_q[i] = (((1e-7)/0.00286990776725)*float(interleave_q[i])  / (gain)+10**-20)
        interleave_sum[i] = (((1e-7)/0.00286990776725)*float(interleave_sum[i])  / (gain)+10**-20)
        interleave_dif[i] = (((1e-7)/0.00286990776725)*float(interleave_dif[i])  / (gain)+10**-20)

    freqs = np.arange(2048)*200.0/2048

    plt.ion()
    fig = plt.figure()
    
    #I input Log scale plot
    Iplot_log = fig.add_subplot(2,4,1)
    plt.title('LoFASM Spectrometer (ADC I): INITIALIZING')
    plt.ylabel('Power (dBm)ish')
    #plt.xticks(range(0,200))
    plt.xticks(range(0,200,20))
    plt.ylim(-100,0)
    #plt.ylim(-25,0)
    #plt.ylim(-50,-10)
    #plt.xlim(0,25)
    plt.grid()
    #plt.xlabel('Frequency (MHz)')

    #I input linear scale plot
    Iplot_lin = fig.add_subplot(2,4,5)
    plt.title('ADC I: Linear')
    plt.xticks(range(0,200,20))
    plt.grid()
    plt.ylim([0,.2])

    
    #Q input log scale plot
    Qplot_log = fig.add_subplot(2,4,2)
    plt.ylabel('Power (dBm)')
    #plt.xticks(range(0,200))
    plt.xticks(range(0,200,20))
    plt.ylim(-100,0)
    #plt.ylim(-25,0)
    #plt.xlim(2030,2047)
    #plt.xlim(0,25)
    #plt.ylim(-50,-10)
    plt.grid()
    #plt.xlabel('Frequency (MHz)')
    plt.title('LoFASM spectrometer (ADC Q): INITIALIZING')

    #Q input linear scale plot
    Qplot_lin = fig.add_subplot(2,4,6)
    plt.title('ADC Q: Linear')
    #plt.xticks(range(0,200,20))
    plt.ylim([0,.2])
    plt.grid()

    
    #Re(Vi*Vq)  log scale plot
    sum_plot_log = fig.add_subplot(2,4,3)
    plt.ylabel('Power (dBm)')
    plt.xticks(range(0,200,20))
    #plt.xticks(range(0,200,10))
    #plt.ylim(-25,0)
    #plt.xlim(0,25)
    plt.ylim(-100,0)
    plt.grid()
    #plt.xlabel('Frequency (MHz)')
    plt.title('LoFASM spectrometer (sum): INIT')

    #Re(Vi*Vq) linear scale plot
    sum_plot_lin = fig.add_subplot(2,4,7)
    plt.title('sum: Linear')
    #plt.xticks(range(0,200))
    plt.ylim([0,.2])
    plt.grid()
    
    #dif  log scale plot
    dif_plot_log = fig.add_subplot(2,4,4)
    plt.ylabel('Power (dBm)')
    #plt.xticks(range(0,200))
    plt.xticks(range(0,200,20))
    plt.ylim(-100,0)
    #plt.xlim(0,25)
    #plt.ylim(-25,0)
    plt.grid()
    #plt.xlabel('Frequency (MHz)')
    plt.title('LoFASM spectrometer (diff): INIT')

    #dif input linear scale plot
    dif_plot_lin = fig.add_subplot(2,4,8)
    plt.title('diff: Linear')
    plt.xticks(range(0,200,20))
    plt.ylim([0,.2])
    plt.grid()

    line_I_lin, = Iplot_lin.plot(freqs,interleave_i,'k-')
    line_Q_lin, = Qplot_lin.plot(freqs,interleave_q,'k-')
    line_I_log, = Iplot_log.plot(freqs,10*np.log10(interleave_i),'k-')
    line_Q_log, = Qplot_log.plot(freqs,10*np.log10(interleave_q),'k-')
    
    line_sum_lin, = sum_plot_lin.plot(freqs,interleave_sum,'k-')
    line_dif_lin, = dif_plot_lin.plot(freqs,interleave_dif,'k-') 
    line_sum_log, = sum_plot_log.plot(freqs,10*np.log10(np.array(interleave_sum)-min(interleave_sum)+10**-20),'k.-')
    line_dif_log, = dif_plot_log.plot(freqs,10*np.log10(np.array(interleave_dif)-min(interleave_dif)+10**-20),'k.-')

    raw_input('press enter to continue.')
    fig.canvas.draw()
    time.sleep(2)
    try:
        while(1):
            #acc_n,interleave_i = get_spect_data(fpga, 'i', evenHandles,oddHandles)
            #_, interleave_q = get_spect_data(fpga, 'q', evenHandles, oddHandles)
            acc_n, interleave_i, interleave_q, interleave_sum, interleave_dif = get_spect_data(fpga)
            for i in range(len(interleave_i)):
                #interleave_i[i] = ((freqs[i]/freqs[-1])**3.5)*(((1e-7)/0.00286990776725)*float(interleave_i[i])  / (gain)+10**-20)
                #interleave_q[i] = ((freqs[i]/freqs[-1])**3.5)*(((1e-7)/0.00286990776725)*float(interleave_q[i])  / (gain)+10**-20)
                #interleave_sum[i] = ((freqs[i]/freqs[-1])**3.5)*(((1e-7)/0.00286990776725)*float(interleave_sum[i])  / (gain)+10**-20)
                #interleave_dif[i] = ((freqs[i]/freqs[-1])**3.5)*(((1e-7)/0.00286990776725)*float(interleave_dif[i])  / (gain)+10**-20)
                interleave_i[i] = (((1e-7)/0.00286990776725)*float(interleave_i[i])  / (gain)+10**-20)
                interleave_q[i] = (((1e-7)/0.00286990776725)*float(interleave_q[i])  / (gain)+10**-20)
                interleave_sum[i] = (((1e-7)/0.00286990776725)*float(interleave_sum[i])  / (gain)+10**-20)
                interleave_dif[i] = (((1e-7)/0.00286990776725)*float(interleave_dif[i])  / (gain)+10**-20)
 
            line_I_log.set_ydata(10*np.log10(interleave_i))
            line_Q_log.set_ydata(10*np.log10(interleave_q))
            line_I_lin.set_ydata(interleave_i)
            line_Q_lin.set_ydata(interleave_q)
            line_sum_log.set_ydata(10*np.log10( list(np.array(interleave_sum)+10**-20) ))
            line_dif_log.set_ydata(10*np.log10( list(np.array(interleave_dif)+10**-20) ))
            print interleave_i[256], interleave_q[256], interleave_sum[248]
            print np.log10(interleave_i[256]), np.log10(interleave_q[256]), np.log10(interleave_sum[248])
            
            line_sum_lin.set_ydata(interleave_sum)
            line_dif_lin.set_ydata(interleave_dif)
            
            
            
            Iplot_lin.set_title('LoFASM I Spectrometer (linear): %i' % acc_n)
            Qplot_lin.set_title('LoFASM Q Spectrometer (linear): %i' % acc_n)
            Iplot_log.set_title('LoFASM I Spectrometer (log): %i' % acc_n)
            Qplot_log.set_title('LoFASM Q Spectrometer (log): %i' % acc_n)
            sum_plot_lin.set_title('LoFASM S Spectrometer (linear): %i' % acc_n)
            dif_plot_lin.set_title('LoFASM D Spectrometer (linear): %i' % acc_n)
            sum_plot_log.set_title('LoFASM S Spectrometer (log): %i' % acc_n)
            dif_plot_log.set_title('LoFASM D Spectrometer (log): %i' % acc_n)
            fig.canvas.draw()
 
 
    except KeyboardInterrupt:
        try:
            raw_input("Press Enter to unpause plot")
        except Keyboardinterrupt:
            print 'LoFASM Controller has detected a KeyboardInterrupt!\nExiting now!'
            exit()

def print_spect_HDR(HDR):
    header_fields = ["Telescope: ","Mode: ", "Observer: ", "NChan: ", "BW: ", "Center Freq.: ",
            "DATE: ", "Comments: "]
    for i in range(len(header_fields)):
        print header_fields[i],HDR[i*8:(i+1)*8]
def upgain2(fpga):
    current_setting = fpga.read_uint('gain')
    new_setting = current_setting * 2
    print "old setting: %i\nnew setting: %i" % (current_setting, new_setting)
    fpga.write_int('gain',new_setting)

def downgain2(fpga):
    current_setting = fpga.read_uint('gain')
    new_setting = int(current_setting / 2.0)
    print "old setting: %i\nnew setting: %i" % (current_setting, new_setting)
    fpga.write_int('gain',new_setting)

def upgain10(fpga):
    current_setting = fpga.read_uint('gain')
    new_setting = current_setting * 10
    print "old setting: %i\nnew setting: %i" % (current_setting, new_setting)
    fpga.write_int('gain',new_setting)

def downgain10(fpga):
    current_setting = fpga.read_uint('gain')
    new_setting = int(current_setting / 10.0)
    print "old setting: %i\nnew setting: %i" % (current_setting, new_setting)
    fpga.write_int('gain',new_setting)

def dump_regs(fpga):
    devs = fpga.listdev()
    for dev in devs:
        print dev,": ",fpga.read_uint(dev)

class GeneralError:
    def __init__(self,msg):
        self.msg = msg

