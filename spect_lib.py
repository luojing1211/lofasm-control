#!/opt/python2.7/bin/python2.7
'''
This script demonstrates programming an FPGA, configuring a wideband spectrometer and plotting the received data using the Python KATCP library along with the katcp_wrapper distributed in the corr package. Designed for use with TUT3 at the 2009 CASPER workshop.\n

You need to have KATCP and CORR installed. Get them from http://pypi.python.org/pypi/katcp and http://casper.berkeley.edu/svn/trunk/projects/packetized_correlator/corr-0.4.0/

\nAuthor: Jason Manley, November 2009.
'''

#TODO: add support for ADC histogram plotting.
#TODO: add support for determining ADC input level 

#import corr,time,numpy,struct,sys,logging,pylab,matplotlib
import corr,time,numpy,struct,sys,logging

import matplotlib
#matplotlib.use('MacOSX')
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


#bitstream = sys.argv[1]
#katcp_port=7147

#files in which data will be dumped
of_even_i = open("data/even_i.dat","wb")

of_odd_i = open("data/odd_i.dat","wb")

#of_even_q = open("lofasm_data/dat0709_even_q.dat","wb")
#of_odd_q = open("lofasm_data/dat0709_odd_q.dat","wb")

def exit_fail():
    print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
    try:
        fpga.stop()
    except: pass
    raise
    exit()

def exit_clean():
    try:
        fpga.stop()
    except: pass
    exit()

def get_data(fpga):
    #get the data...    
    acc_n = fpga.read_uint('acc_cnt')

    even_i = fpga.read('even_i',1024*4,0)
    odd_i = fpga.read('odd_i',1024*4,0)
    
    a_0=struct.unpack('>1024L',even_i)
    a_1=struct.unpack('>1024L',odd_i)

     # write files
   # of_even_i.write(even_i)
   # of_odd_i.write(odd_i)

	

    interleave_a=[]

    for i in range(1024):
        interleave_a.append(a_0[i])
        interleave_a.append(a_1[i])

    return acc_n, interleave_a 

def plot_spectrum(fig,fpga,gain):
#    matplotlib.pyplot.clf()
    plt.clf()
    acc_n, interleave_a = get_data(fpga)
   
    for i in range(len(interleave_a)):
        #interleave_a[i]=(10**-15) + (float(interleave_a[i])  )
        #interleave_a[i]=(10**-20) + (((1e-3)/0.0191959030971)*float(interleave_a[i])  / (fpga.read_int('gain')))
        #interleave_a[i]=(((1e-7)/0.00286990776725)*float(interleave_a[i])  / (opts.gain)+10**-20)
        interleave_a[i]=(((1e-7)/0.00286990776725)*float(interleave_a[i])  / (gain)+10**-20)
        
    freqs = numpy.arange(2048)*200.0/2048
    
    #plt.plot(freqs,interleave_a,'k.-')
    plt.plot(freqs,10*numpy.log10(interleave_a),'k.-')
#    plt.plot([0,100],[-68.7,-68.7],'--')
#    plt.plot([20,30,40,50,60,70,80],[-65.7,-60.7,-58.7,-60.7,-61.7,-63.7,-65.7],'g--')

    plt.title('28bit power: 14BIT Integration number %i' % acc_n)
    plt.ylabel('Power (dBm)    RBW = 48.8 kHz')
#    plt.ylim(-100,0.00)
#    plt.yticks(range(-100,5,5))
    plt.xticks(range(0,200,10))
    plt.grid()
    plt.xlabel('Frequency (MHz)')
    fig.canvas.draw()
    print 'hello'
    fig.canvas.manager.window.after(100, plot_spectrum(fig,fpga,gain))
    

#START OF MAIN:

if __name__ == '__main__':
    from optparse import OptionParser


    p = OptionParser()
    p.set_usage('spectrometer.py <ROACH_HOSTNAME_or_IP> [options]')
    interleave_a[i]=(((1e-7)/0.00286990776725)*float(interleave_a[i])  / (opts.gain)+10**-20)
    p.set_description(__doc__)
    p.add_option('-l', '--acc_len', dest='acc_len', type='int',default=(2**25)/2048,
        help='Set the number of vectors to accumulate between dumps. default is 2*(2^28)/2048, or just under 2 seconds.')
    p.add_option('-g', '--gain', dest='gain', type='int',default=int(float(0xffffffff) /((2**0)*1.0)),
        help='Set the digital gain (6bit quantisation scalar). Default is 0xffffffff (max), good for wideband noise. Set lower for CW tones.')
    p.add_option('-s', '--skip_prog', dest='skip_prog', action='store_true',
        help='Skip reprogramming the FPGA and configuring EQ.')
    p.add_option('-b', '--bof', dest='boffile',type='str', default='',
        help='Specify the bof file to load')
    opts, args = p.parse_args(sys.argv[1:])


#Added by Louis Dartez: allows automatic use without arguments at execution time
#    if args==[]:
 #       print 'Please specify a ROACH board. Run with the -h flag to see all options.\nExiting.'
  #      exit()
   # else:
    roach = '192.168.4.21'#args[0] 
    if opts.boffile != '':
        bitstream = opts.boffile

    try:
        loggers = []
        lh=corr.log_handlers.DebugLogHandler()
        logger = logging.getLogger(roach)
        logger.addHandler(lh)
        logger.setLevel(10)
    
        print('Connecting to server %s on port %i... '%(roach,katcp_port)),
        fpga = corr.katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10,logger=logger)
        time.sleep(1)
    
        if fpga.is_connected():
            print 'ok\n'
        else:
            print 'ERROR connecting to server %s on port %i.\n'%(roach,katcp_port)
            exit_fail()
    
        print '------------------------'
        print 'Programming FPGA with %s...' %bitstream,
        if not opts.skip_prog:
            fpga.progdev(bitstream)
            print 'done'
        else:
            print 'Programming Skipped.'
        
    #    print fpga.listdev()
    
        print 'Configuring accumulation period to  %f...' % opts.acc_len,
        fpga.write_int('acc_len',opts.acc_len)
        print 'done'
    
        print 'Resetting counters...',
        fpga.write_int('cnt_rst',1) 
        fpga.write_int('cnt_rst',0) 
        print 'done'
    
        print 'Setting digital gain of all channels to %i...'%opts.gain,
    #    if not opts.skip:
    #        fpga.write_int('gain',opts.gain) #write the same gain for all inputs, all channels
    #        print 'done'
    #    else:   
    #        print 'Manual Gain Skipped.'
        fpga.write_int('gain',opts.gain)
        #set up the figure with a subplot to be plotted
    #    fig = matplotlib.pyplot.figure()
        fig = plt.figure()
        ax = fig.add_subplot(1,1,1)
    
        # start the process
        fig.canvas.manager.window.after(100, plot_spectrum)
        plt.plot([1,2,3,4])
        plt.show()
        #plot_spectrum()
        print 'Plot started.'
        #raw_input("Press Enter to continue...")
    except KeyboardInterrupt:
        exit_clean()
    except:
        exit_fail()
    
    exit_clean()

