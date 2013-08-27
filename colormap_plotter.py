#!/usr/bin/python
import struct
import matplotlib.pyplot as plt
import numpy as np
import sys
import time


def freq2bin(freq):
	num_channels = 2048
	bandwidth = 200.0 #MHz
	rbw = bandwidth/num_channels

	bin_num = np.ceil(float(freq)/rbw)
	return bin_num

def sec2bin(sec_to_find,num_bins,total_time_sec):

	binwidth = total_time_sec/float(num_bins)
	offset_from_bin0 = sec_to_find % total_time_sec
	bin_num = int(np.ceil(offset_from_bin0 * binwidth) )
	print bin_num
	return bin_num

def grab_spects(num_spects,infile):
	spect_array = []
	for i in range(num_spects):
		infile.read(8)
		spect_array.append(10*np.log10(np.array(struct.unpack('>1024L',infile.read(1024*4)))))
		infile.read(1024*4)
	return spect_array	

#import lofasm_ctrl_lib as llib
filename = sys.argv[1] #first argument

infile = open(filename,'rb')

HEADER = infile.read(80) 

print "first ACC number: %s" % infile.read(8)

seconds_per_spect = .0419
seconds_to_plot = float(raw_input("How many seconds of data should be plotted at once?"))
num_spect_to_plot = int(np.ceil(seconds_to_plot / seconds_per_spect))
print "%f seconds of data = %i accumulations to be plotted at once" % (seconds_to_plot, num_spect_to_plot)

spect_array = []#np.zeros([num_spect_to_plot,2048])
infile.seek(80) # go back to beginning of data


stride=100


for i in range(num_spect_to_plot):
	spect_id = infile.read(8) #pass spectrum ID
	raw_dat = infile.read(1024*4) #read actual data
	spect_array.append(10*np.log10(np.array(struct.unpack('>1024L',raw_dat))))
	infile.read(1024*4)

#spect_array = np.array(spect_array)

bin_width = seconds_to_plot/float(num_spect_to_plot) #seconds/bin
plt.ion()
fig = plt.figure()
yticks = [freq2bin(x) for x in np.arange(0,100,10)]
ytick_labels = [str(x) for x in np.arange(0,100,10)]
xticks = [sec2bin(x,num_spect_to_plot,seconds_to_plot) for x in np.arange(0,10,1)]
xtick_labels = [str(x) for x in np.arange(0,10,1)]

colorplot = fig.add_subplot(111)
plt.title('colorplot viewer')
plt.ylim(0,1023)
#plt.ylabel('Frequency (MHz)')
#plt.yticks([x*200.0/2047 for x in range(2048)])

line_colorplot = colorplot.imshow(np.transpose(spect_array))
#colorplot.set_yticks([x for x in range(1024)])
print "the ylim is: ",colorplot.get_ylim()
colorplot.set_yticks(yticks)
colorplot.set_yticklabels(ytick_labels)
colorplot.set_xticks(xticks)
colorplot.set_xticklabels(xtick_labels)

fig.canvas.draw()
raw_input('press enter to contine')
while 1:

	new_spects = grab_spects(stride,infile)
	#print "new spectrum!"

	#remove first spectrum in spect_array
	new_array=spect_array[stride:]

	for i in range(stride):
		new_array.append(new_spects[i])
	#update diagram

	new_array = new_array

	line_colorplot.set_array(np.transpose(new_array))
	spect_array = new_array
	fig.canvas.draw()
	#time.sleep(.1)
