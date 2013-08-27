#!/opt/python2.7/bin/python2.7
#clean_data.py
#this program will clean LoFASM Data
#this program will take, as inputs, the even and odd LoFASM data files
#this program will return a clean and interleaved data set with only an 80 byte header and the data...no acc numbers

import sys
import struct
import time
import numpy as np

def getFileHeader(file_obj, hdr_size_bytes=80):
    orig_ptr = file_obj.tell()
    file_obj.seek(0)
    hdr = file_obj.read(hdr_size_bytes)
    file_obj.seek(orig_ptr)
    return hdr

def getFileSize(file_obj):
    orig_ptr_pos = file_obj.tell()
    file_obj.seek(0)
    file_obj.readlines()
    final_ptr_pos = file_obj.tell()
    file_obj.seek(orig_ptr_pos)
    total_size_bytes = final_ptr_pos

#    print "Total size of %s (bytes): %s" % (file_obj.name,total_size_bytes)
    total_size_GB = total_size_bytes / float(2**30)
    return total_size_GB

def getNextSpectID(file_obj, size_bytes=8):
    return file_obj.read(size_bytes)

def getNextSpectData(file_obj, size_bytes=2048*4):
    raw_spect = file_obj.read(size_bytes)
    struct_fmt = size_bytes/4
    spect = list(struct.unpack('>'+struct_fmt+'L',file_obj.read(size_bytes)))
    return spect

def getTotalNumberOfSpectra(total_size_bytes, spect_size_bytes=1024*4, hdr_size_bytes=80, spect_id_size_bytes=8):
    total_payload_size_bytes = total_size_bytes - hdr_size_bytes
    spect_plus_id_size_bytes = spect_id_size_bytes + spect_size_bytes

    total_number_of_spectra = total_payload_size_bytes / spect_plus_id_size_bytes
    return total_number_of_spectra

def remove_dup_acc(file_obj,hdr_len_bytes=80):
    print ("Removing Duplicate Spectrum IDs for %s..." % file_obj.name)
    sys.stdout.flush()
    original_pointer_position = file_obj.tell()
    acc_list = []
    channel_list = []
    file_obj.seek(hdr_len_bytes) #get past the header but before the first acc number
    

    first_acc = acc_num = file_obj.read(8)
    acc_list.append(acc_num) #type:string
    print "First Spect ID: %i" %int(first_acc)
    while acc_num != '':
        print "\rACC: "+str(abs(int(acc_num)-int(first_acc))+1),
        sys.stdout.flush()
        if int(acc_num) not in acc_list:
            acc_list.append(int(acc_num)) #add this acc number to the 'database'
            channel_list.extend(list(struct.unpack('>1024L',file_obj.read(1024*4))))
        else: #don't save spectra, skip over data to the front of the next acc_num
            file_obj.read(1024*4)

        acc_num = file_obj.read(8) #get next acc_num
        #print "new_acc: %i" % int(acc_num)
    print "\rDone."
    return acc_list, channel_list
        
if __name__ == "__main__":
    even_filename = sys.argv[1]
    odd_filename = sys.argv[2]
    interleaved_filename = sys.argv[3]
    if interleaved_filename == '':
        interleaved_filename = 'clean_data_ouput.dat'

    print "opening files!..."
    try:
        even_file = open(even_filename,'rb')
        odd_file = open(odd_filename,'rb')
        print "%s's size (GB): %f" % (even_file.name,getFileSize(even_file))
        print "%s's size (GB): %f" % (odd_file.name,getFileSize(odd_file))
        interleaved_file = open(interleaved_filename,'wb')
    except: 
        print "couldn't open the files!"

    num_spect_in_file = getTotalNumberOfSpectra(getFileSize(even_file)*(2**30))
    print "There are %i spectra in this file!" % (num_spect_in_file)
    even_acc_list, even_spect_data = remove_dup_acc(even_file)
    odd_acc_list, odd_spect_data = remove_dup_acc(odd_file)
    
    if even_acc_list != odd_acc_list:
        print "Something went very wrong! The acc_lists are not the same!"
        exit()
    else:
        print "ACC lists okay!"
    if len(even_spect_data) != len(odd_spect_data):
        print "Something went very wrong! The spect lists have different lengths!"
        exit()
    else: print "DATA ok!"

    #write interleaved data with no ACC's

    interleaved_file.write(getFileHeader(even_file)) #write header information

    print "Saving %f spectra to %s" %(len(even_acc_list), interleaved_file.name)
    
    for i in range(len(even_spect_data)):
        interleaved_file.write(struct.pack('>L',even_spect_data[i]))
        interleaved_file.write(struct.pack('>L',odd_spect_data[i]))

    print "Done!"
    even_file.close()
    odd_file.close()
    interleaved_file.close()
