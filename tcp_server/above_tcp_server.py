#! /usr/bin/env python
"""
ABOVE TCP SERVER
VERSION: 3.0.0 (IN DEVELOPMENT)

Author: Casey Daniel
Date:   May 2015

Description:
    This is the TCP Sever for the ABOVE VLF project. Version 3 is to replace previous
    version of the server, and allow for the accomodation of multiple files.
    This will esseintially be a re-write of the entire server.

    THIS SERVER IS STILL IN DEVELOPMENT

Changelog:
    3.0.0:
        -N/A
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
from time import sleep

#Constants
BufferSize = 1024
DataStopKey = "Data_Stop"
MaxResends = 3
yearPrefix = "20"
#TCPPort = 26020
#TCPIP = "136.159.51.194" #SSSSSSOOOOOOOMMMMMMMMEEEEEEEETTTTTTTTTHHHHHHHIIIIIIIINNNNNNNNGGGGGG
TCPIP = "136.159.51.194"
TCPPort = 26000
connectionTimeout = 60
connectionBacklog = 5
normalTimeout = None
connectionTimeout = 120
maxResends = 3

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
dataStop        = "Data_Stop"

#Directories
#rootDir = "/data/vlf"
rootDir = "/Users/Casey/AboveServerTest"
timeSerriesDir  = os.path.join(rootDir, "incoming_files", "time_serries")
houseFilesDir   = os.path.join(rootDir, "incoming_files", "house_keeping")
narrowBandDir   = os.path.join(rootDir, "incoming_files", "narrow_band")
spectralDir     = os.path.join(rootDir, "incoming_files", "spectral")
lostAndFound    = os.path.join(rootDir, "incoming_files", "lost_and_found")
PIDPath         = os.path.join(rootDir, "src", "PID")

#Logging Settings
logPath = os.path.join(rootDir, "logs")
logFileName = "above_tcp_sever_%s.log" % TCPPort
logName = "Above TCP Sever Logger"
logLevel = logging.DEBUG
maxLogSize = 1024000 * 100 #100MB
maxLogFiles = 5 #Maximum number of log files to be saved

class StreamToLogger(object):
    """
        Python class to help stream standard out and standard error to the log file
        in case of crashes
    """
    def __init__(self, logger, log_level=logging.INFO):
      self.logger = logger
      self.log_level = log_level
      self.linebuf = ''

    def write(self, buf):
      for line in buf.rstrip().splitlines():
         self.logger.log(self.log_level, line.rstrip())

class MyDaemon(Daemon):
    """
        Override the run method in the MyDaemon class, used to make the 
        process a Daemon.
    """
    def run(self):
        main()

def initLogging():
    """
    initLogging
        Intialize the logger file
    """
    global logger
    #Create logger
    logger = logging.getLogger(logName)
    logger.setLevel(logLevel)
    
    #Logging file name and path
    if not os.path.exists(logPath):
        os.makedirs(logPath)
    fullLogFile = os.path.join(logPath, logFileName)
    
    #Start the logger with a formated strting message, as well ensure that file 
    #size does not exceed maxLogSize and that there only the last maxLogFiles are saved
    handler = logging.handlers.RotatingFileHandler(fullLogFile, maxBytes = maxLogSize, backupCount = maxLogFiles)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S UTC")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #Intial Message
    logger.info("----------------Above VLF TCP Server -------------------")
    logger.info("Now Starting Sever on port %s" % str(TCPPort))

    #Standart out and error re-directs
    outStream = StreamToLogger(logger, logging.INFO)
    sys.stdout = outStream
    
    errorStream = StreamToLogger(logger, logging.ERROR)
    sys.stderr = errorStream


def writeData(splitHeader, data, threadNo):
    global logger
    
    fileDir = ""
    #Determine the file path
    if splitHeader[8] == "hsk":
        fileDir = houseFilesDir
    elif splitHeader[8] == "time":
        fileDir = timeSerriesDir
    elif splitHeader[8] == "nrbd":
        fileDir = narrowBandDir
    elif splitHeader[8] == "spec":
        fileDir = spectralDir
    else:
        fileDir = lostAndFound

    if not os.path.isdir(fileDir):
        logger.debug("Thread-%s: path %s did not exists, now creating" % (str(threadNo), fileDir))
        os.makedirs(fileDir)

    #make file name
    day           = splitHeader[0][:2]
    month         = splitHeader[0][2:4]
    year          = yearPrefix + splitHeader[0][4:]
    hour          = splitHeader[1][:2]
    minute        = splitHeader[1][2:4]
    second        = splitHeader[1][4:6]
    siteUID       = splitHeader[5]
    deviceUID     = splitHeader[6]
    chunkNo       = splitHeader[2]
    fileExtension = splitHeader[8]

    fileName = "%s%s%s_%s%s%s_%s_%s.chunk%s.%s" % (day, month, year, hour, minute, second, siteUID, deviceUID, chunkNo, fileExtension)
    fullFilePath = os.path.join(fileDir, fileName)
    logger.info("Thread-%s: Now writing %s" % (str(threadNo), fullFilePath))
    #Write to file
    try:
        with open(fullFilePath, 'w+') as dataFile:
            dataFile.write(data)
    except IOException, e:
        logger.info("Thread-%s: Unable to write file %s. Error %s" % (str(threadNo), fullFilePath, str(e)))

    logger.info("Thread-%s: Done writing file" % str(threadNo))
    
def recvData(conn, s, threadNo, headerSplit, resend):
    """
    recvData
        Function responsbile for the data connection

        The same status return code are used here as well
        1 indicates the connection is fine
        2 indicates a problem with the connection, and needs to be closed.
    """
    data = ""
    chars = " "
    global logger
    while 1:
        
        if chars == "":
            logger.warning("Thread-%s: Recived blank packet while collecting data, aborting connection" % str(threadNo))
            return 2, resend
        
        elif ConnectionEnd in data:
            logger.warning("Thread-%s: Found connection end while collecting data, aborting connection" % str(threadNo))
            return 2, resend
        elif dataStop in data:
            logger.info("Thread-%s: Data stop key has been recieved, now checking data" % str(threadNo))
            if (len(data) - len(dataStop)) != int(headerSplit[7]) and (len(data) != int(headerSplit[7])):
                if resend <= 3:
                    logger.warning("Thread-%s: Data length does not match the expected length. Recived %d, expected %s, will retry connection" 
                                    % (str(threadNo), len(data) - len(dataStop), headerSplit[7]))
                    conn.send(dataNOK)
                    data = ""
                    resend += 1
                    continue
                else:
                    logger.warning("Thread-%s: Data length does not match, expected %d, connection has exceeded maximum retries, now aborting conneciton"
                                    % (str(threadNo), len(data) - len(dataStop), headerSplit[7]))
                    return 2, resend
            elif (len(data) - len(dataStop)) == int(headerSplit[7]) or (len(data) == int(headerSplit[7])):
                logger.info("Thread-%s: Recived the correct amount of data, now moving forward with writing the file." % str(threadNo))
                conn.send(DataOK)
                writeData(headerSplit, data, threadNo)
                logger.info("Thread-%s: Done file %d/%d" % (str(threadNo), headerSplit[2]+1,headerSplit[3]))
                return 1, resend
        chars = conn.recv(BufferSize)
        data += chars



def recvHeader(conn, s, threadNo, header, resend):
    """
    recvHeader
        This function handles the next step of receiving the header

        returns a status integer, as well as the number of resends tried on this
        connection

        Status code of 1 means that the connection is still being processed as normal
        status code of 2 indicates that an error has happend and the connection needs to be closed
    """
    global logger
    chars = " "
    while 1:

        if chars == "":
            logger.warning("Thread-%s: Recived blank packet while collecting the header, aborting connection" % str(threadNo))
            return 2
        elif ConnectionEnd in header:
            logger.warning("Thread-%s: Recived connection end while collecting the header, aborting connection" % str(threadNo))
            return 2
        elif header.endswith("}"):
            logger.info("Thread-%s: Collected the header: %s" % (str(threadNo), header))
            headerSplit = header[header.index("{")+1:-1]
            headerSplit = headerSplit.split(",")
            if len(headerSplit) != 9 and resend <= maxResends:
                logger.warning("Thread-%s: Header was not of correct length, have tried %d connections, will try again" % (str(threadNo), resend))
                logger.warning("Thread-%s: Header was of length %d, expected 9" % (str(threadNo), len(headerSplit)))
                resend += 1
                conn.send(HeaderNOK)
                header = ""
                continue
            elif len(headerSplit) != 9 and resend > maxResends:
                logger.warning("Thread-%s: Incorect header length, maximum retries have been reached, will now abort the connection" % str(threadNo))
                return 2
            
            logger.info("Thread-%s: Recived a valid header, now starting to process the data" % str(threadNo))
            conn.send(HeaderOK)
            status, resends = recvData(conn, s, threadNo, headerSplit, resend)

            if status == 2:
                logger.debug("Thread-%s: Detected an error, continuing with connection abort" % str(threadNo))
                return 2, resend
            if status == 1:
                logger.info("Thread-%s: Data recieved sucessfully" % str(threadNo))
                return 1, resend

        chars = conn.recv(BufferSize)
        header += chars
                



def dataConnection(conn, s, threadNo, resend):
    """
    dataConnection
        Manages the data connection
        Returns an integer indicating the status.

        If 1 is returned, then the data connection was fine, and can now
        move on to other commands or be close

        If 2 then an error was found higher up, and needs to be quit.
    """
    global logger
    message = ""
    logger.debug("Thread-%s: Starting data connection" % str(threadNo))
    while 1:
        chars = conn.recv(BufferSize)
        message += chars
        logger.info("Thread-%s: Recieved %s" % (str(threadNo), message))

        if chars == "":
            logger.warning("Thread-%s: Recieved blank packet, expected a header, now closing the connection" % str(threadNo))
            return 2, resend
        elif ConnectionEnd in message:
            logger.warning("Thread-%s: Recieved end connection command, expected a header, now closing the connection" % str(threadNo))
            return 2, resend
        elif HeaderSend in message:
            logger.info("Thread-%s: Now collecting the header" % str(threadNo))
            index = message.index("]")
            headerContents = message[index+1:] # TODO: confirm this is a thing that actually does properly
            satus = recvHeader(conn, s, threadNo, headerContents, resend)
            #Check the status code
            if satus == 2:
                logger.info("Thread-%s: An error in the header/data connection" % str(threadNo))
                return 2, resend
            else:
                message = ""
                continue
            
        elif DataEnd in message:
            logger.info("Thread-%s: No more data to collect" % str(threadNo))
            return 1, resend

def recv(conn, s, threadNo):
    """
    recv
        Main loop for the connection. Once the connection is started, this 
        loop handles the server commands
    """
    global logger
    logger.info("Thread-%s: Starting new connection" % (str(threadNo)))

    #s.settimeout(connectionTimeout)
    resend = 0
    
    message = ""
    while 1:
        #read a message
        chars = conn.recv(BufferSize)
        message += chars
        logger.info("Thread-%s: Recieved: %s" % (str(threadNo), chars))

        #Check the message for things
        #blanket packet, connection closed
        if chars == "":
            logger.warning("Thread-%s: Received blank packet, expected wakeup call, aborting connection" % str(threadNo))
            break

        elif message.endswith(Wakeup):
            logger.info("Thread-%s: Received wakeup call" % str(threadNo))
            """
            This would be the place to add a decision on what to command
            flow to go to. Right now the only one is the data connection.
            When the move to more place the logic in here, either before
            the data connection or after the status check.
            """
            logger.info("Thread-%s: Starting Data connection" % str(threadNo))
            #Start Data Connection
            conn.send(DataRequest)
            logger.debug("Thread-%s: Sent %s" % (str(threadNo), DataRequest))
            status, resend = dataConnection(conn, s, threadNo, resend)
            if status == 1:
                logger.info("Thread-%s: No Additional commands, now closing" % str(threadNo))
                conn.send(ConnectionEnd)
                break
            else:
                logger.info("Thread-%s: Data Reciving has failed, now closing connection" % str(threadNo))
                break
        elif ConnectionEnd in message:
            logger.warning("Thread-%s: Received end transmision command, expected wakeup call. Now aborting connection" % str(threadNo))
            break

    #Close the connection
    try:
        logger.info("Thread-%s: Now safely closing the connection" % str(threadNo))
        conn.send(ConnectionEnd)
        conn.close()
        #s.settimeout(normalTimeout)
    except SocketError, e:
        logger.error("Thread-%s: Unable to safely close connection. Socket error %s" % (str(threadNo), str(e)))
        try:
            conn.close()
        except:
            logger.error("Thread-%s: Unable to safely close connection." % str(threadNo))


def main():
    global logger
    global threadCount

    #start the logger
    initLogging()

    packet = ""
    
    #Intilaize the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    s.settimeout(connectionTimeout)
    s.setblocking(0)

    #Attempt to bind the socket
    try:
        s.bind((TCPIP,TCPPort))
        logger.debug("Port %d is now bound" % TCPPort)
    except SocketError, e:
        logger.warning("Unable to start the server. %s " % str(e))
        return

    #more of setting the socket up
    s.listen(connectionBacklog)
    logger.info("Listening on port %d (%d connection backlog)" % (TCPPort, connectionBacklog))
    logger.info("-----------------------------------------------------")

    #infinte loop for the server
    while 1:
        #Establish connections and spawn new threads for each new connection
        try:
            conn, addr = s.accept()
            activeThreads = threading.activeCount()
            logger.info("Found %d active threads" % activeThreads)
            newThread = Thread(target = recv, args=(conn, s, activeThreads)) 
            newThread.start()

        except SocketError, e: 
            logger.error("Socket error: %s" % str(e))
            try:
                s.settimeout(normalTimeout)
                conn.close()
            except Exception , e:
                logger.error("Unable to close socket after error: %s" % str(e))

        except KeyboardInterrupt:
            logger.error("Keyboard interupt")
            exit(0)


##################
#Main Entry Point#
##################
if __name__ == "__main__":
    
    #Check PID Path
    if not os.path.isdir(PIDPath):
        os.makedirs(PIDPath)

    pidFile = os.path.join(PIDPath, "tcp_serever_pid_" + str(TCPPort) + ".pid")

    TCPServer = MyDaemon(pidFile)

    if len(sys.argv) == 2:
        command = sys.argv[1]

        if command == "start":
            print("****************************************************")
            print("    Starting tcp server on port %s" % str(TCPPort))
            print("****************************************************")
            TCPServer.start()

        elif command == "stop":
            print("****************************************************")
            print("       Stopping the tcp server......")
            print("****************************************************")
            TCPServer.stop()

        elif command == "restart":
            print("****************************************************")
            print("      Restarting the tcp server")
            print("****************************************************")
            TCPServer.restart()
        elif command == "main":
            print("Starting Main")
            main()
        else:
            print("Invalid Command, please refer to the documentation")
    else:
        print("Please use ./above_tcp_sever_%s.py start to start the script" % str(TCPPort))
        print("Please see the documentaiton for more details")
