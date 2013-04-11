import numpy as np
import matplotlib.pyplot as plt

#begin get_power
def get_power(y):
    return np.abs(y)**2
#nd get_power

#begin getSpectrum
def getSpectrum(y):
    N=len(y)
    Y = np.fft.fft(y)           #compute FFT
    midpoint = (N/2)
    Z = get_power(Y[:midpoint])
    return Z

#end getSpectrum

##############################
#begin getNumPad
def getNumPad(padded_pkt_array):
    N = len(padded_pkt_array)
    num_padded = 0
    num_data = 0
    for i in range(N):
        pkt_type = padded_pkt_array[i].typeOfPacket #get type of packet
        if pkt_type == "Zero Padding":
            num_padded += 1
      #      print "adding padded packet!"
        elif pkt_type == "Data Packet":
            num_data += 1
      #      print 'Data packet (%i)' % (i+1)
      #  print 'packet %i: %s |  P: %i   D: %i' % (i+1,pkt_type,num_padded,num_data)
    return num_padded
#end getNumPad
#############################
#begin getFFTavg
def getFFTavg(y,fft_len):
    N = len(y)
    fft_sum = np.array([0.0]*(fft_len/2))
    numAvgs = int(np.floor(float(N)/fft_len))    #this value will get truncated 

    #begin forloop
    for i in range(numAvgs):
        index = i*fft_len           #increment in multiples of fft_len (start at zero)
        if i == (numAvgs - 1):      #if at last subint (piece of the data)
            subint = y[(-1*fft_len):]   #then just assign the rest of the array to subint
        else:
            subint = y[index:index+fft_len] #otherwise only use the next window of length fft_len
        
        subfft = getSpectrum(subint)        #acquire power spectrum
        fft_sum += subfft                   #and add
    #end forloop

    fft_avg = fft_sum/float(numAvgs)        #compute avg for each bin

    return fft_avg                          #type numpy array
#end getFFTavg
