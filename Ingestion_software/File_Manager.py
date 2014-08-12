#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 File Manager Script
 Version: 1.0.6

 Created by: Casey Daniel
 Date: 13/05/2014

 Description:
  This script will run periodically on the same machine as the tcp server to combine the file chunks, send health
  keeping data back to RTEMP, as well as generate a summary plot thumbnail to be sent back to RTEMP.
  This task will start according to :param:TIME_DELAY. This is measured in seconds.

  This will be compatible with previous software versions, however is compatible with tcp server version 2.1.x+

  To start simply call ./File_Manager.py start and to stop the script call ./File_Manager.py stop
  If a restart is needed simply call ./File_Manager.py restart

 Changelog:
    0.0.1:
       -N/A

    0.0.2:
       -Chunk files are now moved out of the main directory into a chunk directory

    0.0.3:
       -Combined loggers between the unpacking routine and the rest of the file

    0.1.0:
       -Script now combines into a master data file, in the same binary format at as the chucnk files
       -Tested, candidate to start on server

    0.1.1:
       -Updated checking on header values

    0.2.0:
       -Now handles corrupted, moves them into a separate directory
       -Checks to make sure all present files are there before processing
       -Handles abandoned file chunks
       -NOTE: Requires Software 2.1+ running on the main board

    0.2.1:
      -Added in RTEMP Packets
      -Better Commenting
      -new directories is no longer depends on the old
      -Should now be backwards compatible

    0.2.2:
      -Now checks for dictionary file from server to send IP address to RTEMP
      -Looks for DataResends to check the number of data resend requests in the last seconds, parameter RESEND_TIME

    0.2.3:
      -Added in an extra entry into the RTEMP package

    0.3.0:
      -Bug Fixes
      -Better documentation

    0.4.0:
      -New Functions to only handle in binary data rather than unpacking

    0.5.0:
      -Finally working with the Daemon Process

    1.0.0:
      -Bug Fixes
      -Stable release

    1.0.1:
      -Updated header version

    1.0.2:
      -Search list is now sorted

    1.0.3:
      -Standard error and standard out are now re-directed to the log file

    1.0.4:
        -Temporary fix for the camrose time stamp bug
        -Minor change to RTEMP packets.

    1.0.5:
        -Removed batt_temp from RTEMP packets
        -converted the voltages and temp to real units

    1.0.6:
        -Added a double check to make sure all chunk files are indeed moved.


 Bug tracker:
   -Find away to look for files that are more than just the _00 chunk

 TODO:
   -Look into putting a command to start services at boot

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
__name__ = '__main__'

import threading
import logging
import logging.handlers
import os
import glob
import struct
import shutil
from datetime import datetime
import sys
import socket
import time as Time
import pickle
from Daemon import Daemon

#################
#  Constants
#################
#Time Delay between clean-ups
TIME_DELAY = 60.0 * 5  # 5 min since that's how long between packets being sent

#File Paths
#RAW_FILE_PATH = "/data/vlf/testServer/testRawData"                  # Server test path
RAW_FILE_PATH = "/data/vlf/RawData"                       # Sever Root Path

CHUNK_DATA_PATH = "/data/vlf/chunks"                               # server path
#CHUNK_DATA_PATH = "/data/vlf/testServer/Chunks"                     # Server test path

FULL_DATA_PATH = "/data/vlf/full_files"                            # server path
#FULL_DATA_PATH = "/data/vlf/testServer/FullFiles"                   # Server test path

ERROR_PATH = "/data/vlf//malformeFiles"                            # Server Path
#ERROR_PATH = "/data/vlf/testServer/BadFiles"                        # Server test path

#ROOT_FILE_PATH = "/data/vlf/testServer"
ROOT_FILE_PATH = "/data/vlf"

# logging strings
#LOG_PATH = "/data/vlf/testServer/logs"  # Server test path
LOG_PATH = "/data/vlf/logs"  # Server Path

LOGFILE_MAX_BYTES = 1024000 * 100   # 100MB
LOGFILE_BACKUP_COUNT = 5
LOG_FILENAME = "Above_File_Manager.log"
logger = None

#Time from file writen to be found corrupted if the full set is not available
CuruptedTime = 3600  # seconds

#RTEMP UDP Info
RTEMP_IP = "136.159.51.160"
RTEMP_PORT = 25000
MAX_PACKET_SIZE = 1024  # 1Kb
LAST_PACKET_TIMESTAMP = None
time_between_packets = 15

#Key Strings
START_KEY = "Data_Start"

#miscilanious
IP_Dict = {}  # IP Dictionary, barr entry put in for testing purposes
RESEND_TIME = 300  # Seconds for the number of resends to be noted
PID_PATH = '/usr/local/src/above/PID'
PID_FILE = 'FileManager.pid'


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


def loggerInit():
    """
    loggerInit simply initializes the logger file that the log statements can be found in
    :return: None
    """
    global logger

    # initialize the logger
    logger = logging.getLogger("ABOVE VLF Acquisition Logger")
    logger.setLevel(logging.DEBUG)

    #create the path if it does not exist
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)

    LOG_FILE = os.path.join(LOG_PATH, LOG_FILENAME)
    #Handler to make sure files don't get to big, and will spin off new files
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=LOGFILE_MAX_BYTES, backupCount=LOGFILE_BACKUP_COUNT)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S UTC")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #Standard out re-direct
    outStream = StreamToLogger(logger, logging.INFO)
    sys.stdout = outStream

    #Standard error re-direct
    errorStream = StreamToLogger(logger, logging.ERROR)
    sys.stderr = errorStream

    # write initial messages
    logger.info("+++++++ ABOVE VLF File Manager Log +++++++")
    logger.info("Starting File Manager......")


def getHeader(path, fileName):
    """
    getHeader is a replacement for the unpackFile method. unpackFile reads in the binary data and translates them to
    two lists of integers. For the needs of this script, this seems unnecessary.
    This script simply reads in the header, followed by the data. A check for the end key is made, and the start key
    if the software version is previous to 2.1.
    :param path: specified file path as a string
    :param fileName: specified file name as a string
    :return: (binary data as a string, header as a list.)
    """
    global logger

    if not os.path.isfile(os.path.join(path, fileName)):
        logger.warning("Unable to find file %s/%s" % (path, fileName))
        return None, None

    hsk = ""

    #Open the file
    with open(os.path.join(path, fileName), 'rb') as contents:
        #Read characters until } is found, the end of the header
        while 1:
            try:
                char = contents.read(1)
            except IOError, e:
                logger.warning("Unable to read character, error: %s" % str(e))
                return None, None
            hsk += char
            if char == "}":
                break

        #split the header and remove the brackets
        hskSplit = hsk[1:-1].split(",")

        #For software version previous to 2.1, the start key needs to be read
        try:
            softwareVersion = float(hskSplit[4])
        except ValueError:
            logger.info("Unable to get the software version")
            return None, None
        if softwareVersion < 2.1:
            try:
                startKey = contents.read(len("Data_Start"))
            except IOError, e:
                logger.warning("Unable to read file %s, error:" % (fileName, str(e)))
                return None, None
            if startKey == "Data_Start":
                logger.info("Found the start key of file %s" % fileName)
            else:
                logger.warning("Unable to find the start key")
                return None, None

        #Read the reamining informaiton in the file
        try:
            remaingData = contents.read()
        except IOError, e:
            logger.warning("Unable to read data, error %s" % str(e))

        #find the end key in the file, everything else is the binary data
        if remaingData.endswith("Data_Stop\0"):
            data = remaingData[:-10]
            return hskSplit, data
        elif remaingData.endswith("Data_Stop"):
            data = remaingData[:-9]
            return hskSplit, data
        elif remaingData.endswith("Data_Stop "):
            data = remaingData[:-10]
            return hskSplit, data
        else:
            logger.warning("Unable to find the stop key")
            return None, None


def fileCombinationBinary(data, header, filePath, fileName):
    """
    fileCombinationBinary is a function that will write the binary data to the specified file.

    The difference between fileCombinationBinary and fileCombination is that this function takes in the binary data
    instead of each channel as a list of integers. This is to be used with the getHeader method instead of the
    unpackFile method.

    :param data: String of the binary data
    :param header: Header contents as a list
    :param fileName: specified file name as a string
    :param filePath: specified file path as a string
    :return: None
    """
    global logger

    logger.info("Combinind data files")

    softwearVersion = float(header[4])

    fileHeader = ""

    newHeader = [None] * 19


    newHeader[0] = header[0]
    newHeader[1] = header[1]
    newHeader[2] = "0"
    newHeader[3] = header[3]
    newHeader[4] = "2.1"
    newHeader[5] = header[5]
    newHeader[6] = header[6]
    newHeader[7] = header[7]
    newHeader[8] = header[8]
    newHeader[9] = header[9]
    newHeader[10] = header[10]
    newHeader[11] = header[11]
    newHeader[12] = header[12]
    newHeader[13] = header[13]
    newHeader[14] = header[14]
    newHeader[15] = header[15]
    newHeader[16] = str(len(data))
    newHeader[17] = "1"
    newHeader[18] = header[18]

    headerString = ",".join(str(x) for x in newHeader)

    #make the string to be written to file
    fileData = "{%s}%sData_Stop" % (headerString, data)

    #check the file path
    if not os.path.isdir(filePath):
        os.makedirs(filePath)
        logger.debug("Making the data file path %s" % filePath)

    #open and write the data file
    logger.debug("Writing data file")
    with open(os.path.join(filePath, fileName), "w") as dataFile:
        try:
            dataFile.write(fileData)
        except IOError, e:
            logger.warning("Unable to write file %s, error %s" % (fileName, str(e)))

    logger.debug("Done writing file %s/%s" % (filePath, fileName))


def sendToRTEMP(Header, malformed_packets):
    """
    Responisble for sending health keeping information to the RTEMP server at the University of Calgary
    :param Header: Header contents, as a list
    :return: None
    """
    global logger
    global LAST_PACKET_TIMESTAMP
    global IP_Dict

    #extracts information
    #This form is valid for header version 2.1 and rev a or b
    if Header[5][-1] == 'a' or Header[5][-1] == 'b':
        version = "2.0"
        project = "above"
        site = Header[6]
        device = Header[8]
        date = Header[0]
        time = Header[1]
        gps_fix = Header[3]
        temp = (((float(Header[12])/256)*5)-0.6)*100
        rssi = Header[14]
        V_batt = (float(Header[11])/256)*20
        V_twelve = (float(Header[10])/256)*30
        V_five = (float(Header[9])/256)*10
        clock_speed = Header[13]
        memory_addr = Header[18]

    formattedTime = "%s:%s:%s" % (str(time[0:2]), str(time[2:4]), str(time[4:6]))
    formattedDate = "20%s-%s-%s" % (str(date[4:6]), str(date[2:4]), str(date[0:2]))

    current_time = datetime.utcnow()
    #We can't send RTEMP packets to quickly, otherwise we can overload the server. Maximum of one very 10 seconds
    if LAST_PACKET_TIMESTAMP is not None:
        timeDiff = current_time - LAST_PACKET_TIMESTAMP
        timeDiff = timeDiff.total_seconds()
        if timeDiff < 10:
            Time.sleep(time_between_packets)
    LAST_PACKET_TIMESTAMP = current_time

    #Loading the latest dictionary from the server, if it is not loadable, then the latest is being written to
    #Else it a dummy variable is sent, this should only happen when testing on another computer, or just starting
    #everything for the first time
    try:
        ips = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "Ip_Dict.pkl"), 'r')
        IP_Dict = pickle.load(ips)
        IP_addr = IP_Dict[Header[6]]
        ips.close()
    except IOError, e:
        logger.debug("Unable to load IP dictionary, error: %s" % str(e))
        if len(IP_Dict) == 0:
            IP_addr = "0.0.0:0"
        else:
            IP_addr = IP_Dict[Header[6]]
    except KeyError:
        IP_addr = "0.0.0:0"

    array = []
    try:
        f = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "DataResends.txt"), 'r')

        contents = f.read()
        contents = contents.split("\n")
        if len(contents) > 0:
            for part in contents:
                part = part.split(",")
                array.append(part)
        else:
            resends = 0
        f.close()
    except IOError, e:
        logger.debug("Unable to open DataResends.txt, error: %s" % str(e))
        resends = 0
    #finds the number of resends in the last 5 min
    try:
        if len(array) > 0:
            resends = 0
            for entry in reversed(array):
                timeStamp = float(entry[0])
                timeDiff = timeStamp - Time.time()
                if timeDiff < RESEND_TIME:
                    resends += int(entry[1])
                else:
                    break
        else:
            resends = 0
    except ValueError:
        resends = 0


    #Clears the data resends file
    try:
        f = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "DataResends.txt"), 'w')
        f.write("")
        f.close()
    except IOError, e:
        logger.debug("Unable to clear dataResends file, error: %s" % str(e))


    #seconds since epoch in UTC, this is to be sent to RTEMP following the monitor key
    seconds_epoch = Time.time()
    #Assembles the basic information required
    #To change the data sent, simply change this string. Key values and data are separated by a single space
    #Make sure you tell Darren as well
    RTEMP_packet = "instrument %s date %s time %s gps_fix %s temp %s V_batt %s V_12 %s V_5 %s rssi %s IP_addr %s " \
                   "memory_addr %s clk_speed %s \nserver %s mal_packets %s no_resends %s " \
                   % (str(seconds_epoch)[:-3],  # Seconds since epoch
                      formattedDate,            # Formatted Date
                      formattedTime,            # Formatted Time
                      gps_fix,                  # GPS Fix
                      temp,                     # Temp of the main board
                      V_batt,                   # Battery Voltage
                      V_twelve,                 # Voltage of the 12 Volt input
                      V_five,                   # Voltage of the 5 volt input
                      rssi,                     # Wifi signal strength
                      str(IP_addr[:-6]),        # IP Address of the instrument minus the port information
                      str(memory_addr),         # SD memory address
                      str(clock_speed),         # Reported clock speed
                      str(seconds_epoch)[:-3],  # Seconds since epoch
                      str(malformed_packets),   # No. of malformed packets in the set
                      str(resends))             # No. of resent packets in the last 5 min


    #Find the size of the information
    packet_size = sys.getsizeof(RTEMP_packet)

    #There is a maximum packet size of ~1400 Bytes that can be in the UDP packet, to ensure that the entire packet
    #Can be transmitted, the maximum packet size is set to 1024 Bytes.
    #If more information is needed, then the packets are queued appropriately
    if packet_size < MAX_PACKET_SIZE:
        RTEMP_header = "monitor %s version %s project %s site %s device %s date %s time %s PACKET_NUMBER %s " \
                       "QUEUE_LENGTH %s\n" % (str(seconds_epoch)[:-3],  # Seconds since epoch in UTC
                                                   version,             # Version number, 2.0
                                                   project,             # Project, above
                                                   site,                # Site UID
                                                   device,              # Device UID
                                                   formattedDate,       # Date of the file
                                                   formattedTime,       # Time of the file
                                                   str(1),              # Packet number 1, since everything fits in one
                                                   str(0))              # Queue length 0,
        RTEMP_message = "%s%s" % (RTEMP_header, RTEMP_packet)
        logger.debug("Sending RTEMP Packet %s" % RTEMP_message)
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            soc.sendto(RTEMP_message, (RTEMP_IP, RTEMP_PORT))
        except socket.error, e:
            logger.warning("Unable to send RTEMP Packet, error: %s" % str(e))

    else:
        numberOfPackets = packet_size%MAX_PACKET_SIZE + 1
        for i in range(0, numberOfPackets):
            RTEMP_header = "monitor %s version %s project %s site %s device %s date %s time %s PACKET_NUMBER %s " \
                       "QUEUE_LENGTH %s\n" % (str(seconds_epoch)[:-3],            # Seconds since epoch
                                                   version,                       # Version, 2.0
                                                   project,                       # project, above
                                                   site,                          # Site UID
                                                   device,                        # Device UID
                                                   date,                          # Date from file
                                                   time,                          # Time from file
                                                   str(i),                        # Packet number
                                                   str(numberOfPackets - i - 1))  # Packets in queue
            RTEMP_message = "%s%s" % (RTEMP_header, RTEMP_packet[i*MAX_PACKET_SIZE:(i+1) * MAX_PACKET_SIZE])
            logger.debug("Sending RTEMP packet %s/%s %" % (str(i), str(numberOfPackets), RTEMP_message))
            try:
                soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                soc.sendto(RTEMP_message, (RTEMP_IP, RTEMP_PORT))
            except socket.error, e:
                logger.warning("Unable to send RTEMP Packet, error: %s" % str(e))
            #Ensures we don't overload the server
            Time.sleep(time_between_packets)

    return


def cleanUp():
    """
    This is the main portion of the script
    First the files are found, starting in the RAW_FILE_PATH, this is a constant at the top of this file
    Once file chunks are found, then we iterate through all of the chunks to combine the data, then the data
    combination is called, and the chunks are moved.
    If something is wrong with the files, then they are moved to a graveyard directory, specified at the top of the file
    The timer function at the bottom of this function ensure a that this script is called periodically
    :return: None
    """
    global logger
    logger.info("Starting clean up")
    for paths, dirs, files in os.walk(RAW_FILE_PATH):
            os.chdir(paths)
            #search for the first chunk of the file
            for f in sorted(glob.glob("*_00.chunk.dat")):
                Headers = []
                f = f.split("_")
                #Get the base file name
                file_name = "%s_%s_%s_%s_" % (f[0], f[1], f[2], f[3])  # THIS IS A TEMPORARY FIX WHILE CAMROSE
                                                                       # HAS A GPS TIME ISSUE
                search_file_name = "%s_%s*" % (f[0], f[1][:-2])
                #search_file = "%s*" % file_name
                search_file = "%s*" % search_file_name
                logger.info("Search file %s" % search_file_name)

                #Gets the directory information
                siteID = ""
                numberOfFiles = len(glob.glob(search_file))
                CuruptedFiles = 0
                hourDir = ""
                totalData = ""
                Data = ""
                #Searches for the files, checks to make sure the _00 is not in the last spot in the list
                #With the GPS bug where the first file has a different second entry then the rest.
                chunks = sorted(glob.glob(search_file), key=str.lower)
                if "_00.chunk" in chunks[-1]:
                    lastkey = chunks[-1]
                    chunks.remove(lastkey)
                    chunks.insert(0, lastkey)
                    logger.info("Moved 00 to the front of the list!")

                search_file = "%s*" % search_file_name
                for chunk in chunks:
                    logger.debug("Unpacking file %s" % (str(chunk)))
                    header, data = getHeader(paths, chunk)

                    #If the file is curupted, then the file is moved to the graveyard and combine the data we have
                    #into a larger chunk
                    if header is None:
                        logger.warning("Malformed file %s" % str(chunk))

                        if not os.path.exists(ERROR_PATH):
                            os.makedirs(ERROR_PATH)
                        try:
                            shutil.move(os.path.join(paths, chunk),
                                        os.path.join(ERROR_PATH, chunk))
                            logger.info("moving %s to %s" % (chunk, ERROR_PATH))
                        except IOError, e:
                            logger.warning("Unable to move chunk %s, error: %s" % (str(chunk), str(e)))

                        if len(Headers) == 0:
                            continue

                        full_file_path = os.path.join(FULL_DATA_PATH, hourDir, siteID)
                        full_file_name = "%sFull_File-%s.dat" % (file_name, str(CuruptedFiles))
                        logger.info("Combining Files due to corrupted file")

                        if not os.path.exists(full_file_path):
                            os.makedirs(full_file_path)
                        fileCombinationBinary(totalData, Headers[0], full_file_path, full_file_name)
                        CuruptedFiles += 1

                        continue



                    hour = header[1][0:2]
                    year = "20%s" % header[0][4:6]
                    month = header[0][2:4]
                    day = header[0][0:2]
                    site = header[6]
                    hourDir = os.path.join(year, month, day, site, hour)
                    Data += data

                    expectedFiles = header[-2]
                    #If not all 45 files are present, and the data has been sitting for longer than the time specified
                    #in CuruptedTime than the file set is assumed to be malformed, and moved to the graveyard
                    #There was a small revision to software 2.0 where 15 file chunks were sent instead of 45
                    if int(numberOfFiles) != int(expectedFiles) or numberOfFiles != 15:
                        currentTime = datetime.utcnow()
                        fileTime = header[1]
                        fileDate = header[0]
                        fileTimeStamp = datetime(year=int("20" + fileDate[4:6]), month=int(fileDate[2:4]),
                                                 day=int(fileDate[0:2]), hour=int(fileTime[0:2]), minute=int(fileTime[2:4]),
                                                 second=int(fileTime[4:6]))
                        timeDiff = fileTimeStamp - currentTime
                        timeDiff = timeDiff.total_seconds()
                        if abs(timeDiff) > CuruptedTime:
                            CuruptedFiles += 1
                            logger.warning(
                                "Found file set with missing chunks more than an hour old, moving file set, found %s "
                                "Files, expected %s" % (numberOfFiles, str(expectedFiles)))
                            sendToRTEMP(header, numberOfFiles)
                            for curuptedChunk in glob.glob(search_file):
                                if not os.path.exists(ERROR_PATH):
                                    os.makedirs(ERROR_PATH)

                                try:
                                    logger.info("Moving file %s" % curuptedChunk)
                                    shutil.move(os.path.join(paths, curuptedChunk),
                                                os.path.join(ERROR_PATH, curuptedChunk))
                                except IOError, e:
                                    logger.warning("Unable to move chunk %s, error: %s" % (str(curuptedChunk), str(e)))
                            break

                    Headers.append(header)
                    totalData += data
                    chunkPath = os.path.join(CHUNK_DATA_PATH, hourDir)
                    if not os.path.exists(chunkPath):
                        os.makedirs(chunkPath)

                    try:
                        logger.info("Moving %s to %s" % (str(os.path.join(paths, chunk)),
                                                         os.path.join(chunkPath, chunk)))
                        shutil.move(os.path.join(paths, chunk), os.path.join(chunkPath, chunk))
                    except IOError, e:
                        logger.warning("Unable to move chunk %s, error: %s" % (str(chunk), str(e)))

                if CuruptedFiles == 0:
                    full_file_path = os.path.join(FULL_DATA_PATH, hourDir)
                    full_file_name = "%sFull_Data.dat" % file_name
                else:
                    full_file_path = os.path.join(FULL_DATA_PATH, hourDir)
                    full_file_name = "%sFull_Data-%s.dat" % (file_name, str(CuruptedFiles))
                if not os.path.exists(full_file_path):
                    os.makedirs(full_file_path)

                if len(Headers) > 0:
                    logger.info("Making full file %s" % os.path.join(full_file_path, full_file_name))
                    fileCombinationBinary(Data, Headers[0], full_file_path, full_file_name)
                    sendToRTEMP(Headers[0], CuruptedFiles)

                # Double check to make sure no files remain from this set
                for chunk in chunks:
                    if os.path.isfile(chunk):
                        # Check to make sure the directory does exist, otherwise make it
                        if not os.path.exists(chunkPath):
                            os.makedirs(chunkPath)
                        # Move the file to the chunk path
                        try:
                            logger.info("Moving file %s" % chunk)
                            shutil.move(chunk, os.path.join(chunkPath, chunk))
                        except IOError, e:
                            logger.warning("Unable to move chunk %s, error: %s" % (str(chunk), str(e)))

    #Start this part for recursive checking, disabled for checking
    threading.Timer(TIME_DELAY, cleanUp).start()


def main():
    #Main Function
    loggerInit()
    cleanUp()

#Main Entry Point
if __name__ == '__main__':
    # Check to make sure the path for the PID file exists
    if not os.path.isdir(PID_PATH):
        os.makedirs(PID_PATH)
    # Make the PID file and daemon object
    pidFile = os.path.join(PID_PATH, PID_FILE)
    fileManager = MyDaemon(pidFile)

    # Check the argument passed to the system, and execute the command
    if len(sys.argv) == 2:
        if sys.argv[1] == 'start':
            print "**********************************************************************"
            print "              Starting the file manager script"
            print "         Please refer the log file %s/%s" % (LOG_PATH, LOG_FILENAME)
            print "**********************************************************************"

            fileManager.start()
        elif sys.argv[1] == 'stop':
            print "**********************************************************************"
            print "               Stopping the File manager script"
            print "**********************************************************************"
            fileManager.stop()

        elif sys.argv[1] == 'restart':
            print "**********************************************************************"
            print "               Restarting the File manager script"
            print "**********************************************************************"
            fileManager.restart()

        elif sys.argv[1] == 'main':
            print "**********************************************************************"
            print "          Starting the file manager script with no daemon"
            print "         Please refer the log file %s/%s" % (LOG_PATH, LOG_FILENAME)
            print "**********************************************************************"
            loggerInit()
            cleanUp()

        else:
            print "Incorrect argument, " \
                  "Please use ./File_Manager.py start to start the script. See documentation for more detail"
            sys.exit(2)
            sys.exit(0)

    else:
        print "Please use ./File_Manager.py start to start the script. See documentation for more detail"