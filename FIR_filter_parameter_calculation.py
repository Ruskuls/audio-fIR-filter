# Import all necessary libraries
import numpy as np
import scipy
import scipy.signal
import matplotlib.pyplot as plt
import math
import sys
import serial
import struct

# COM port configuration, on FPGA UART baudrate is fixed - 19200, other baudrates won't work
port = "/dev/ttyAMA0"
rate = 19200

#Check if entered value is non zero and is integer type
def string_to_int(value_to_convert, default_value):
    try:
        return int(value_to_convert)
    except ValueError:
        print "Entered value is not an integer"
        print "Default value will be used - ", default_value
        return default_value

#Check if entered value is non zero and is integer type
def string_to_float(value_to_convert, default_value):
    try:
        return int(value_to_convert)
    except ValueError:
        print "Entered value is not an floating point value"
        print "Default value will be used - ", default_value
        return default_value


# Get frequency sample rate from command line input
FreqSampleRate_input = raw_input("Please enter Frequency Sample Rate (integer): ")

#Convert input value to integer
FreqSampleRate = string_to_int(FreqSampleRate_input, 48000)

# Get FIR Filter length from command line input
FIRlength_input = raw_input("Please enter used FIR filter length (integer): ")

#Convert input value to integer
FIRlength = string_to_int(FIRlength_input, 4096)

# Calculate Frequency Resolution from input values
FreqResolution = float(FreqSampleRate)/float(FIRlength)

# Get low-end frequency from command line input
Lowest_frequency_input = raw_input("Please enter Low-end frequency: ")
Lowest_frequency_input = string_to_float(Lowest_frequency_input, FreqResolution)

spl_lin_array_decimated = []
normalized_spl_array = []
sample_count_from_measurement = 1703

# Use measured data or pass simple unity gain filter
use_measured_data = raw_input("Please select, use maseured data, Y/N: ")
if use_measured_data in ['N', 'n', 'no', 'No', 'NO']:
	print "You selected unity gain filter response"
	length = float(FreqSampleRate/FIRlength)
	length = 20000/length
	length = int(round(length))
	print length
	normalized_spl_array.append(0)
	for k in range(1,1816):
		normalized_spl_array.append(1)

else:
	# Get frequency sample rate
	#Calculate decimation factor
	fp = open('lin_spaced_measurement_12_09_2015.txt', 'r')
	lines = fp.readlines()
	freq_lin_array = []
	for k in range(14,16):
	    l =  lines[k]
	    arry = l.split(" ")
	    freq_lin = arry[0]
	    freq_lin = float(freq_lin)
	    freq_lin_array.append(freq_lin)
	fp.close()
    
	#Calculate frequency step
	frequency_step = freq_lin_array[1] - freq_lin_array[0]
	#print frequency_step

	decimation_factor = int(FreqResolution / frequency_step)
	print decimation_factor

	# open and split all values from measurement file
	fp = open('lin_spaced_measurement_12_09_2015.txt', 'r')
	lines = fp.readlines()
	spl_index = 0
	spl_lin_array = []
	freq_lin_array = []
	phase_lin_array = []
	freq_lin_array_decimated = []
	phase_lin_array_decimated = []
	spl_inverse_array = []
	spl_to_voltage_array = []
	for k in range(14,len(lines)):
	    l =  lines[k]
	    arry = l.split(" ")
	    freq_lin = arry[0]
	    freq_lin = float(freq_lin)
	    spl_lin = arry[1]
	    spl_lin = float(spl_lin)
	    phase_lin = arry[2]
	    phase_lin = float(phase_lin)
	    spl_lin_array.append(spl_lin)
	    freq_lin_array.append(freq_lin)
	    phase_lin_array.append(phase_lin)
	fp.close()

	#Get lowest measured frequency
	start_frequency = freq_lin_array[0]
	
	#Calculate number of sample count, from measurement file
	sample_count_from_measurement = len(freq_lin_array)/decimation_factor

	# Check if sample count is odd number, if not, discard last sample
	if ((sample_count_from_measurement % 2) == 0):
		sample_count_from_measurement = sample_count_from_measurement -1

	#Find closest frequency resolution value from measurement file
	Closest_frequency_from_measurement = FreqResolution*round(Lowest_frequency_input / FreqResolution)
	print "Closest frequency", Closest_frequency_from_measurement
	tt = int(Closest_frequency_from_measurement/FreqResolution) - 1
	print "tt", tt

	if ((Closest_frequency_from_measurement - start_frequency) > 0):
	    print "Input frequency is larger then lowest measured frequency"
	    low_end_frequency_value = int(round((Closest_frequency_from_measurement-start_frequency)/frequency_step))
	else:
        # In cases when measured frequency is higher than frequency step resolution, additional filter coefficients must be added to impulse response
	    print "Input frequency is lower then lowest measured frequency"
	    #Always round up
	    g = int(np.ceil(start_frequency/Closest_frequency_from_measurement))
	    print "g", g
	    print "g*closest frequency from measurement file", g*Closest_frequency_from_measurement

	    for ones in range(0, (g-1)):
		freq_lin_array_decimated.append(frequency_step)
		spl_lin_array_decimated.append(100)

	    low_end_frequency_value = int(round((g*Closest_frequency_from_measurement-start_frequency)/frequency_step))
	    print low_end_frequency_value 

	# Perform decimation.
	for decimation in range((g-1),sample_count_from_measurement):
	    freq_lin_array_decimated.append(freq_lin_array[decimation_factor*(decimation)+low_end_frequency_value])
	    spl_lin_array_decimated.append(spl_lin_array[decimation_factor*(decimation)+low_end_frequency_value])
	    phase_lin_array_decimated.append(phase_lin_array[decimation_factor*(decimation)+low_end_frequency_value])

	# Calculate inverse function of measured AFR
	#first step is to acquire average value of AFR
	spl_avarage = np.mean(spl_lin_array_decimated)
	print spl_avarage

	# Create inverse function of provided AFR curve
	for l in range(0,sample_count_from_measurement):
	    # If SPL reading is higher than average spl, then difference is substracted from avarge spl
	    if spl_lin_array_decimated[l] > spl_avarage:
	        spl_inverse = spl_avarage - (spl_lin_array_decimated[l]-spl_avarage)
	    # If SPL reading is lower than average spl, then difference is added to avarge spl value
	    else:
	        spl_inverse = (spl_avarage - spl_lin_array_decimated[l]) + spl_avarage
	    # Calculated inverse values are stored to array
	    spl_inverse_array.append(spl_inverse)

	# convert DB values to voltage units -> y = 10^(DB/20)
	for k in range(0,sample_count_from_measurement):
	    spl_to_voltage = math.pow((spl_inverse_array[k]/20),10)
	    spl_to_voltage_array.append(spl_to_voltage)

	# normalize maximum voltage
	for n in range(0,len(spl_to_voltage_array)):
	    normalized_spl = spl_to_voltage_array[n]/max(spl_to_voltage_array)
	    normalized_spl_array.append(normalized_spl)


#IFFT calculation
coeff = np.fft.irfft(normalized_spl_array,FIRlength)

coeff_shifted = np.fft.ifftshift(coeff)

#Normalize coefficients to maximize bit usage.
coeff_mult_value = 32767/max(coeff_shifted)

#convert floating point number to 16-bit signed integer
coeff_int16 = np.int16(coeff_shifted*coeff_mult_value)

#Write processed data to txt file
coeff_fp = open('coeff.txt', 'w+')
for write_lines in range(0,len(coeff_int16)):
    coeff_fp.write(str(coeff_int16[write_lines])+'\n')

coeff_fp.close

#Send converted 16-bit data through serial port to an FPGA
#ser = serial.Serial(port, rate, timeout = 10, parity = serial.PARITY_NONE)
#converted_data_rray = []

#for num in range(0, len(coeff_int16)):
#    converted_data = struct.pack('<h', coeff_int16[num])
#    converted_data_rray.append(converted_data)
#    ser.write(converted_data)
#ser.close()

# Plotting calculated variables
#acquire actual frequency plot graphs for displaying calculated AFR
w,h = scipy.signal.freqz(coeff_shifted)

plt.figure("""Freqz plot""")
plt.plot(w, 20*np.log10(abs(h)), 'r')
plt.show()
