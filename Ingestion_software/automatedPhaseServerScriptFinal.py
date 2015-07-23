"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 Narrowband Phase and Power Processing Script
 Version: 2.7.3

 Author: Eric Davis
         ecdavis@ucalgary.ca
 
 Created: 2015/03/17

 Description:
    Script to calculate the phase and power of the sideband signals from various VLF 
    transmitters. Produces a text file for the given date, site, and carrier frequency.
    Monitors six transmitters as of 03/17/2015
    
    Carrier Frequency (kHz)	Location:
            19.8	        Australia
            21.4	        Hawaii
            24.0	        Maine
            24.8	        Washington
            25.2	        North Dakota
            37.5	        Iceland

 Directions:
    Call the function 'totalphase', which is expecting a list of filenames including directory tree.

 Changelog:
   0.9.0: 
    -first trial run on server

   0.9.1:
    - touch up on directory and filename
    
    

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
import matplotlib
matplotlib.use('Agg')
import os
import struct
from pylab import sum
import math
from scipy import fft, ifft, real, pi, sin, cos, arctan, ptp
import numpy as np
import logging

def plots(filename,frange,n,slist):
    ant1 = np.zeros(n)   # Establishing the arrays 
    ant2 = np.zeros(n)   # for the data
    tarr = np.zeros(n)
    freq = np.zeros(n)        
    datanum = 0 
    filename = os.path.abspath(filename) # making filename os compatible
    try:          
        f = open((filename), 'rb')      # Opening file as bytes
            
        lines = f.read()                # to read data
        fheader = lines[:120]          # Filehader
        for x in slist:                
            sloc = fheader.find(x)   # Little script runs        
            if sloc != -1:           # through possible sitelist            
                si = x               # to find site
                break
            if x == slist[-1]:   # Assign site variable in case it doesnt get 
                si = [None]      # matches with site list
        
        tloc = lines.find(',')   # Marker for  
        ye = '20' + lines[5:7]   # getting the time
        mo = lines[3:5]          # Setting up rest 
        da = lines[1:3]         # of stuff for isodatetime
        hour = lines[tloc+1:tloc+3]
        minute = lines[tloc+3:tloc+5]
        second = lines[tloc+5:tloc+7]
    
        head = ye+mo+da
        isot = ye+ '-' +mo+ '-' +da+ 'T' +hour+ ':' +minute+ ':' +second+ 'Z'   # ISO time as a string      

        # Little routine to pull the timing crystal counts and get an accuate sampling frequency    
        timer = lines[:114].find('3G')   # Two markers depending on    
        mm = lines[:114].find('}')       #  how data is returned (3g, wifi, SD)
        oscillations = str(lines[timer-10:timer-1])  # e.g. 100000723, ,99999673
        if timer == -1:
            oscillations = str(lines[mm-28:mm-19]) 
            if mm == -1:
                oscillations = '100000000'
                logging.warning('Could not recover samples from header for file %s', filename)
        if oscillations[0] == ',':
            oscillations = int(oscillations[1:])
        else:
            oscillations = int(oscillations) 
                            
        if oscillations > 150000000:
            sampf = (((oscillations/2.0)/100000000.0)*(150000.0*((666+2.0/3.0)/667)))
        else:
            sampf = ((oscillations/100000000.0)*(150000.0*((666+2.0/3.0)/667)))   
        # End of getting sampling frequency routine

        ttot = n/sampf
              
        begin = lines.find("}") + 1
        f.seek(600000)
        end = lines.find("Data_Stop")     
        f.seek((begin))
        c = begin         # Make sure reading data as bytes starts at right place
        while c < ((end)-1):
            z = struct.unpack('>h', f.read(2))  # This is for getting
            d1 = int(''.join(map(str,z)))    # all the data in the correct form
            ant1[datanum] = d1               # and into a single integer array
        
            d = struct.unpack('>h', f.read(2))  # This is for getting
            d2 = int(''.join(map(str,d)))    # all the data in the correct form
            ant2[datanum] = d2               # and into a single integer array
        
            tarr[datanum] = 1/sampf * datanum
            freq[datanum] = datanum/ttot
            
            datanum += 1
            c += 4
        f.close()
        
        fft1 = fft(ant1)/n
        fft2 = fft(ant2)/n

        red = 'yes'

    except:
        ant1 = [None]
        ant2 = [None]
        tarr = [None]
        fft1 = [None]
        fft2 = [None]
        sampf = [None]
        isot = [None]
        head = [None]
        ye = [None]
        mo = [None]
        da = [None]
        si  = [None]
        red = 'no' 
        logging.error('Could not open file %s' % filename)
    return ant1,ant2, tarr, fft1, fft2, sampf, isot, head, ye, mo, da, si, red


def filters(carfarr,sampf,n,fft1,fft2):
    filtered = []
    power = []
    
    for freq in carfarr:      # Doing a list of all the narrow band signals for each frequency
        ft1 = np.array(fft1)
        ft2 = np.array(fft2)

        # Establishing the filter frequency range
        carf = float(freq)

        lowerbound = carf - 150  # This gives the narrow band filter a range of 
        upperbound = carf + 150   # 300 Hz to collect the spillover in frequency 
                    
        # This function gets the specific bins for a given frequency range and converts the others to zeroes        
        #  Establishing boundary bins of filter  
        start1 = int((lowerbound/sampf)*n)
        end1 = int((upperbound/sampf)*n)
        start2 = n - end1 + 1               
        end2 = n - start1 + 1
        # zeroing all other bins but the signal on both antennas
        ft1[0:start1] = 0
        ft1[end1:start2] = 0
        ft1[end2:] = 0
        ft2[0:start1] = 0
        ft2[end1:start2] = 0
        ft2[end2:] = 0

        # Getting the power
        power1 = sum(abs(ft1)**2)
        power2 = sum(abs(ft2)**2)
    
        filtered1 = ifft(ft1)
        filtered2 = ifft(ft2)  
        # imaginary signal should be mostly zero anyways but just in case
        filtered1 = real(filtered1)
        filtered2 = real(filtered2)
        
        # Extending the power and narrow band signal into one array.
        filtered.extend([filtered1,filtered2])    # signal 1 NS antenna 
        power.extend([power1,power2])           # Signal 2 EW antenna
            # Each frequency has two lists within the array corresponding to each antenna 
    return filtered, power

                
def phase(filtered, carf, sampf,tarr,bitclock,baudrate):
    uphasearr = []   # Establishing arrays to hold the entire unfiltered phase
    lphasearr = []   # in both the upper and lower sideband frequencies    
    deltaf = 50  # This is determined from baudrate and modulation scheme (MSK)

    window = 125  # This is the window the phase is calculated and averaged over for a single bit (1/6 of a full bit). This bit phase is in turn averaged over the whole second later on
    phasebitsize = len(filtered[0])/window/baudrate   # data points in a bit in phase time series (6)
    rawbitsize = len(filtered[0])/baudrate    # data points in a bit in raw signal time series (750)
    
    bins = len(filtered[0])/window - phasebitsize    # Lose a full bits worth of data points(6) to start in sync with bitclock
    time = np.array(tarr)   # Just to not f up the 'tarr' array created a 'time' array

    for k in range(0,len(filtered)):
        modu = carf[k] + deltaf   # The sideband frequencies used in the 
        modl = carf[k] - deltaf   # MSK modulation scheme
        
        startbin = (np.abs(time - bitclock[k])).argmin()    # Start measuring the phase at start of measured bitclock
        endbin = startbin - rawbitsize   # Endbin will be negative to make sure it is even splitting the time series into chunks 1/6 of a bit in length

        uy = filtered[k]*sin((2.0)*(pi)*modu*time)   # Crunching the phase in segments 
        ux = filtered[k]*cos((2.0)*(pi)*modu*time)   # 1/6 of a bit in length                
        uysum = np.split(uy[startbin:endbin],bins)  # Summed over this whole segment for 
        uxsum = np.split(ux[startbin:endbin],bins)  # phase measurement
        uphase = -arctan((sum(uysum, axis = 1))/(sum(uxsum, axis = 1)))   # a phase for upper and lower sidebands in MSK modulation
                                                
        ly = filtered[k]*sin((2.0)*(pi)*modl*time)  # Crunching the phase in segments 
        lx = filtered[k]*cos((2.0)*(pi)*modl*time)   # 1/6 of a bit in length      
        lysum = np.split(ly[startbin:endbin],bins)  # Summed over this whole segment for
        lxsum = np.split(lx[startbin:endbin],bins)  # phase measurement         
        lphase = -arctan((sum(lysum, axis = 1))/(sum(lxsum, axis = 1)))  # this is the lower sidebands phase
        
        lphasearr.extend([lphase])  # Adding the arrays of uppper phase
        uphasearr.extend([uphase])  # and lower phase for each frequency
    
    return uphasearr, lphasearr  # Each element in array has 1194 datapoints


def bitphase(uphase,lphase):
    ubitphase = []
    lbitphase = []
    for yy in range(0,len(uphase)):
        uph = []
        lph = []
        for xx in range(0,199):
            bitstart = xx*6
            sbin = bitstart+1
            ebin = bitstart+5
            ubit = uphase[yy][sbin:ebin]
            lbit = lphase[yy][sbin:ebin]
            upperrange = ptp(ubit)   # ptp Finds the range in the 
            lowerrange = ptp(lbit)   # respective bits

            if upperrange < 0.15:          # This is just 
                meanubit = np.mean(ubit)   # to establish
                uph.extend([meanubit])     # any bits used in the 
            if lowerrange < 0.15:          # overall median calc are locked on (ranges less than 0.15 over bit)
                meanlbit = np.mean(lbit)   # This means there are a different amount of valid 
                lph.extend([meanlbit])     # bits for the upper and lower sideband frequencies
        ubitphase.extend([uph])
        lbitphase.extend([lph])            
    ubitphase = np.array(ubitphase)
    lbitphase = np.array(lbitphase)    
    return ubitphase, lbitphase

        
def operationbitclock(ubitphase,lbitphase,lefile):
    bitclock = [None]*len(ubitphase)
    umed = [None]*len(ubitphase)
    lmed = [None]*len(ubitphase)
    for j in range(0,len(ubitphase)):
        umedian = np.median(ubitphase[j])
        lmedian = np.median(lbitphase[j])
        umed[j] = umedian
        lmed[j] = lmedian
    
        bc = (abs(umedian-lmedian)/pi)*0.005 
        if math.isnan(bc) == True:  # Sometimes never get a reasonable signal on one 
            bc = 0                  # or both sidebands, this is to catch that
            logging.warning('no bitclock recovered for %s',lefile)
        bitclock[j] = bc

    return bitclock, umed, lmed


####### This is the function that calls all the others defined above
def totalphase(filelist, logger):
    global logging
    logging = logger
    logging.info("This is a test")

    ################ ESTABLISHING CONSTANTS #####################
    sitelist = ['atha','barr','cmrs','fsmi','pina']  # SITLELIST AS OF 02/27/2015. WILLL NEED TO UPDATED WHEN MORE SITES ARE ADDED
    carfarr = [19800,21400,24000,24800,25200,37500] # The frequencies monitored. [Australia, Hawaii, Maine, Washinton, North Dakota, Iceland]    
    frange = 15             # constants used for 
    n = frange * 10000      # every file and 
    baudrate = 200          # every frequency

    print("INSIDE THE THREAD")
    print(filelist)
    
    for thisfile in filelist:
        # The array for the bitclocks of each frequency monitored. 
        NSbitclock= [0]*(len(carfarr))      # One for bitclock from NS signal and 
        EWbitclock= [0]*(len(carfarr))      # another array for EW signals   
 
        ################## NOW CALLING THE FUNCTIONS TO PROCESS THE DATA ######################       
        ant1,ant2, tarr, fft1, fft2, sampf, isotime, header, year, month, day, site,red = plots(thisfile,frange,n,sitelist)   # ant1,ant2, tarr, fft1, fft2, freq are all 150000 length arrays of 1s
        if red == 'yes':    # 'red' is the marker for if file got read or not... I am not a creative man
            filtered, power = filters(carfarr,sampf,n,fft1,fft2)    # filtered is list of narrowband signals, two columns of 150000 for each frequncy. 1st column is NS antenna, 2nd is EW antenna.
                                                                                        # power is two columns for each frequency of 1 data point for power in narrow bands signal
            # Getting the narrow band signal for the corresponding carrier frequency
            NSuphase, NSlphase = phase(filtered[::2], carfarr, sampf, tarr, NSbitclock, baudrate)  # NSuphase/NSlphase has one array for each frequency
            EWuphase, EWlphase = phase(filtered[1::2], carfarr, sampf, tarr, EWbitclock, baudrate) # EWuphase/EWlphase has one array for each frequency
                    
            NSubitphase, NSlbitphase = bitphase(NSuphase,NSlphase) # Each **ubitphase/**lbitphase array splits data of
            EWubitphase, EWlbitphase = bitphase(EWuphase,EWlphase) # 200 bits for each second depending on broadcast

            NSbitclock, NSumedian, NSlmedian = operationbitclock(NSubitphase, NSlbitphase,thisfile)
            EWbitclock, EWumedian, EWlmedian = operationbitclock(EWubitphase, EWlbitphase,thisfile)
    
            ################### NOW WRITING TO THE PROCESSED DATA TO TEXT FILE ################################        
            # Establishing data into seperate arrays for entire second for each frequency
            d19800 = [isotime,round(NSumedian[0],3),round(NSlmedian[0],3),round(EWumedian[0],3),round(EWlmedian[0],3),round(power[0],3),round(power[1],3),len(NSubitphase[0]),len(NSlbitphase[0]),len(EWubitphase[0]),len(EWlbitphase[0])]       
            d21400 = [isotime,round(NSumedian[1],3),round(NSlmedian[1],3),round(EWumedian[1],3),round(EWlmedian[1],3),round(power[2],3),round(power[3],3),len(NSubitphase[1]),len(NSlbitphase[1]),len(EWubitphase[1]),len(EWlbitphase[1])]
            d24000 = [isotime,round(NSumedian[2],3),round(NSlmedian[2],3),round(EWumedian[2],3),round(EWlmedian[2],3),round(power[4],3),round(power[5],3),len(NSubitphase[2]),len(NSlbitphase[2]),len(EWubitphase[2]),len(EWlbitphase[2])]        
            d24800 = [isotime,round(NSumedian[3],3),round(NSlmedian[3],3),round(EWumedian[3],3),round(EWlmedian[3],3),round(power[6],3),round(power[7],3),len(NSubitphase[3]),len(NSlbitphase[3]),len(EWubitphase[3]),len(EWlbitphase[3])]
            d25200 = [isotime,round(NSumedian[4],3),round(NSlmedian[4],3),round(EWumedian[4],3),round(EWlmedian[4],3),round(power[8],3),round(power[9],3),len(NSubitphase[4]),len(NSlbitphase[4]),len(EWubitphase[4]),len(EWlbitphase[4])] 
            d37500 = [isotime,round(NSumedian[5],3),round(NSlmedian[5],3),round(EWumedian[5],3),round(EWlmedian[5],3),round(power[10],3),round(power[11],3),len(NSubitphase[5]),len(NSlbitphase[5]),len(EWubitphase[5]),len(EWlbitphase[5])]       
        
            alldata = [d19800,d21400,d24000,d24800,d25200,d37500]      # And making them all into one array easing the coding 
                
            for fileidx in range(0,len(carfarr)):
                direc = os.path.join('data','vlf','phasedata',year,month,day) # Folder to write the file to
                if not os.path.exists(direc):
                    os.makedirs(direc)   
                currentf = direc+'/'+header+'_'+site+'_'+str(carfarr[fileidx])+'_phase_power.txt'
                currentf = os.path.abspath(currentf)   # Making filename os cross compatible    
                
                entry = str(alldata[fileidx])  # Editing 
                entry = entry.replace("'","")  # data string
                entry = entry.replace(",","")  # into a 
                entry = entry.replace("[","")  # readable 
                entry = entry.replace("]","")  # format
                
                if os.path.isfile(currentf) == False:   # If file doesn't exist yet it will write a header
                    g=open(currentf,'w') 
                    g.writelines('Site:' + site + '     Carrrierfrequency:' + str(carfarr[fileidx]))      
                    g.write('\n')
                    g.writelines('ISOTime NSPhaseUpperSideband NSPhaseLowerSideband EWPhaseUpperSideband EWPhaseLowerSideband NSSignalPower EWSignalPower NS_UValidbits NS_LValidbits EW_UValidbits EW_LValidbits')
                    g.write('\n')  
                    
                    g.write(entry)        
                    g.close()   
                else:
                    h =open(currentf,'r+') 
                    llines = h.readlines()
                    
                    last = llines[-1]      # Last line of data entered        
                    last2 =  llines[-2]    # Second last line of data entered
                    oldtime = last[:20]    # Timestamp of last entry
                    oldertime = last2[:20] # timestamp of entry from two files ago
                    h.seek(0)
                    tess = h.read()
                    xx = tess.find(last)  # marker to find where last line is

                    newm = entry.find('Z')  
                    newtime =  entry[:newm+1]  # Current timestamp

                    if newtime > oldtime:
                        h.seek(xx+100)            
                        h.write('\n')
                        h.write(entry)  
                    elif  newtime == oldtime:
                        logging.error('No data written, same timestamp as previous line %s', currentf[-35:])
                    elif newtime < oldertime:  
                        logging.error('No data written, timestamp is too old %s', currentf[-35:])                    
                    elif newtime < oldtime:   # Rewrites last two lines if for whatever reason files come in out of order
                        h.seek(xx)
                        h.write('\n')
                        h.write(entry)
                        h.write('\n')
                        h.write(last)   
                        logging.info('Current timestamp %s was earlier than previous timestamp %s', newtime, oldtime) 
                    h.close()
               
