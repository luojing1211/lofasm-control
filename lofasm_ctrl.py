#!/opt/python2.7/bin/python2.7

import corr,time,numpy,struct,sys,logging,matplotlib
#import spect_dump_i_14b_28pow as SpectCtrl
import lofasm_ctrl_lib as llib


####################################################
if __name__=='__main__':
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
            default='lofasm_2013_Mar_21_1924.bof',help='Boffile to program the FPGA')
    p.add_option('-i','--roach_ip',action='store',dest='roach_ip',help='ROACH IP address')
    p.add_option('-j','--spect',action='store_true',dest='spect_mode',
            help='Run in Spectrometer Mode.')
    p.add_option('-k','--bbrec',action='store_true',dest='bbr_mode',
            help='Run in Baseband Recorder Mode.')
    p.add_option('-d','--dual',action='store_true',dest='dual_mode',
            help='Run in dual mode.')
    p.add_option('-r','--rec',action='store_true',dest='rec',help='If this flag is set then data will be written to disk.')
    p.add_option('-t','--pkts',action='store',type='int',dest='num_pkts',help='This will dictate how many packets the BBR captures during each snapshot for plotting.')
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
        exit_clean()

    #program boffile
    try:
        if opts.prog:

            if opts.boffile == '':
                msg = 'No boffile provided!'
                raise GeneralError(msg)
            else:
                print 'Programming %s...%s' % (opts.boffile,fpga.progdev(opts.boffile))
        else:
            print "Skipping boffile programming"
    except GeneralError(msg) as err:
        print err.msg
        exit_clean()

#determine which mode to run in

    if opts.spect_mode:
        #config spectrometer
        #def spect_config(fpga,acc_len=262144,gain=int(0xffffffff),rec=0):
        
        if opts.rec:
            print "Recording requested!"
            even_hndls,odd_hndls = llib.spect_config(fpga,spectAccLen,spectGain,rec=1)
            llib.run_spect(fpga,spectGain,evenHandles=even_hndls,oddHandles=odd_hndls)
        else:
            llib.spect_config(fpga,spectAccLen,spectGain)
            llib.run_spect(fpga,spectGain)

    elif opts.bbr_mode:
        if opts.rec:
            sock = llib.bbr_config(fpga)
            llib.bbr_run(opts.num_pkts,sock,rec=1)
        else:
            sock = llib.bbr_config(fpga)
            llib.bbr_run(opts.num_pkts,sock)
        pass
    elif opts.dual_mode:
        #config spect
        #config bbr
        #spawn threads for spect & bbr
        pass
