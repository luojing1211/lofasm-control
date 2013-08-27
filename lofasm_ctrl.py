#!/opt/python2.7/bin/python2.7

import corr
import time
import numpy as np
import struct
import sys
import logging
import matplotlib.pyplot as plt
import lofasm_ctrl_lib as llib
from multiprocessing import Process

class GeneralError:
    def __init__(self,msg):
        self.msg = msg
        print self.msg
def run_spect(REQUEST_REC):
    if REQUEST_REC:
        print "Spect: recording requested!"
        even_hndls, odd_hndls = llib.spect_config(fpga, spectAccLen, spectGain,
                rec=1)
        #llib.run_spect(fpga, spectGain, evenHandles=even_hndls,
        #        oddHandles=odd_hndls)
        llib.just_record(fpga, even_hndls, odd_hndls)
    else:
        llib.spect_config(fpga, spectAccLen, spectGain)
        llib.run_spect(fpga, spectGain) #this goes on forever

def run_bbr(REQUEST_REC,NUM_PKTS_CAPTURE,fpga=corr.katcp_wrapper.FpgaClient('192.168.4.21')):
    if REQUEST_REC:
        sock = llib.bbr_config(fpga)
        llib.bbr_run(NUM_PKTS_CAPTURE, sock, rec=1)
    else:
        sock = llib.bbr_config(fpga)
        llib.bbr_run(NUM_PKTS_CAPTURE, sock, rec=0)

####################################################
if __name__=='__main__':                          #if run as standalone program...
    from optparse import OptionParser

    #option parser
    p = OptionParser()
    p.set_usage('lofasm_mon.py [args]')
    p.set_description(__doc__)
    p.add_option('-a','--acc_len',type='int',dest='spectAccLen',default=2**17,
            help='Set the number of vectors to accumulate between dumps. Default is 2**17.')
    p.add_option('-g','--gain',type='int',dest='spectGain',default=0xffffffff,
            help='Set digital gain for Spectrometer. Default is 0xffffffff.')
    p.add_option('-p','--prog',action='store_true',dest='prog', 
            help='Program the FPGA.')
    p.add_option('-b','--boffile',action='store',dest='boffile',
            #default='lofasm_2013_Mar_21_1924.bof',help='Boffile to program the FPGA')
            default='',help='Boffile to program the FPGA')
    p.add_option('-l','--listbof',action='store_true',dest='listbof',
            help='List all the available bof files.')
    p.add_option('-i','--roach_ip',action='store',dest='roach_ip',help='ROACH IP address')
    p.add_option('-j','--spect',action='store_true',dest='spect_mode',
            help='Run in Spectrometer Mode.')
    p.add_option('-k','--bbrec',action='store_true',dest='bbr_mode',
            help='Run in Baseband Recorder Mode.')
    p.add_option('-d','--dual',action='store_true',dest='dual_mode',
            help='Run in dual mode.')
    p.add_option('-r','--rec',action='store_true',dest='rec',help='If this flag is set then data will be written to disk.')
    p.add_option('-t','--pkts',action='store',type='int',dest='num_pkts',help='This will dictate how many packets the BBR captures during each snapshot for plotting.')
    p.add_option('-P','--playback',action='store_true',dest='playback',
            help = 'Read and plot LoFASM Data File')
    p.add_option('-f','--filename', action='store', dest='filename',
            help='path to input file')
    p.add_option('-I','--interleave', action='store_true', dest='interleave',
            help='set to interleave even and odd frequency bins')
    p.add_option('-s','--startPlayback',action='store',dest='plot_start',default=1,type='int')
    p.add_option('-S','--saveplot',action='store_true',dest='save_plot',help='save plots instead of displaying',default=False)
    #parse options
    opts, args =  p.parse_args(sys.argv[1:])

    # set roach_ip var
    if (opts.roach_ip == None):
        roach_ip = '192.168.4.21'
    else:
        roach_ip = opts.roach_ip

    
    #set vars
    spectAccLen = opts.spectAccLen
    spectGain = opts.spectGain

    #connect to fpga
    print 'Connecting to server %s ...' % roach_ip
    try:
        fpga = corr.katcp_wrapper.FpgaClient(roach_ip)
        time.sleep(1)
        if fpga.is_connected():
            print 'OK'
        else:
            msg = "Not able to connect to roach board."
            raise GeneralError(msg)
    except GeneralError as err:
        print err.msg
        pass
        #exit_clean()

    if opts.listbof:
        bofs = fpga.listbof()
        for bof in bofs:
            print bof,"\n"
        exit_clean()
    #program boffile
    try:
        if opts.prog:

            if opts.boffile == '':
                latest_bof = (fpga.listbof())[-1]
                print "No bof provided..using latest on ROACH\n"
                print 'Programming %s...%s' % (latest_bof,fpga.progdev(latest_bof))
                #raise GeneralError(msg)
            else:
                print 'Programming %s...%s' % (opts.boffile,fpga.progdev(opts.boffile))
        else:
            print "Skipping boffile programming"
    except GeneralError(msg) as err:
        print err.msg
        exit_clean()

#determine which mode to run in

    if opts.spect_mode:
        run_spect(opts.rec) 
    elif opts.bbr_mode:
        run_bbr(opts.rec, opts.num_pkts)
    elif opts.dual_mode: #doesn't quite work yet
        spect_proc = Process(target=run_spect, args=(opts.rec,))
        bbr_proc = Process(target=run_bbr, args=(opts.rec, opts.num_pkts,))
        #spect_proc.start()
        bbr_proc.start()
        #config spect
        #config bbr
        #spawn threads for spect & bbr
        pass
    elif opts.playback:

        file_prefix = opts.filename[:-4]
        file_ext = opts.filename[-4:]
        if opts.interleave:
            efile = open(file_prefix+'_even'+file_ext,'rb')
            ofile = open(file_prefix+'_odd'+file_ext,'rb')
            #get HEADER
            HDR = efile.read(80)
            ofile.seek(88)
            llib.print_spect_HDR(HDR)
            first_acc = efile.read(8)
        else:
            spect_file = open(file_prefix+file_ext,'rb')
            HDR = spect_file.read(80)
            first_acc = spect_file.read(8)
            llib.print_spect_HDR(HDR)
            
        
        try:
            freqs = np.arange(2048)*200.0/2048
            plt.ion()
            fig = plt.figure()
            plot1 = fig.add_subplot(211)
            
            plt.title('LoFASM Data Playback')
            plt.xticks(range(0,200,20))
            plt.ylim([-100,0])
            plt.grid()
            plot2 = fig.add_subplot(212)
            plt.title('LoFASM Data Playback (Linear)')
            plt.xticks(range(0,200,10))
            plt.ylim([0,.7e-7])
            plt.grid()
            log_obj, = plot1.plot(freqs,np.arange(2048))
            linear_obj, = plot2.plot(freqs,np.arange(2048))
       
            #get first acc
            print "first acc: %s" %first_acc
            
            if int(opts.plot_start) < int(first_acc):
                spectrums_to_jump = 0
            else:
                spectrums_to_jump = abs(int(first_acc) - int(opts.plot_start))
            
            print "plot requested: %s" % opts.plot_start
            print "jumping: %i" % spectrums_to_jump

            if opts.interleave:
                bytes_to_jump = spectrums_to_jump*4104
                efile.seek(80+bytes_to_jump)
                ofile.seek(80+bytes_to_jump)
            else:
                bytes_to_jump = spectrums_to_jump*(2048*4)
                spect_file.seek(80+bytes_to_jump)
            
            fig.canvas.draw()
            raw_input('enter')
            

            while(1):

                if opts.interleave:
                    
                    acc_n = efile.read(8)
                    acc_n_odd = ofile.read(8)
                    even_chans = struct.unpack('>1024L',efile.read(1024*4))
                    odd_chans = struct.unpack('>1024L',ofile.read(1024*4))
                    #print "len even: %i" % len(even_chans)
                    #print "len odd: %i" % len(odd_chans)
                    spectrum = []
                    for i in range(len(even_chans)):
                        spectrum.append(even_chans[i])
                        spectrum.append(odd_chans[i])
                else:
                    acc_n = spect_file.read(8)
                    spectrum = [x for x in struct.unpack('>2048L',spect_file.read(2048*4))]

                for i in range(len(spectrum)):
                    spectrum[i] = ((freqs[i]/freqs[-1])**3.5)*(((1e-7)/0.00286990776725)*float(spectrum[i])  / (opts.spectGain)+10**-20)
                #print 'spect:',len(spectrum)i
                #print spectrum
                print acc_n
                log_obj.set_ydata(10*np.log10(spectrum))
                plot1.set_title('LoFASM Data Playback: %s' % acc_n)
                linear_obj.set_ydata(spectrum)
                plot2.set_title('LoFASM Data Playback (Linear): %s' % acc_n)

                if opts.save_plot:
                    png_title = opts.even_file_name[:17] + opts.even_file_name[21:] + acc_n_even + '.png'
                    print "Saving %s ..." % png_title
                    fig.savefig(png_title)
                else:
                    fig.canvas.draw()
                time.sleep(1)
                #skip spectra
                #efile.read(((1024*4)+8))
                #ofile.read(((1024*4)+8))

        except KeyboardInterrupt:
            print "i've been interrrupted!"
            exit()
