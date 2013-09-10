#!/opt/python2.7/bin/python2.7
import numpy as np
import sys
import time
import struct
import matplotlib.pyplot as plt

def print_header(HDR):
    header_fields = ["Telescope: ","Mode: ","Observer: ", "NChan: ", "BW: ", "Center Freq.: ", "DATE: ", "Comments: "]
    for i in range(len(header_fields)):
        print header_fields[i],HDR[i*8:(i+1)*8]
if __name__ == "__main__":    
    from optparse import OptionParser

    #option parser
    p = OptionParser()
    p.set_usage('lofasm_plotter.py [args]')
    p.set_description(__doc__)
    p.add_option('-g','--gain',type='int',dest='spectGain',default=0xffffffff,
            help='Set digital gain for Spectrometer. Default is 0xffffffff.')
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
    
    if opts.playback:

        file_prefix = opts.filename[:-4]
        file_ext = opts.filename[-4:]
        if opts.interleave:
            efile = open(file_prefix+'_even'+file_ext,'rb')
            ofile = open(file_refix+'_odd'+file_ext,'rb')
            #get HEADER
            HDR = efile.read(80)
            #ofile.seek(88)
            ofile.seek(80)
            print_header(HDR)
            first_acc = '123'#efile.read(8)
        else:
            spect_file = open(file_prefix+file_ext,'rb')
            HDR = spect_file.read(80)
            first_acc = '12345678'#spect_file.read(8)
            print_header(HDR)
            
        
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
            #print "first acc: %s" %first_acc
            
          #  if opts.plot_start < first_acc:
          #      spectrums_to_jump = 0
          #  else:
          #      spectrums_to_jump = abs(int(first_acc) - int(opts.plot_start))
          #  
          #  print "plot requested: %s" % opts.plot_start
          #  print "jumping: %i" % spectrums_to_jump

            spectrums_to_jump = 0
            if opts.interleave:
                bytes_to_jump = spectrums_to_jump*4096
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
                    #acc_n = spect_file.read(8)
                    spectrum = [x for x in struct.unpack('>2048L',spect_file.read(2048*4))]

                for i in range(len(spectrum)):
                    spectrum[i] = ((freqs[i]/freqs[-1])**3.5)*(((1e-7)/0.00286990776725)*float(spectrum[i])  / (opts.spectGain)+10**-20)
                #print 'spect:',len(spectrum)i
                #print spectrum
                #print acc_n
                log_obj.set_ydata(10*np.log10(spectrum))
                #plot1.set_title('LoFASM Data Playback: %s' % acc_n)
                linear_obj.set_ydata(spectrum)
                #plot2.set_title('LoFASM Data Playback (Linear): %s' % acc_n)

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

    else:
        print "nothing to do here"
