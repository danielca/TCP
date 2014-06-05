#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 TCP Server Script
 Version: 2.1.2

 Author: Darren Chaddock
 Created: 2014/02/27

 Edited By: Casey Daniel
 Edited: 2014/05/06

 Description:
    TCP Server for the ABOVE VLF Array. This server handles the incoming data from the instruments in the
    field. These files are then saved to a dump directory.
    Cleanup of these files will be handled by other processes.

 Directions:
    To start the server, it is recommended that nohup be used to ensure the server will run even after any terminal
    sessions have stopped. An example: "nohup ./tcp_server.py"

 Changelog:
   1.9.0:
     -initial release

   1.9.1:
     -Server now starts file_manager.py to combine the files
     -NOTE: This version is still untested

   2.0.0:
     -Removed combining of files
     -Removed file_manager.py
     -Re-Structure to be less dependent on closing of connections.
     -Removed milliseconds from file name
     -NOTE: Still untested

   2.0.1:
     -Added test directories for testing on a macbook
     -fixed bug for crashing with log files directories

   2.0.2:
     -Tested server
     -Bug fixes

   2.0.3:
     -Now saves everything to a single directory, and leaves for file_manager.py to sort out the directory tree
     -Removed hardcoded number of chunks, can now be found in the header
     -Will be compatible with software version 2.1+

   2.1.0:
     -Re-structured to allow for buffering of packets
     -Split while loops into ones receiving control strings, and ones receiving data
     -updated header strings for 2.1 software
     -Thread numbers now sent to logger statements to make it easier when multiple connections are received

   2.1.1:
     -Bug fixes
     -Data files will now be dumped into rawData directory

   2.1.2:
    -Added thread time out condition


 TODO:
   -look at ways to keep track of IP addresses
   -Test server
   -Consider Deaemon

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


################
#Constants
################

# globals
TCP_IP = "136.159.51.230" #Sever IP
#TCP_IP = "136.159.51.194" #Test IP for Casey's Mac
TCP_PORT = 26000
BUFFER_SIZE = 1024
LOG_PATH = "/logs"
LOG_FILENAME = "above_vlf_acquire_server.log"
ROOT_FILE_PATH = "/data/vlf/testServer" #Sever Root Path
FILE_PATH = "/rawData"
#ROOT_FILE_PATH = "/Users/Casey/Desktop/AboveTest/AboveRawData" #Test path for Casey's Mac
#TOTAL_CHUNKS_PER_FILE = 45
YEAR_PREFIX = "20"
CONNECTION_BACKLOG = 5
threadCount = 0
fileChunksReceived = 0
logger = None

# socket globals
SOCKET_TIMEOUT_ON_CONNECTION = 15.0
SOCKET_TIMEOUT_NORMAL = None

# logging strings
LOGFILE_MAX_BYTES = 1024000 * 100   #100MB
LOGFILE_BACKUP_COUNT = 5

# control strings
CONTROL_CLOSE = "[CTRL:close]\0"
CONTROL_HSK_REQUEST = "[CTRL:reqhsk]\0"
CONTROL_HSK_RECEIVE = "[CTRL:hskvals]"
CONTROL_DATA_START = "[CTRL:dstart]"
CONTROL_DATA_END = "[CTRL:dend]"
CONTROL_DATA_REQUEST = "[CTRL:dr-00:00]\0"
CONTROL_DATA_RESPONSE_OK = "[CTRL:d-ok]\0"
CONTROL_DATA_RESPONSE_NOK = "[CTRL:d-resend]\0"
CONTROL_WAKEUP_CALL_RECEIVE = "[CTRL:wakeup]"
CONTROL_WAKEUP_CALL_SEND = "[CTRL:awake]\0"

#miscilanious
PACKET_SIZE_ERROR = 256000 # 256KB
DATA_STOP_KEY = "Data_Stop\0"
THREAD_TIME_OUT = 900 #15 min


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
    filePath = os.path.join(ROOT_FILE_PATH, FILE_PATH)
    #filePath = "%s/%s/%s/%s/%s_%s/ut%s" % (ROOT_FILE_PATH, year, month, day, siteUID, deviceUID, hour)
    filename = "%s%s%s_%s%s%s_%s_%s_%02d.chunk.dat" % (year, month, day, hour, minute, second, siteUID, deviceUID, int(chunkNumber))
    fullFilename = os.path.join(filePath, filename)
    
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

##################################
#Handle the connection after the
# control awake command
##################################
def dataConnection(threadNum, conn, addr, socket, packetNo):
    global logger

    logger.info("THREAD-%s: Now starting to process the connection" % str(threadNum))
    receivedBytes = 0
    data = ""
    header = ""
    packet = ""


    dataFiles = 0
    day = ""
    month = ""
    year = ""
    hour = ""
    minute = ""
    second = ""
    milliseconds = ""
    chunkNumber = ""
    siteUID = ""
    deviceUID = ""
    TotalChunks = ""
    fileSize = ""
    StartSize = ""

    IncomingData = False

    while 1:
        packetBuff = conn.recv(BUFFER_SIZE)
        packet += packetBuff
        packetNo += 1
        logger.info("THREAD-%s: Received packet %d (%d Bytes)" % (str(threadNum), packetNo, len(packetBuff)))

        #Check if packet is empty, or is greater than anything we would expect
        if packetBuff == "":
            logger.warning("THREAD-%s: Connection unexpectedly closed, closing connection" % str(threadNum))
            return True
        if len(packet) > PACKET_SIZE_ERROR:
            logger.warning("THREAD-%s: packet is oddly large while waiting for control string" % str(threadNum))
            conn.send(CONTROL_CLOSE)
            return True

        if packet.startswith(CONTROL_HSK_RECEIVE):
            dataFiles += 1
            header += packet[len(CONTROL_HSK_RECEIVE):]
            timeout = time.time() + THREAD_TIME_OUT
            while 1:
                if time.time() > timeout:
                    logger.warning("THREAD-%s: Thread has been active for longer than %s seconds, closing connection" %
                                   str(threadNum), str(THREAD_TIME_OUT))
                    CloseConnection = True
                    return True

                if header.endswith("}") or header.endswith("}\0"):

                    try:
                        hskSplit = header[1:-1].split(",")
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
                        fileSize = hskSplit[16]
                        TotalChunks =hskSplit[17]
                        packet = ""
                        conn.send(CONTROL_DATA_REQUEST)
                        IncomingData = True
                    except IndexError:
                        logger.warning("THREAD-%s: Could not split header file, atempting resend" % str(threadNum))
                        conn.send(CONTROL_DATA_RESPONSE_NOK)
                        header = ""

                    break
                packetBuff = ""
                chars = conn.recv(BUFFER_SIZE)
                logger.info("Received %s " % str(chars))
                header += chars
                packetNo += 1
                logger.info("THREAD-%s: Received packet %d (%d bytes)" % (str(threadNum), packetNo, sys.getsizeof(chars)))
                if chars == "":
                    logger.warning("THREAD-%s: Connection unexpectedly closed" % str(threadNum))
                    return True

        if IncomingData:
            data += packet
            buff = ""
            packetBuff = ""
            timeout = time.time() + THREAD_TIME_OUT
            while 1:
                if time.time() > timeout:
                    logger.warning("THREAD-%s: Thread has been active for longer than %s seconds, closing connection" %
                                   str(threadNum), str(THREAD_TIME_OUT))
                    CloseConnection = True
                    return True
                buff = conn.recv(BUFFER_SIZE)
                packetNo += 1
                data += buff
                logger.info("THREAD-%s: Received packet %d (%d bytes)" % (str(threadNum), packetNo,
                                                                              sys.getsizeof(buff)))
                if data.endswith(DATA_STOP_KEY):
                    #conn.send(CONTROL_DATA_RESPONSE_OK)
                    logger.info("THREAD-%s: Finished data file %s/%s" % (str(threadNum), str(chunkNumber),
                                                                             str(TotalChunks)))
                    break
                if buff == "":
                    logger.warning("THREAD-%s: Connection unexpectedly closed" % str(threadNum))
                    return True
                #if sys.getsizeof(data) < PACKET_SIZE_ERROR:
                #    logger.warning("THREAD-%s: Unexpectedly large file size in atempting to collect the header" %
                #                   threadNum)
                #    recordChunkFailure(header, chunkNumber)
                #    return True

            if len(data) - sys.getsizeof(DATA_STOP_KEY) != fileSize:
                logger.warning("THREAD-%s: file does not contain the right data size, sending error response" %
                               str(threadNum))
                conn.send(CONTROL_DATA_RESPONSE_NOK)
                header = ""
                packet = ""
                data = ""
            else:
                conn.send(CONTROL_DATA_RESPONSE_OK)
            logger.info("THREAD-%s: writing data to file" % str(threadNum))
            writeDataToFile(data, header)
            header = ""
            packet = ""
            packetBuff = ""
            data = ""

        if packet.startswith(CONTROL_CLOSE):
            header = ""
            packet = ""
            packetBuff = ""
            data = ""
            logger.info("THREAD-%s: Successfully received %s/%s data files" % (str(threadNum), str(dataFiles),
                                                                                   str(TotalChunks)))
            return True

#################################
# Process the connection
#################################
def processConnection(threadNum, conn, addr, socket):
    # init
    global logger
    global threadCount
    global fileChunksReceived
    global packet
    #packet = ""
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
        
        # while there is data coming in
        timeout = time.time() + THREAD_TIME_OUT

        while 1:
            if time.time() > timeout:
                logger.warning("THREAD-%s: Thread has been active for longer than %s seconds, closing connection" %
                               str(threadNum), str(THREAD_TIME_OUT))
                CloseConnection = True
                break
            chars = conn.recv(BUFFER_SIZE)
            logger.info("Received string %s" % str(chars))
            if chars == "":
                logger.warning("Blank packet")
                CloseConnection = True
                break
            packetCount += 1
            logger.info("THREAD-%s: Received packet of size %d" % (str(threadNum), len(chars)))
            packet += chars
            if packet.startswith(CONTROL_WAKEUP_CALL_RECEIVE):
                conn.send(CONTROL_WAKEUP_CALL_SEND)
                logger.info("THREAD-%s: Received wakeup call: '%s' and sending response, starting data connection '%s'"
                            % (str(threadNum), packet, CONTROL_WAKEUP_CALL_SEND))
                dataConnection(threadNum, conn, addr, socket, packetCount)
                writeFileFlag = False
                wakeupWait = False
                break
            if len(packet) > PACKET_SIZE_ERROR:
                logger.warning("THREAD-%s: Packet length is oddly large, closing connection, STOP FAILING HERE" % str(threadNum))
                CloseConnection = True
                break

        """
        while 1:
            chars = conn.recv(BUFFER_SIZE)
            packet += chars
            if chars == "":
                CloseConnection = True
                logger.info("THREAD-%s: Received a blank packet, will close connection" % str(threadNum))
                break
                packet = packet[:-1]
            if (packet.startswith(CONTROL_CLOSE)):
                logger.info("THREAD-%s: Recieved close connection" % str(threadNum))
                CloseConnection = True
                packet = ""
                break #connection close request
            elif (packet.startswith(CONTROL_WAKEUP_CALL_RECEIVE)):
                conn.send(CONTROL_WAKEUP_CALL_SEND)
                packet = ""
                CloseConnection = processConnection(threadNum, conn, addr, socket)
                logger.info("THREAD-%s: Received wakeup call: '%s' and sending response '%s'" % (str(threadNum),
                                                                                                 packet,
                                                                                                 CONTROL_WAKEUP_CALL_SEND))
                writeFileFlag = False
                wakeupWait = False
                break
        """

        # close connection
        #if CloseConnection:
        logger.info("THREAD-%s: Safely closing connection" % str(threadNum))
        conn.close()
        packet = ""
        #if writeFileFlag:
        #    # write data
        #    ret = writeDataToFile(data, hsk)
        #    fileChunksReceived += 1
            
            # check if it is time to build the full file out of all the chunks
        #    logger.info("Received %d/%d chunks" % (fileChunksReceived, TotalChunks))
        #    if (fileChunksReceived == TotalChunks):
        #        fileChunksReceived = 0
        logger.debug("++++++++++++++")
    except SocketError, e:
        logger.error("THREAD-%s: Socket error: %s" % (str(threadNum), str(e)))
        try:
            conn.close()
            logger.info("THREAD-%s: Safely closed connection" % str(threadNum))
        except Exception, e:
            logger.error("THREAD-%s: Error closing connection after socket error" % str(threadNum))
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
    global packet
    initLogging()
    packet = ""

    # bind and listen on the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # SOCK_STREAM = TCP, SOCK_DGRAM = UDP
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(SOCKET_TIMEOUT_NORMAL)
    try:
        s.bind((TCP_IP, TCP_PORT))
    except SocketError, e:
        logger.warning("Socket error, unable to start server. %s" % str(e))
        print "************************************************"
        print " Unable to start server, program will now exit"
        print "************************************************"
        return

    s.listen(CONNECTION_BACKLOG)  # listen with buffer of n connections
    logger.info("Listening on port %d (%d connection backlog)... " % (TCP_PORT, CONNECTION_BACKLOG))
    logger.info("++++++++++++++++++++++++++++++++++++++++")
    
    fileChunksReceived = 0

    while 1:
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
