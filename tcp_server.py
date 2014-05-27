#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 TCP Server Script
 Version: 2.1.1

 Author: Darren Chaddock
 Created: 2014/02/27

 Edited By: Casey Daniel
 Edited: 2014/05/06

 Description:
    TCP Server for the ABOVE VLF Array. This server handles the incoming data from the instruments in the
    field. These files are then saved to a dump directory.
    Cleanup of these files will be handled by other processes.

 Directions:
    To start the tcp server simply use the command ./tcp_server.py start
    Similarly to stop the server use ./tcp_server.py stop

 Changelog:
   1.9.0:
     -initial release

   1.9.1:
     -Server now starts file_manager.py to combine the files
     -NOTE: This version is still untested

   1.10.0:
     -Removed combining of files
     -Removed file_manager.py
     -Re-Structure to be less dependent on closing of connections.
     -Removed milliseconds from file name
     -NOTE: Still untested

   1.10.1:
     -Added test directories for testing on a macbook
     -fixed bug for crashing with log files directories

   2.0.0:
     -Tested server
     -Bug fixes

   2.0.1:
     -Now saves everything to a single directory, and leaves for file_manager.py to sort out the directory tree
     -Removed hardcoded number of chunks, can now be found in the header
     -Will be compatible with software version 2.1+

   2.1.0:
     -Re-structured to allow for buffering of packets
     -Split while loops into ones receiving control strings, and ones receiving data
     -updated header strings for 2.1 software
     -Thread numbers now sent to logger statements to make it easier when multiple connections are received

   2.1.1:
     -Added Deaemon to ensure the server won't be killed
     -Added documentation about the start and stop command


 TODO:
   -Examine hard coded number of files
   -look at ways to keep track of IP addresses
   -Test server

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
from daemon import runner
import subprocess
from threading import Thread


##################
#Class to handle
#the start of the
#Deaemon process
##################
class ServerDeaemon():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path =  '/tmp/tcp_server.pid'
        self.pidfile_timeout = 5

    def run(self):
        while True:
            main()


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
#ROOT_FILE_PATH = "/Users/Casey/Desktop/AboveTest/AboveRawData" #Test path for Casey's Mac
#TOTAL_CHUNKS_PER_FILE = 45
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
PACKET_SIZE_ERROR = 10000
DATA_STOP_KEY = "Data_Stop"


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
    filePath = ROOT_FILE_PATH
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
def dataConnection(theadNum, conn, addr, socket, packetNo):
    global logger
    receivedBytes = 0
    data = ""
    header = ""
    packet = ""

    recved = False
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
    while 1:
        packetBuff = conn.recv(BUFFER_SIZE)
        packet += packetBuff
        packetNo += 1
        logger.info("THREAD-%s: Received packet %d (%d Bytes)" % (str(theadNum), packetNo, len(packetBuff)))

        #Check if packet is empty, or is greater than anything we would expect
        if packetBuff == "":
            logger.warning("THREAD-%s: Connection unexpectedly closed, closing connection" % str(theadNum))
            return True
        if len(packet) < PACKET_SIZE_ERROR:
            logger.warning("THREAD-%s: packet is oddly large" % str(theadNum))
            conn.send(CONTROL_CLOSE)
            return False

        if packet.startswith(CONTROL_HSK_RECEIVE):
            dataFiles += 1
            header += packet[len(CONTROL_HSK_RECEIVE):]
            while 1:
                chars = conn.recv(BUFFER_SIZE)
                header += chars
                packetNo += 1
                logger.info("THREAD-%s: Received packet %d (%d bytes)" % (str(theadNum), packetNo, sys.getsizeof(chars)))
                if header.endswith("}"):

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
                    except IndexError:
                        logger.warning("THREAD-%s: Could not split header file, atempting resend" % str(theadNum))
                        conn.send(CONTROL_DATA_RESPONSE_NOK)
                        header = ""

                    break
                elif chars == "":
                    logger.warning("THREAD-%s: Connection unexpectedly closed" % str(theadNum))
                    return True

        if packet.startswith(DATA_STOP_KEY):
            data += packet
            buff = ""
            while 1:
                buff = conn.recv(BUFFER_SIZE)
                packetNo += 1
                data += buff
                logger.info("THREAD-%s: Received packet %d (%d bytes)" % (str(theadNum), packetNo,
                                                                              sys.getsizeof(buff)))
                if data.endswith("Data_Stop"):
                    conn.send(CONTROL_DATA_RESPONSE_OK)
                    logger.info("THREAD-%s: Finished data file %s/%s" % (str(theadNum), str(chunkNumber),
                                                                             str(TotalChunks)))
                    break
                if buff == "":
                    logger.warning("THREAD-%s: Connection unexpectedly closed" % str(theadNum))
                    return False
                if sys.getsizeof(data) < PACKET_SIZE_ERROR:
                    logger.warning("THREAD-%s: Unexpectedly large file size" % theadNum)
                    recordChunkFailure(header, chunkNumber)
                    return False

            if len(data) - len(DATA_STOP_KEY) != fileSize:
                logger.warning("THREAD-%s: file does not contain the right data size, sending error response" %
                               str(theadNum))
                #conn.send(CONTROL_DATA_RESPONSE_NOK)
                header = ""
                packet = ""
                data = ""
            logger.info("THREAD-%s: writing data to file" % str(theadNum))
            writeDataToFile(data, header)
            header = ""
            packet = ""
            data = ""

        if packet.startswith(CONTROL_CLOSE):
            logger.info("THREAD-%s: Successfully received %s/%s data files" % (str(theadNum), str(dataFiles),
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
        CloseConnection = False
        
        # while there is data coming in
        while 1:
            chars = conn.recv(BUFFER_SIZE)
            packetCount += 1
            logger.info("THREAD-%s: Received packet of size %d" % (str(threadNum), len(chars)))
            packet += chars
            if packet.startswith(CONTROL_WAKEUP_CALL_RECEIVE):
                conn.send(CONTROL_WAKEUP_CALL_SEND)
                logger.info("THREAD-%s: Received wakeup call: '%s' and sending response '%s'" % (str(threadNum),
                                                                                                 packet,
                                                                                                 CONTROL_WAKEUP_CALL_SEND))
                writeFileFlag = False
                wakeupWait = False
                break
            if len(packet) < PACKET_SIZE_ERROR:
                logger.warning("THREAD-%s: Packet length is oddly large, closing connection" % str(threadNum))
                CloseConnection = True
                break
            if not CloseConnection:
                logger.warning("THREAD-%s: Sending error message" % str(threadNum))




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
                CloseConnection= True
                break #connection close request
            elif (packet.startswith(CONTROL_WAKEUP_CALL_RECEIVE)):
                conn.send(CONTROL_WAKEUP_CALL_SEND)
                logger.info("THREAD-%s: Received wakeup call: '%s' and sending response '%s'" % (str(threadNum),
                                                                                                 packet,
                                                                                                 CONTROL_WAKEUP_CALL_SEND))
                writeFileFlag = False
                wakeupWait = False
                continue



            """

            if (wakeupWait == True or dataReceivedFlag == True):  # will wait for an empty packet from the FPGA to signal that it has remotely closed the connection
                if not packet:
                    break  # empty packet

            elif (packet.startswith(CONTROL_WAKEUP_CALL_RECEIVE)):
                print "working"
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
                    CloseConnection = True
                    break  # empty packet

                data += packet
                if (data.endswith(CONTROL_CLOSE)):
                    data = data.rstrip(CONTROL_CLOSE)
                    dataReceivedFlag = True
                    CloseConnection = True
                    break
            """



        """
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
                TotalChunks =hskSplit[19]
                
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
        """

        # close connection
        if CloseConnection:
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
    global logger
    initLogging()

    logger.info("Starting Deameon.....")

    ServerStart = ServerDeaemon()
    DeaemonRunner = runner.DaemonRunner(ServerStart)
    DeaemonRunner.do_action()
    #main()
