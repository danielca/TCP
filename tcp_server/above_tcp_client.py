#! /usr/bin/env python
"""
ABOVE TCP TEST CLIENT (UNDER DEVELOPMENT)
version 2.0.0

created by: Casey Daniel
Date: May 2015


Description:
    This python program will simulate TCP Connections on the server.


Changelog:
    2.0.0:
     -N/A

"""

from math import sin
import math
import numpy as np
from numpy import fft as npfft
import socket
import datetime
import struct
from time import sleep

#Constants
bufferSize = 1024                   # Rev buffer size  
tcpAddr = "136.159.51.194"          # IP Address of the TCP server  #TESTING ON MY MAC
tcpPort = 26000                     # Port of the TCP Server        #TESTING ON MY MAC
connectionTimeout = 60              # Timeout for the socket
sampleFreq = 75000                  # 75KHz Sample Freqency
sampleSize = sampleFreq*1           # 1 second of data
spectralMaxFreq = 5000              # max frequency for the spectral data
narrowBandFreq = [25000, 55000]     # list of frequencies
narrowBandBandwidth = 25            # +- bins
narrowBandFFTSize = 1024            # Size of the FFT for the narrow band chunks
binWidth = 2                        # number of bins to average IF YOU CHANGE THIS FIGURE OUT SOMETHING
                                    # TO AVERAGE THE BINS TOGETHER
maxTimePacket = 15                  # Number of Packet Divisions for time packets
maxSpecPacket = 1                   # Number of packet divisions for spec data
maxNrbdPacket = 1                   # Number of packet divisions for Narrowband data


#CONTROL STRINGS
Wakeup          = "[CTRL:wakeup]"
DataRequest     = "[CTRL:new_data]"
HeaderSend      = "[CTRL:hdr]"
HeaderOK        = "[CTRL:hdr-ok]"
HeaderNOK       = "[CTRL:hdr-nok]"
DataOK          = "[CTRL:d-ok]"
DataNOK         = "[CTRL:d-nok]"
RecvMoreData    = "[CTRL:more-data]"
DataEnd         = "[CTRL:no-data]"
ConnectionEnd   = "[CTRL:end]"
DataStopKey     = "Data_Stop"

#Global Initializations
timeBinary = "" 
specBinary = "" 
nrbdBinary = ""
resends = 0 

"""
Data point and Data array create a time serries data signal with specified frequencies
"""
def dataPoint(i):
    return 10*sin(i*25000) + 10*sin(i*2000) + 10*sin(i*55000)

def dataArray(size):
    array = [None]*size
    for i in range(0,size):
        array[i] = dataPoint(i)
    return array

"""
Now we have come to the FFT portion of this code. Spectral and Narrowband data
require different file types. They compute the FFT, manipulate it as required,
then retrun either a 1-d or 2-d array of FFT data
"""
def specFFT(timeData):
    #compute the FFT and the bin limits
    rawFFT = npfft.fft(timeData)
    maxSpecBin = math.floor(spectralMaxFreq*len(timeData)/sampleFreq)
    rawSpecData = rawFFT[0:maxSpecBin]
    
    specData = []
    bins = []
    for i in range(0,len(rawSpecData), binWidth):
        #average bins together
        specData.append(abs(sum(rawSpecData[i:binWidth+1]))/binWidth)
        bins.append(i)
        bins.append(i+binWidth)
    return specData, bins

def nrbdFFT(timeData):
    phasors = []
    for i in range(0,len(timeData),narrowBandFFTSize):
        #Compute the FFT for each section of time
        section = npfft.fft(timeData[i:i+narrowBandFFTSize+1])
        for transmitter in narrowBandFreq:
            #Extract the bins and add them to the list of phasors
            centerBin = math.floor(transmitter*narrowBandFFTSize/sampleFreq)
            phasors.append(section[centerBin-narrowBandBandwidth:centerBin+narrowBandBandwidth+1])

    return phasors

"""
These pack functions take in time data, call the FFT functions if needed
and then pack the data into the binary formats that will be sent
"""
def packTimeData(data):
    binaryData = ""
    # make each point a binary number
    for dataPoint in data:
        binaryData += struct.pack(">h", dataPoint)
    return binaryData

def packSpecData(rawData):
    rawSpecData, specBins = specFFT(rawData)
    
    binaryData = ""
    # Pack the bin table into the binary, followed by the data
    for number in specBins:
        binaryData += struct.pack(">h", number)

    for point in rawSpecData:
        binaryData += struct.pack(">h", point)

    return binaryData

def packNrbdData(data):
    phasors = nrbdFFT(data)
    
    binaryData = ""
    # pack the phasors into a real and imaginary number combined
    for i in range(0,len(phasors)):
        for j in range(0,len(phasors[i])):
            binaryData += struct.pack(">h", phasors[i][j].real)
            binaryData += struct.pack(">h", phasors[i][j].imag)

    return binaryData

def initData():
    """
    initData is the function that creates the data, and stores them as global
    variables to be used by the transmitt functions so they only need to be 
    created once
    """
    global timeBinary
    global specBinary
    global nrbdBinary

    rawData = dataArray(sampleSize)

    timeBinary = packTimeData(rawData)
    specBinary = packSpecData(rawData)
    nrbdBinary = packNrbdData(rawData)

def sendHskData(s, date, time):
    """
    Simulates a health keeping file and sends it off in a single packet
    """
    global resends
    data = "{%s,%s,210220000.000,hsk,3.0,lab1,tst-00,151,145,167,255,600000,45000}" % (str(date), str(time))
    serverHeader = serverHeader = "{%s,%s,%d,%d,3.0,lab1,tst-00,%d,hsk}" % (date, time, 0, 1, len(data))
    data += DataStopKey

    s.send(HeaderSend)
    s.send(serverHeader)
    doneData = False
    print "sent: %s" % HeaderSend + serverHeader
    while resends <=3:
        response = s.recv(bufferSize)
        print "recieved: %s" % response
        if response == HeaderOK:
            while resends <= 3:
                s.send(data)
                print "sent data"
                dataResponse = s.recv(bufferSize)
                print "recieved: %s" % dataResponse
                if dataResponse == DataOK:
                    doneData = True
                    break
                elif dataResponse == DataNOK:
                    resends += 1
                    continue
        elif response == HeaderNOK:
            resends += 1
            continue
        if doneData:
            break
    if resends > 3:
            s.send(DataEnd)
            return 1
    
    return 0
        
def sendNrbdData(s,date,time):
    """
    Transmission of the narrow band data. Both server and narrow band header
    are created and sent along with the binary data.
    """
    global timeBinary
    global specBinary
    global nrbdBinary
    global resends
    data = nrbdBinary
    # figure out how to divide the data into packets if needed
    dataDivis = int(math.floor(len(data)/maxNrbdPacket))
    
    #For each packet
    for i in range(0,maxNrbdPacket):
        nrbdHeader = "{%s,%s,210220000.000,nrbd,3.0,lab1,tst-00,600000,664,>h,%d,%d,1,1}" % (date, time, narrowBandFFTSize, 2*narrowBandBandwidth)
        packetData = nrbdHeader
        packetData += data[i*dataDivis:(i+1)*dataDivis]
        packetData += DataStopKey

        #Assemble the headers
        serverHeader = "{%s,%s,%d,%d,3.0,lab1,tst-00,%d,nrbd}" % (date, time, 0, maxSpecPacket, len(packetData))

        response = ""
        dataResponse = ""
        
        # Send the server header and ensure it is recived
        # If more than 3 resends quit the connection
        while resends <= 3:
            # Send the server header within the confines of the server specs
            s.send(HeaderSend)
            s.send(serverHeader)
            sleep(2)

            nextData = False
            print("Sent: %s" % HeaderSend+serverHeader)
            response += s.recv(bufferSize)
            print("Recieved: %s" % response)
            
            if HeaderOK in response:
                s.send(packetData)
                sleep(2)
                while resends <=3:
                    # Now moving on to the data
                    print("Sent Data")
                    dataResponse += s.recv(bufferSize)
                    print("Recieved: %s" % dataResponse)
                    if DataOK in dataResponse:
                        nextData = True
                        dataResponse = ""
                        response = ""
                        print "Next Data Packet"
                        break
                    elif dataResponse == DataNOK:
                        retries += 1
                        dataResponse = ""
                        continue
                
            elif response == HeaderNOK:
                resends += 1
                response = ""
                dataResponse = ""
                continue

            if nextData:
                break
        if resends > 3:
            s.send(DataEnd)
            return 1
    return 0
        
def sendSpecData(s, date, time):
    """
    Transmission of the spectral data. 
    """
    global timeBinary
    global specBinary
    global nrbdBinary
    global resends
    # figure out how to divide the file up
    data = specBinary
    dataDivis = int(math.floor(len(data)/maxSpecPacket))
    response = ""
    dataResponse = ""

    # loop over the number of packets
    for i in range(0,maxSpecPacket):
        specHeader = "{%s,%s,210220000.000,spec,3.0,lab1,tst-00,600000,>h,%d,1,1}" % (date, time, sampleSize)
        packetData = specHeader
        packetData += data[i*dataDivis:(i+1)*dataDivis]
        packetData += DataStopKey

        #Assemble the headers
        serverHeader = "{%s,%s,%d,%d,3.0,lab1,tst-00,%d,spec}" % (date, time, 0, maxSpecPacket, len(packetData))
        
        # Loop to make sure the header is sent correctly
        # If it can't be done in 3 attempts, abandon connection
        while resends <= 3:
            # Send the server header within the confines of the server specs
            s.send(HeaderSend)
            s.send(serverHeader)
            sleep(2)

            nextData = False
            print("Sent: %s" % HeaderSend+serverHeader)
            response += s.recv(bufferSize)
            print("Recieved: %s" % response)
            
            if HeaderOK in response:
                s.send(packetData)
                sleep(2)
                while resends <=3:
                    # Now moving on to the data
                    print("Sent Data")
                    dataResponse += s.recv(bufferSize)
                    print("Recieved: %s" % dataResponse)
                    if DataOK in dataResponse:
                        nextData = True
                        dataResponse = ""
                        response = ""
                        print "Next Data Packet"
                        break
                    elif dataResponse == DataNOK:
                        retries += 1
                        dataResponse = ""
                        continue
                
            elif response == HeaderNOK:
                resends += 1
                response = ""
                dataResponse = ""
                continue

            if nextData:
                break

    if resends > 3:
        return 1

    return 0

def sendTimeData(s, date, time):
    """
    Transmission of the Time serries data
    """
    global timeBinary
    global specBinary
    global nrbdBinary
    global resends
    print ("Now sending Time Data")
    data = timeBinary
    response = ""
    dataResponse = ""
    #Determine how the data should be divided up
    dataDivis = int(math.floor(len(data)/maxTimePacket))
    for i in range(0,maxTimePacket):
        #Assemble a server header along with a data header
        timeHeader = "{%s,%s,210220000.000,time,3.0,lab1,tst-00,600000,664,>h}" % (date, time)
        packetData = timeHeader
        packetData += data[i*dataDivis:(i+1)*dataDivis]
        packetData += DataStopKey
        serverHeader = "{%s,%s,%d,%d,3.0,lab1,tst-00,%d,time}" % (date, time, i, maxTimePacket, len(packetData))
        respone = ""
        dataResponse = ""
        
            
        while resends <= 3:
            # Send the server header within the confines of the server specs
            s.send(HeaderSend)
            s.send(serverHeader)
            sleep(2)

            nextData = False
            print("Sent: %s" % HeaderSend+serverHeader)
            response += s.recv(bufferSize)
            print("Recieved: %s" % response)
            
            if HeaderOK in response:
                s.send(packetData)
                sleep(2)
                while resends <=3:
                    # Now moving on to the data
                    print("Sent Data")
                    dataResponse += s.recv(bufferSize)
                    print("Recieved: %s" % dataResponse)
                    if DataOK in dataResponse:
                        nextData = True
                        dataResponse = ""
                        response = ""
                        print "Next Data Packet"
                        break
                    elif dataResponse == DataNOK:
                        retries += 1
                        dataResponse = ""
                        continue
                
            elif response == HeaderNOK:
                resends += 1
                response = ""
                dataResponse = ""
                continue

            if nextData:
                s.send(ConnectionEnd)
                break

    if resends > 3:
        return 1

    return 0

def connection(dataTypes):
    """
    Start the connection. The list of data types to be sent in this 
    transmission are in an array contained in dataTypes
    """
    #Simulates one cycle of data files
    global resends
    resends = 0
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((tcpAddr, tcpPort))
    s.settimeout(connectionTimeout)
    s.send(Wakeup)

    print("Sent: %s" % Wakeup)

    response = s.recv(bufferSize)

    print("Recieved: %s" % response)

    #Add more elif for other command flows
    if response == DataRequest:
        #Get the date and time
        date = datetime.datetime.utcnow().strftime("%d%m%y")
        time = datetime.datetime.utcnow().strftime("%H%M%S.%f")
        time = time[:10]

        #Loop thorugh all the file types given and send them
        for fileType in dataTypes:
            print("Sending File Type %s" % fileType)
            if fileType == "time":
                status = sendTimeData(s, date, time)
                if status == 1:
                    s.send(ConnectionEnd)
                    return 1
                continue

            elif fileType == "spec":
                status = sendSpecData(s,date,time)
                if status == 1:
                    s.send(ConnectionEnd)
                    return 1
                continue
            elif fileType == "nrbd":
                status = sendNrbdData(s,date,time)
                if status == 1:
                    s.send(ConnectionEnd)
                    return 1
                continue
            elif fileType == "hsk":
                status = sendHskData(s, date, time)
                if status == 1:
                    s.send(ConnectionEnd)
                    return 1
                continue

        s.send(DataEnd)
        print("Sent: %s" % DataEnd)
        response = s.recv(bufferSize)
        print("Recieved: %s" % response)
        if response == ConnectionEnd:
            try:
                s.send(ConnectionEnd)
            except:
                print("Done Connection")
            return 0
    
def main():
    """
    Main loop
    Initializes the data then goes through cycles of data
    """
    initData()

    # Loop to simulate data connections
    # Current set up
    # Once an hour send hsk
    # Every 10 min send hsk
    # Every 5 min send spec and nrbd
    # This can be changed for different cycles
    while 1:
        connection(["time","spec","nrbd","hsk"])
        for j in range(0,10):
            sleep(5*60)
            connection(["spec","nrbd"])
            sleep(5*60)
            connection(["spec","nrbd","hsk"])

#Main entry point
main()
        
    
