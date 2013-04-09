import numpy as np
import matplotlib.pyplot as plt

#############################
#begin get_power
def get_power(y):
	"""if y is a list containing complex values then get_power returns
	abs(y)**2 (i.e. the power) of y"""
	return np.abs(y)**2#np.array([(x.conj()*x).real for x in y])
#end get_power
#############################
#begin getSpectrum
def getSpectrum(y):
    """returns first half of y's power spectrum
    (i.e. positive freqs)...one doesn't really NEED the others, right?
    Usage: getSpectrum(y)"""

    N=len(y)                                #length of input signal
    Y = np.fft.fft(y)                       #compute FFT, returns ndarray (numpy array)
    
    #Z = []
    midpoint = (N/2)
    #Z.extend(Y[:midpoint])                  #"up to" midpoint for positive frequencies
    Z = get_power(Y[:midpoint])                        #calculate power from voltages
    
    return Z                                #return power spectrum in positive freqs
#end getSpectrum
#############################

#begin getNumPad

def getNumPad(padded_pkt_array):
	""" Returns the number of padded packets (filled in for dropped pkts) in a list 
	or array of LoFASM Packet objects"""
	N = len(padded_pkt_array)
	num_padded = 0
	num_data = 0
	for i in range(N):
		pkt_type = padded_pkt_array[i].typeOfPacket #get type of packet
		if pkt_type == "Zero Padding":
			num_padded += 1
			print "adding padded packet!"
		elif pkt_type == "Data Packet":
			num_data += 1
			print 'Data packet (%i)' % (i+1)
		print 'packet %i: %s |   P: %i	D: %i' % (i+1,pkt_type,num_padded,num_data)
	return num_padded
#end getNumPad
###########################
#begin gettFFTavg

def getFFTavg(y,fft_len):
	#print 'fft_len:', str(fft_len),"\n",type(y)
	N = len(y)                           #get length of input signal
	fft_sum = np.array([0.0]*(fft_len/2))      #
	numAvgs = int(N/fft_len)  #this value will get truncated if N is not 
    #    perfectly divisible by fft_len
	
    #begin forloop
    for i in range(numAvgs):
		index = i*fft_len                               #increment in multiples of fft_len (start at zero)
		if i==(numAvgs-1):                              #if at last subint (piece of the data)
			subint = y[(-1*fft_len):]                   #then just assign the rest of the array to subint
		else:
			subint = y[index:index+fft_len]             #otherwise only use the next window of length fft_len

		#print 'subint length: ', str(len(subint))
		subfft = getSpectrum(subint)		            #acquire power spectrum
        fft_sum += subfft                               #and add
    #end forloop

	fft_avg = fft_sum/float(numAvgs)                    #compute average in each bin

	return fft_avg	                                    #type numpy array
#end getFFTavg
###############################
