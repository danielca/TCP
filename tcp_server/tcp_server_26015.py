#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 TCP Server Script
 Version: 2.1.8

 Author: Darren Chaddock
 Created: 2014/02/27

 Edited By: Casey Daniel
 Edited: 2014/05/06

 Description:
    TCP Server for the ABOVE VLF Array. This server handles the incoming data from the instruments in the
    field. These files are then saved to a dump directory.
    Cleanup of these files will be handled by other processes.

 Directions:
    To start the server simply call ./tcp_server_26000.py start
    To stop the server call ./tcp_server stop
    If a restart is needed call ./tcp_server_26000.py restart

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
     -Will be compatible with header version 2.1+

   2.1.0:
     -Re-structured to allow for buffering of packets
     -Split while loops into ones receiving control strings, and ones receiving data
     -updated header strings for 2.1 software
     -Thread numbers now sent to logger statements to make it easier when multiple connections are received

   2.1.1:
     -Bug fixes
     -Data files will now be dumped into root/rawData directory

   2.1.2:
     -Added thread time out condition

   2.1.3:
     -Various bug fixes, server is now stable
     -clean-up of various debug statements

   2.1.4:
     -Bug fixes
     -More comments and descriptions
     -Stress testing is still needed

   2.1.5:
     -Finally added in the daemon process

   2.1.6:
     -Bug fixes
     -Stable release!!!!!!

   2.1.6:
     -Added new standard in and out directory

   2.1.7:
     -Standard out and standard error are now re-directed to the log file

   2.1.8:
    -Potential fix for the case where the control string is stuffed into the same packet as the data_stop key



 TODO:
   -Fix any random bugs that come up.

 BUG TRACKER:
   -Put try an expept around file size cast to an integer.
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""

import socket
from socket import error as SocketError
import time
from sys import exit
import datetime
import os
import sys
import logging
import logging.handlers
from threading import Thread
import threading
import pickle
from Daemon import Daemon
import select

################
#Constants
################

# globals
ROOT_FILE_PATH = '/data/vlf'
TCP_IP = "136.159.190.48"  # Sever IP
TCP_PORT = 26015
BUFFER_SIZE = 1024
YEAR_PREFIX = "20"
CONNECTION_BACKLOG = 5
threadCount = 0
fileChunksReceived = 0
RECV_TIMEOUT = 5
logger = None
IP_dict = {}

# socket globals
SOCKET_TIMEOUT_ON_CONNECTION = None
SOCKET_TIMEOUT_NORMAL = None

# logging strings
LOG_FILENAME = "above_vlf_tcp_server_%s.log" % str(TCP_PORT)
LOGFILE_MAX_BYTES = 1024000 * 100   # 100MB
LOGFILE_BACKUP_COUNT = 5
LOG_PATH = "logs"
FILE_PATH = "RawData"

# control strings
CONTROL_CLOSE = "[CTRL:close]"
CONTROL_HSK_REQUEST = "[CTRL:reqhsk]"
CONTROL_HSK_RECEIVE = "[CTRL:hskvals]"
CONTROL_DATA_START = "[CTRL:dstart]"
CONTROL_DATA_END = "[CTRL:dend]"
CONTROL_DATA_REQUEST = "[CTRL:dr-00:00]"
CONTROL_DATA_RESPONSE_OK = "[CTRL:d-ok]"
CONTROL_DATA_RESPONSE_NOK = "[CTRL:d-resend]"
CONTROL_WAKEUP_CALL_RECEIVE = "[CTRL:wakeup]"
CONTROL_WAKEUP_CALL_SEND = "[CTRL:awake]"

#PID file
PID_FILE = 'TCP_Server_%s.pid' % str(TCP_PORT)
PID_PATH = '/data/vlf/PID'

#miscilanious
PACKET_SIZE_ERROR = 25600000000000000  # ~256KB
DATA_STOP_KEY = "Data_Stop"
CONNECTION_TIMEOUT = 60*5
DATA_RESEND_CUTOFF = 3


#Used to override the method in daemon.py
class MyDaemon(Daemon):
    def run(self):
        main()


class StreamToLogger(object):
   """
   Class that helps take standard out and error and re-direct them to the log file
   """
   def __init__(self, logger, log_level=logging.INFO):
      self.logger = logger
      self.log_level = log_level
      self.linebuf = ''

   def write(self, buf):
      for line in buf.rstrip().splitlines():
         self.logger.log(self.log_level, line.rstrip())


##################################
# initialize the logging file
##################################
def initLogging():
    """
    initLogging starts the logging file
    :return:
    """
    global logger
    
    # initialize the logger
    logger = logging.getLogger("ABOVE VLF Acquisition Logger")
    logger.setLevel(logging.DEBUG)
    LogPath = os.path.join(ROOT_FILE_PATH, LOG_PATH)
    #check to see if the log path exists
    if not os.path.exists(LogPath):
        os.makedirs(LogPath)

    LOG_FILE = os.path.join(LogPath, LOG_FILENAME)
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=LOGFILE_MAX_BYTES, backupCount=LOGFILE_BACKUP_COUNT)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S UTC")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # write initial messages
    logger.info("+++++++ ABOVE VLF Acquire Server +++++++")
    logger.info("Initializing TCP server ... ")

     #Standard out re-direct
    outStream = StreamToLogger(logger, logging.INFO)
    sys.stdout = outStream

    #Standard error re-direct
    errorStream = StreamToLogger(logger, logging.ERROR)
    sys.stderr = errorStream
    
    # return
    return
 

##################################
# record a chunk failure (and 
# signal for a resend)
##################################
def recordChunkFailure(hsk, chunkNumber):
    """
    Records the chunk faliure and requesets a resend, not currently used
    :param hsk: Header contents
    :param chunkNumber: Chunk number that failed
    :return:
    """
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
def writeDataToFile(data, hsk, threadNum):
    """
    Writes the data taken in to a file
    :param data: raw data from the transmition
    :param hsk: Header information
    :param threadNum: Thread number, used for logging purposes
    :return:
    """
    # init 
    global logger
    # set filename
    hskSplit = hsk[1:-1].split(',')
    day = str(hskSplit[0][0:2])
    month = str(hskSplit[0][2:4])
    year = str(YEAR_PREFIX + hskSplit[0][4:6])
    hour = hskSplit[1][0:2]
    minute = hskSplit[1][2:4]
    second = hskSplit[1][4:6]
    chunkNumber = hskSplit[2]
    siteUID = hskSplit[6]
    deviceUID = hskSplit[8]
    filePath = "%s/%s" % (ROOT_FILE_PATH, FILE_PATH)
    filename = "%s%s%s_%s%s%s_%s_%s_%02d.chunk.dat" % (year, month, day, hour, minute, second, siteUID, deviceUID,
                                                       int(chunkNumber))
    fullFilename = os.path.join(filePath, filename)
    
    # create path for destination filename if it doesn't exist
    if not (os.path.exists(filePath)):
        logger.debug("THREAD-%s: Creating directory path '%s'" % (str(threadNum), filePath))
        os.makedirs(filePath, mode=0755)

    try:
        # init
        fp = open(str(fullFilename), "wb")
        
        # write hsk and data
        fp.write(hsk)
        fp.write(data)
        
        # close
        fp.close()
        logger.info("THREAD-%s: Wrote data to individual chunk file '%s'" % (str(threadNum), fullFilename))
    except IOError, e:
        logger.error("THREAD-%s: IOError when writing data to individual chunk file: %s" % (str(threadNum), str(e)))
        return
    
    # return
    return


##################################
#Handle the connection after the
# control awake command
##################################
def dataConnection(threadNum, conn, addr, socket, packetNo):
    """
    Handles the data connection from the client, including receving the header and the binary data
    The dictionary is writen to file if a new IP is found, and this is then passed on to the ingestion scripts
    :param threadNum: Thread number for logging purposes
    :param conn: connection used
    :param addr: IP addres of the connection
    :param socket: Socket used
    :param packetNo: the number of packets already received from this connection
    :return:
    """
    global logger

    logger.debug("THREAD-%s: Now starting to process the connection" % str(threadNum))
    dataResends = 0
    data = ""
    header = ""
    packet = ""


    dataFiles = 0
    chunkNumber = ""
    siteUID = ""
    TotalChunks = ""
    fileSize = ""

    IncomingData = False


    timeout = time.time() + CONNECTION_TIMEOUT
    while 1:
        packetBuff = conn.recv(BUFFER_SIZE)
        packet += packetBuff
        packetNo += 1
        #Total connection timeout
        if time.time() > timeout:
            logger.warning("THREAD-%s: Connection has been established longer than %s seconds, closing connection" %
                        (str(threadNum), str(CONNECTION_TIMEOUT)))
            return dataResends

        #Check if packet is empty
        if packetBuff == "":
            logger.warning("THREAD-%s: Connection unexpectedly closed, closing connection" % str(threadNum))
            return dataResends

        #Check for controll close
        if CONTROL_CLOSE in packet:
            logger.info("THREAD-%s: Received close command, now closing the connection" % str(threadNum))
            return dataResends

        if packet.startswith(CONTROL_WAKEUP_CALL_RECEIVE):
            logger.info("THREAD-%s: Received control wakeup, sending %s and retrying connection" %
                        (str(threadNum), CONTROL_WAKEUP_CALL_SEND))
            conn.send(CONTROL_WAKEUP_CALL_SEND)
            packet = ""
            packetBuff = ""
        #Check the packet size to see if it is greater than packet size error defined in constants
        if len(packet) > PACKET_SIZE_ERROR:
            logger.warning("THREAD-%s: packet is oddly large while waiting for control string" % str(threadNum))
            conn.send(CONTROL_CLOSE)
            return dataResends

        #Check header receive control string
        if packet.startswith(CONTROL_HSK_RECEIVE):
            #take in what has been recieved and remove the controll string
            dataFiles += 1
            header += packet[len(CONTROL_HSK_RECEIVE):]
            #recieve loop
            #THREAD BUG HERE?!?!?!?!?!?!
            while 1:
                #check for controll close
                if CONTROL_CLOSE in header:
                    logger.info("THREAD-%s: Recived close command, now closing the connection" % str(threadNum))
                    return dataResends
                #total connection timeout
                if time.time() > timeout:
                    logger.info("THREAD-%s: Connection has been established longer than %s seconds, closing connection"
                                % (str(threadNum), str(CONNECTION_TIMEOUT)))
                    return dataResends


                #Check to see if controll wakeup, if so restart
                if header.endswith(CONTROL_WAKEUP_CALL_RECEIVE):
                    logger.info("Received the wakeup call again, resending the response %s" % CONTROL_WAKEUP_CALL_SEND)
                    conn.send(CONTROL_WAKEUP_CALL_SEND)
                    header = ""
                    packet = ""
                    packetBuff = ""
                    break
                #Checks the end from the headers
                if header.endswith("}") or header.endswith("}\0"):
                    #try to split the header and make sure all the fields are there for software 2.1.X
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
                        fileSize = hskSplit[-3]
                        TotalChunks =hskSplit[-2]
                        memoryAddr = hskSplit[18]

                        packet = ""
                        conn.send(CONTROL_DATA_REQUEST)
                        IncomingData = True
                        logger.info("THREAD-%s: received header %s" % (str(threadNum), header))

                            #Checks to see if the IP is known
                        recvData = True

                        if siteUID in IP_dict.keys():
                            knownIP = IP_dict.get(siteUID)
                            currentIP = "%s:%s" % (addr[0], addr[1])
                            #If this is a new IP, re-write Ip_Dickt.pkl to be read by the file manager
                            if knownIP != currentIP:
                                IP_dict[siteUID] = currentIP
                                if not os.path.isdir(os.path.join(ROOT_FILE_PATH, "Dictionary")):
                                    os.makedirs(os.path.join(ROOT_FILE_PATH, "Dictionary"))
                                if not os.path.isfile(os.path.join(ROOT_FILE_PATH, "Dictionary", "Ip_Dict.pkl")):
                                    try:
                                        f = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "Ip_Dict.pkl"), 'w+')
                                        pickle.dump(IP_dict, f)
                                        f.close()
                                    except IOError, e:
                                        logger.warning("THREAD-%s: Unable to create dictionary file, error: %s" %
                                                       (str(threadNum), str(e)))
                                try:
                                    f = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "Ip_Dict.pkl"), 'w')
                                    pickle.dump(IP_dict, f)
                                    f.close()
                                except IOError, e:
                                    logger.warning("Unable to open dictionary file, error: %s" % str(e))
                        else:
                            IP_dict[siteUID] = "%s:%s" % (addr[0], addr[1])
                    except IndexError:
                        #HANDLE THE SENDING OF THE NOK RESPONSE
                        logger.warning("THREAD-%s: Could not split header file, atempting resend" % str(threadNum))
                        if dataResends > DATA_RESEND_CUTOFF:
                            logger.warning("THREAD-%s: Tried to resend data %s times, aborting connection" %
                                           (str(threadNum), str(dataResends)))
                            conn.send(CONTROL_DATA_RESPONSE_NOK)
                            dataResends += 1
                            header = ""
                            return dataResends
                        else:
                            logger.warning("THREAD-%s Making another attempt at the header")
                            conn.send(CONTROL_DATA_RESPONSE_NOK)
                            header = ""
                            packet = ""
                            packetBuff = ""
                    if recvData:
                        break
                #recieve more characters
                chars = conn.recv(BUFFER_SIZE)
                header += chars
                packetNo += 1
                #Check blank packet
                if chars == "":
                    logger.warning("THREAD-%s: Connection unexpectedly closed" % str(threadNum))
                    return dataResends

        #Once the header is found, it will come down to this loop here
        if IncomingData:
            #Recieve loop
            while 1:
                char = conn.recv(BUFFER_SIZE)
                packetNo += 1
                data += char

                #Check for control close
                if CONTROL_CLOSE in header:
                    logger.info("THREAD-%s: Received close control message, now closing the connection" %
                                str(threadNum))
                    writeDataToFile(data, header, threadNum)
                    return dataResends
                #Total connection timeout
                if time.time() > timeout:
                    logger.info("THREAD-%s: Connection has been established longer than %s, closing connection" %
                                (str(threadNum), str(CONNECTION_TIMEOUT)))
                    return dataResends

                #Check data stop key
                if DATA_STOP_KEY in data or "Data_Stop\0" in data:
                    #conn.send(CONTROL_DATA_RESPONSE_OK)
                    if data.endswith(DATA_STOP_KEY) or data.endswith("Data_stop\0"):
                        logger.info("THREAD-%s: Finished data file %s/%s" % (str(threadNum), str(int(chunkNumber)+1),
                                                                         str(TotalChunks)))
                    else:
                        for l in range(len(data)-1, 0, -1):
                            if data[l] == "[":
                                command = data[l:]
                                data = data[:l]
                                packet += command
                    IncomingData = False
                    break
                #Check for blank packet
                if char == "":
                    logger.warning("THREAD-%s: Connection unexpectedly closed" % str(threadNum))
                    writeDataToFile(data, header, threadNum)
                    return dataResends

                #Check to see for wakup command
                if CONTROL_WAKEUP_CALL_RECEIVE in data:
                    logger.warning("THREAD-%s: Received the wake up call again, attempting the connection again" %
                                   str(threadNum))
                    conn.send(CONTROL_WAKEUP_CALL_SEND)
                    data = ""
                    header = ""
                    IncomingData = False
                    packet = ""
                    break
                #Check to make sure the packet is not redonculusly large REMOVE THIS
                if len(data) > PACKET_SIZE_ERROR:
                    logger.warning("THREAD-%s: Unexpectedly large file size in atempting to collect the header" %
                                   str(threadNum))
                    recordChunkFailure(header, chunkNumber)
                    return dataResends

            #Once the stop key is found, double check to see if the file size is the same as stated in the header
            #Otherwise request a resend
            if (len(data) - len(DATA_STOP_KEY)) != int(fileSize) and data.index(DATA_STOP_KEY) != int(fileSize):
                logger.warning("THREAD-%s: file does not contain the right data size, recieved %s, "
                               "and expected %s" %
                               (str(threadNum), str(len(data) - len(DATA_STOP_KEY)), str(fileSize)))
                #If file has been resent more than DATA_RESEND_CUTOFF then just abort the connection
                if dataResends > DATA_RESEND_CUTOFF:
                            logger.warning("THREAD-%s: Tried to resend data %s times, aborting connection" %
                                           (str(threadNum), str(dataResends)))
                            conn.send(CONTROL_CLOSE)
                            writeDataToFile(data, header, threadNum)
                            return dataResends
                conn.send(CONTROL_DATA_RESPONSE_NOK)
                IncomingData = False
                dataResends += 1
                header = ""
                packet = ""
                data = ""
            else:
                logger.debug("Thread-%s: Sending response %s" % (str(threadNum), CONTROL_DATA_RESPONSE_OK))
                conn.send(CONTROL_DATA_RESPONSE_OK)
                logger.debug("THREAD-%s: writing data to file" % str(threadNum))
                writeDataToFile(data, header, threadNum)
                logger.debug("THREAD-%s: Wrote data to file" % str(threadNum))
                header = ""
                packet = ""
                packetBuff = ""
                data = ""
                IncomingData = False
        #Check controll close
        if packet.startswith(CONTROL_CLOSE):
            header = ""
            packet = ""
            packetBuff = ""
            data = ""
            logger.info("THREAD-%s: Successfully received %s/%s data files" % (str(threadNum), str(dataFiles + 1),
                                                                               str(TotalChunks)))
            return dataResends


#################################
# Process the connection
#################################
def processConnection(threadNum, conn, addr, socket):
    """
    Handles the initial connection. Once the awake command has been recieved, the connection is passed on to
    dataConection. Upon returning, the connection is then closed.
    The number of resends is written to file with a timestamps for use in the ingestion scripts
    :param threadNum: Thread number, use for logging
    :param conn: the connection to the TCP client
    :param addr: IP address of the client
    :param socket: The socket in use
    :return:
    """
    # init
    global logger
    global threadCount
    global fileChunksReceived
    global packet
    #packet = ""
    logger.info("THREAD-%02d: New connection from: %s:%d" % (threadNum, addr[0], addr[1]))
    socket.settimeout(SOCKET_TIMEOUT_ON_CONNECTION)
    dataResends = 0
    
    try:
        data = ""
        hsk = ""
        packetCount = 0
        dataPacketInfo = []
        writeFileFlag = True
        wakeupWait = False
        dataReceivedFlag = False
        
        # while there is data coming in
        timeout = time.time() + CONNECTION_TIMEOUT

        while 1:
            chars = conn.recv(BUFFER_SIZE)
            packetCount += 1
            #logger.info("THREAD-%s: Received packet of size %d" % (str(threadNum), len(chars)))
            packet += chars

            if time.time() > timeout:
                logger.warning("THREAD-%s: Thread has been active for longer than %s seconds, closing connection" %
                               str(threadNum), str(CONNECTION_TIMEOUT))
                break

            if CONTROL_CLOSE in packet:
                logger.info("THREAD-%s: Received control close command, now closing connection" % str(threadNum))
                break

            if chars == "":
                logger.warning("THREAD-%s: Blank packet received, closing connection" % str(threadNum))
                break

            if packet.endswith(CONTROL_WAKEUP_CALL_RECEIVE):
                socket.settimeout(SOCKET_TIMEOUT_ON_CONNECTION)
                conn.send(CONTROL_WAKEUP_CALL_SEND)
                logger.info("THREAD-%s: Received wakeup call: '%s' and sending response, starting data connection '%s'"
                            % (str(threadNum), packet, CONTROL_WAKEUP_CALL_SEND))
                dataResends += dataConnection(threadNum, conn, addr, socket, packetCount)
                socket.settimeout(None)
                break
            if len(packet) > PACKET_SIZE_ERROR:
                logger.warning("THREAD-%s: Packet length is oddly large, closing connection"
                               % str(threadNum))
                break


        # close connection


        packet = ""
        socket.settimeout(None)

    except SocketError, e:
        logger.error("THREAD-%s: Socket error here2: %s" % (str(threadNum), str(e)))

        threadCount -= 1

        if dataResends > 0:
            try:
                if not os.path.isdir(os.path.join(ROOT_FILE_PATH, "Dictionary")):
                    os.makedirs(os.path.join(ROOT_FILE_PATH, "Dictionary"))
                f = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "DataResends.txt"), 'w+')
                f.write("%s,%s" % (str(time.time()), str(dataResends)))
            except IOError, e:
                logger.warning("THREAD-%s: Unable to write to data resend, error: %s", (str(threadNum), str(e)))

        try:
            logger.info("THREAD-%s: Safely closing connection2" % str(threadNum))
            conn.close()
            socket.settimeout(SOCKET_TIMEOUT_NORMAL)
            logger.info("THREAD-%s: Safely closed connection2" % str(threadNum))
        except Exception, e:
            logger.error("THREAD-%s: Error closing connection after socket error3" % str(threadNum))

        return
        
    #return

    if dataResends > 0:
        try:
            f = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "DataResends.txt"), 'w+')
            f.write("%s,%s" % (str(time.time()), str(dataResends)))
            f.close()
        except IOError, e:
            logger.warning("THREAD-%s: Unable to write to data resend, error: %s", (str(threadNum), str(e)))

    threadCount -= 1
    logger.info("THREAD-%s: Safely closing connection1" % str(threadNum))
    socket.settimeout(None)
    conn.close()

    #Check to limit the number of threads active.
    if threadNum > 15:
        time.sleep(120)
        os.system("./usr/local/src/above/tcp_server/tcp_server_26000.py restart")
        #TCP_server.restart()

    return


#################################
# MAIN METHOD
#################################
def main():
    """
    Main function. Handles the binding of the socket, and threads any connection received
    :return:
    """
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

    while 1:
        try:
            # accept connections
            conn, addr = s.accept()
            threadCount += 1
            activeThreads = threading.activeCount()
            logger.info("Found %s active threads" % str(activeThreads))
            newThread = Thread(target=processConnection,  args=(activeThreads, conn, addr, s))
            newThread.start()

        except SocketError, e:
            logger.debug("++++++++++++++")
            logger.error("Socket error or maybe here: " + str(e))
            print "Current timeout set to ", s.gettimeout()
            try:
                s.settimeout(SOCKET_TIMEOUT_NORMAL)
                conn.close()
                logger.info("Safely closed connection")
            except Exception, e:
                logger.error("Error closing connection after socket error %s" % str(e))
            logger.debug("++++++++++++++")
        except KeyboardInterrupt:
            logger.error("Keyboard interrupt encountered, quitting ... ")
            exit(0)

            

# main entry point
if __name__ == "__main__":
    #global TCP_server
    if not os.path.isdir(PID_PATH):
        os.makedirs(PID_PATH)
    pidFile = os.path.join(PID_PATH, PID_FILE)
    TCP_server = MyDaemon(pidFile)

    if len(sys.argv) == 2:
        if sys.argv[1] == 'start':
            print "**********************************************************************"
            print "       Starting the tcp server port %s script" % str(TCP_PORT)
            print " Please refer the log file %s/%s/%s" % (ROOT_FILE_PATH, LOG_PATH, LOG_FILENAME)
            print "**********************************************************************"
            TCP_server.start()
            #except:
            #    pass
        elif sys.argv[1] == 'stop':
            print "**********************************************************************"
            print "                 stopping the tcp server"
            print "**********************************************************************"
            TCP_server.stop()

        elif sys.argv[1] == 'restart':
            print "**********************************************************************"
            print "                 Restarting the tcp server"
            print "**********************************************************************"
            TCP_server.restart()

        elif sys.argv[1] == 'main':
            main()

        else:
            sys.exit(2)
            sys.exit(0)

    else:
        print "Please use ./tcp_server_%s.py start to start the script. See documentation for more detail" % str(TCP_PORT)
