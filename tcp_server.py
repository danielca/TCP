#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 TCP Server Script
 Version: 0.10.1

 Author: Darren Chaddock
 Created: 2014/02/27

 Edited By: Casey Daniel
 Edited: 2014/05/06

 Description:
    TCP Server to respond to data file transmissions from
    the FPGA->WiFly Module.

 Changelog:
   0.9.0:
     -initial release

   0.9.1:
     -Server now starts file_manager.py to combine the files
     -NOTE: This version is still untested

   0.10.0:
     -Removed combining of files
     -Removed file_manager.py
     -Re-Structure to be less dependent on closing of connections.
     -Removed milliseconds from file name
     -NOTE: Still untested

   0.10.1:
    -Added test directories for testing on a macbook
    -fixed bug for crashing with log files directories

 TODO:
  -Test Server
  -look into damon processes

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""

import socket
from socket import error as SocketError
import time
from sys import exit
import datetime
import glob
import os
import sys
from logging import root
import thread
import logging
import logging.handlers
import subprocess
from threading import Thread

# globals
#TCP_IP = "136.159.51.230" #Sever IP
TCP_IP = "136.159.51.194" #Test IP for Casey's Mac
TCP_PORT = 25000
BUFFER_SIZE = 1024
LOG_PATH = "/logs"
LOG_FILENAME = "above_vlf_acquire_server.log"
#ROOT_FILE_PATH = "/data/vlf" #Sever Root Path
ROOT_FILE_PATH = "/Users/Casey/Desktop/AboveTest/AboveRawData" #Test path for Casey's Mac
TOTAL_CHUNKS_PER_FILE = 45
YEAR_PREFIX = "20"
CONNECTION_BACKLOG = 5
threadCount = 0
fileChunksReceived = 0
logger = None

# socket globals
SOCKET_TIMEOUT_ON_CONNECTION = 30.0 
SOCKET_TIMEOUT_NORMAL = None

# logging strings
LOGFILE_MAX_BYTES = 1024000 * 100   #100MB
LOGFILE_BACKUP_COUNT = 5

# control strings
CONTROL_CLOSE = "[CTRL:close]"
CONTROL_HSK_REQUEST = "[CTRL:reqhsk]\0"
CONTROL_HSK_RECEIVE = "[CTRL:hskvals]"
CONTROL_DATA_START = "[CTRL:dstart]"
CONTROL_DATA_END = "[CTRL:dend]"
CONTROL_DATA_REQUEST = "[CTRL:dr-00:00]\0"
CONTROL_DATA_RESPONSE_OK = "[CTRL:d-ok]\0"
CONTROL_DATA_RESPONSE_NOK = "[CTRL:d-resend]\0"
CONTROL_WAKEUP_CALL_RECEIVE = "[CTRL:wakeup]"
CONTROL_WAKEUP_CALL_SEND = "[CTRL:awake]\0"


##################################
# initialize the logging file
##################################
def initLogging():
    global logger
    print "\n-----------------"
    print "Initializing logging"
    
    # initialize the logger
    logger = logging.getLogger("ABOVE VLF Acquisition Logger")
    logger.setLevel(logging.DEBUG)
    LogPath = os.path.join(ROOT_FILE_PATH, "logs")
    if not os.path.exists(LogPath):
        os.makedirs(LogPath)
    LOG_FILE = os.path.join(LogPath,LOG_FILENAME)
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=LOGFILE_MAX_BYTES, backupCount=LOGFILE_BACKUP_COUNT)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s","%Y-%m-%d %H:%M:%S UTC")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # write initial messages
    logger.info("+++++++ ABOVE VLF Acquire Server +++++++")
    logger.info("Initializing TCP server ... ")
    
    # return
    print "Logging initialized, refer to log file for all further messages"
    print "  '%s'" % (LOG_FILENAME)
    print "-----------------"
    return 0
 

##################################
# record a chunk failure (and 
# signal for a resend)
##################################
def recordChunkFailure(hsk, chunkNumber):
    #init
    global logger
  
    # set and write info string
    hskSplit = hsk[1:-1].split(',')
    day = hskSplit[0][:2]
    month = hskSplit[0][2:4]
    year = YEAR_PREFIX + hskSplit[0][4:]
    hour = hskSplit[1][:2]
    minute = hskSplit[1][2:4]
    second = hskSplit[1][4:6]
    milliseconds = hskSplit[1][7:]
    siteUID = hskSplit[6]
    deviceUID = hskSplit[8]
    headerString = datetime.datetime.now().strftime("[%Y/%m/%d %H:%M:%S UTC]")
    dropString = "Requesting retransmit of chunk %02d (%s%s%s_%s%s%s_%s_%s_%02d.chunk.dat)\n" % (int(chunkNumber), year, month, day, hour, minute, second, siteUID, deviceUID, int(chunkNumber))
    logger.info(dropString)


##################################
# Write the data to a file
##################################
def writeDataToFile(data, hsk):
    # init 
    global logger
    
    # set filename
    hskSplit = hsk[1:-1].split(',')
    day = hskSplit[0][:2]
    month = hskSplit[0][2:4]
    year = YEAR_PREFIX + hskSplit[0][4:]
    hour = hskSplit[1][:2]
    minute = hskSplit[1][2:4]
    second = hskSplit[1][4:6]
    milliseconds = hskSplit[1][7:]
    chunkNumber = hskSplit[2]
    siteUID = hskSplit[6]
    deviceUID = hskSplit[8]
    filePath = "%s/%s/%s/%s/%s_%s/ut%s" % (ROOT_FILE_PATH, year, month, day, siteUID, deviceUID, hour)
    filename = "%s%s%s_%s%s%s_%s_%s_%02d.chunk.dat" % (year, month, day, hour, minute, second, siteUID, deviceUID, int(chunkNumber))
    fullFilename = "%s/%s" % (filePath, filename)
    
    # create path for destination filename if it doesn't exist
    if not (os.path.exists(filePath)):
        logger.info("Creating directory path '%s'" % (filePath))
        os.makedirs(filePath, mode=0755)

    try:
        # init
        fp = open(fullFilename, "wb")
        
        # write hsk and data
        fp.write(hsk)
        fp.write(data)
        
        # close
        fp.close()
        logger.info("Wrote data to individual chunk file '%s'" % (fullFilename))
    except IOError, e:
        logger.error("IOError when writing data to individual chunk file: %s" % (str(e)))
        return 1
    
    # return
    return 0

#################################
# Process the connection
#################################
def processConnection(threadNum, conn, addr, socket):
    # init
    global logger
    global threadCount
    global fileChunksReceived
    logger.info("THREAD-%02d: New connection from: %s:%d" % (threadNum, addr[0], addr[1]))
    socket.settimeout(SOCKET_TIMEOUT_ON_CONNECTION)
    
    try:
        data = ""
        hsk = ""
        packetCount = 0
        dataPacketInfo = []
        writeFileFlag = True
        wakeupWait = False
        dataReceivedFlag = False
        CloseConnection = False
        
        # while there is data coming in
        while 1:
            packet = conn.recv(BUFFER_SIZE)
            if (packet.startseith(CONTROL_CLOSE)):
                CloseConnection= True
                break #connection close request

            if (wakeupWait == True or dataReceivedFlag == True):  # will wait for an empty packet from the FPGA to signal that it has remotely closed the connection
                if not packet: 
                    break  # empty packet

            elif (packet.startswith(CONTROL_WAKEUP_CALL_RECEIVE)):
                conn.send(CONTROL_WAKEUP_CALL_SEND)
                logger.info("Received wakeup call: '%s' and sending response '%s'" % (packet, CONTROL_WAKEUP_CALL_SEND))
                writeFileFlag = False
                wakeupWait = False
                continue

            elif (packet.startswith(CONTROL_HSK_RECEIVE)):
                packet = packet.lstrip(CONTROL_HSK_RECEIVE)
                if (len(packet) != 0 and packet[0] == '{' and packet[-1] == '}'):  # HSK values received OK in one packet
                    hsk = packet
                    logger.info("Received HSK data string: '%s'" % (hsk))
                    conn.send(CONTROL_DATA_REQUEST)

                else:
                    logger.warning("Received invalid formed HSK packet, requesting resend")
                    conn.send(CONTROL_HSK_REQUEST)
                    writeFileFlag = False

            else:
                dataPacketInfo.append([len(packet), datetime.datetime.now().strftime("%s")])
                packetCount += 1
                logger.debug("%d (%d bytes)" % (packetCount, len(packet)))
                if not packet: 
                    break  # empty packet

                data += packet
                if (data.endswith(CONTROL_CLOSE)):
                    data = data.rstrip(CONTROL_CLOSE)
                    dataReceivedFlag = True
                    break
                    
        # set and check the total chunk size that we expect (information needed is in the HSK)
        if (dataReceivedFlag == True):
            try:
                hskSplit = hsk[1:-1].split(',')
                dataBytes = hskSplit[-3]
                startStringBytes = hskSplit[-2]
                stopStringBytes = hskSplit[-1]
                
                # set expected chunk size
                expectedChunkSize = int(dataBytes) + int(startStringBytes) + int(stopStringBytes)
                
                # set hsk values to make sure that we got them all
                day = hskSplit[0][:2]
                month = hskSplit[0][2:4]
                year = YEAR_PREFIX + hskSplit[0][4:]
                hour = hskSplit[1][:2]
                minute = hskSplit[1][2:4]
                second = hskSplit[1][4:6]
                milliseconds = hskSplit[1][7:]
                chunkNumber = hskSplit[2]
                siteUID = hskSplit[6]
                deviceUID = hskSplit[8]
                
                # check cases to see if we need a resend request
                if (day == "" or month == "" or year == YEAR_PREFIX or hour == "" or minute == "" or second == "" or milliseconds == "" or chunkNumber == "" or siteUID == "" or deviceUID == ""):  # check we got all hsk values we need
                    raise Exception("Didn't receive all HSK values we needed")
                elif (len(data) == expectedChunkSize):  # check expected chunk size
                    logger.info("Chunk received complete (%d bytes, %d packets), responding with success control" % (expectedChunkSize, packetCount))
                    conn.send(CONTROL_DATA_RESPONSE_OK)
                else:
                    logger.warning("Chunk received incomplete (%d bytes, %d packets), responding with failure control" % (len(data), packetCount))
                    recordChunkFailure(hsk, fileChunksReceived)
                    conn.send(CONTROL_DATA_RESPONSE_NOK)
                    writeFileFlag = False  # don't bother writing the file
            except Exception, e:
                logger.warning("Malformed HSK, cannot extract metadata information: %s" % (str(e)))
                recordChunkFailure(hsk, fileChunksReceived)
                conn.send(CONTROL_DATA_RESPONSE_NOK)
                writeFileFlag = False  # don't bother writing the file
            
            # wait for close connection empty packet
            packet = conn.recv(BUFFER_SIZE)
            if not packet: 
                pass  # empty packet
            else:
                logger.error("Got more data for some reason, forcibly close connection.")
                conn.close()
                threadCount -= 1
                return 0
        
        # close connection
        if CloseConnection:
            logger.info("Safely closing connection")
            conn.close()
        if (writeFileFlag == True):
            # write data
            ret = writeDataToFile(data, hsk, fileChunksReceived)
            fileChunksReceived += 1
            
            # check if it is time to build the full file out of all the chunks
            logger.info("Received %d/%d chunks" % (fileChunksReceived, TOTAL_CHUNKS_PER_FILE))
            if (fileChunksReceived == TOTAL_CHUNKS_PER_FILE):
                fileChunksReceived = 0
        logger.debug("++++++++++++++")
    except SocketError, e:
        logger.error("Socket error: " + str(e))
        try:
            conn.close()
            logger.info("Safely closed connection")
        except Exception, e:
            logger.error("Error closing connection after socket error")
        logger.debug("++++++++++++++")
        
        # return
        socket.settimeout(SOCKET_TIMEOUT_NORMAL)
        threadCount -= 1
        return 1
        
    # return
    socket.settimeout(SOCKET_TIMEOUT_NORMAL)
    threadCount -= 1
    return 0



#################################
# MAIN METHOD
#################################
def main():
    # initialization routines
    global logger
    global threadCount
    initLogging()
    
    # bind and listen on the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # SOCK_STREAM = TCP, SOCK_DGRAM = UDP
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(SOCKET_TIMEOUT_NORMAL)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(CONNECTION_BACKLOG)  # listen with buffer of n connections
    logger.info("Listening on port %d (%d connection backlog)... " % (TCP_PORT, CONNECTION_BACKLOG))
    logger.info("++++++++++++++++++++++++++++++++++++++++")
    
    fileChunksReceived = 0
    while (1):
        try:
            # accept connections
            conn, addr = s.accept()
            threadCount += 1
            thread.start_new_thread(processConnection, (threadCount, conn, addr, s))
        except SocketError, e:
            logger.error("Socket error: " + str(e))
            try:
                conn.close()
                logger.info("Safely closed connection")
            except Exception, e:
                logger.error("Error closing connection after socket error")
            logger.debug("++++++++++++++")
        except KeyboardInterrupt, e:
            logger.error("Keyboard interrupt encountered, quitting ... ")
            exit(0)
            

# main entry point
if (__name__ == "__main__"):
    main()
