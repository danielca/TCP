#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 File Manager Script
 Version: 0.2.1

 Created by: Casey Daniel
 Date: 13/05/2014

 Description:
  This script will run periodically on the same machine as the tcp server to combine the file chunks, send health
  keeping data back to RTEMP, as well as generate a summary plot thumbnail to be sent back to RTEMP.
  This task will start according to :param:TIME_DELAY. This is measured in seconds.

  This will be compatible with previous software versions, however is compatible with tcp server version 2.1.x+

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




 TODO:
   -Decide on error handling
   -un-comment the timer function, commented for testing purposes
   -Deaemon process
   -Uncomment the break statment for the time check

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


#################
#  Constants
#################
#Time Delay between clean-ups
TIME_DELAY = 60.0 #Seconds

#File Paths
RAW_FILE_PATH = "/Users/Casey/Desktop/AboveTest/AboveData/" #Test path for Casey's Mac
#RAW_FILE_PATH = "/data/vlf" #Sever Root Path
CHUNK_DATA_PATH = "/Users/Casey/Desktop/AboveTest/Data/Chunks" #Test Path
#CHUNK_DATA_PATH = "/data/vlf_chunks" #server path
FULL_DATA_PATH = "/Users/Casey/Desktop/AboveTest/Data/FullFiles" #Test Path
#FULL_DATA_PATH = "/data/vlf_full_files" #server path
#ERROR_PATH = "/data/vlf/MalformedFiles" #Server Path
ERROR_PATH = "/Users/Casey/Desktop/AboveTest/Data/MalformedFiles" #test path
ROOT_FILE_PATH = "/data/vlf/testServer"

# logging strings
LOG_PATH = "/Users/Casey/Desktop/AboveTest/Logs"
LOGFILE_MAX_BYTES = 1024000 * 100   #100MB
LOGFILE_BACKUP_COUNT = 5
LOG_FILENAME = "FileManager.log"
logger = None

#Time from file writen to be found corrupted if the full set is not available
CuruptedTime = 3600 #seconds

#RTEMP UDP Info
RTEMP_IP = "136.159.51.160"
RTEMP_PORT = 25000
MAX_PACKET_SIZE = 1024 #1Kb
LAST_PACKET_TIMESTAMP = None

#Key Strings
START_KEY = "Data_Start"
END_KEY = "Data_Stop"
START_KEY_LENGTH = len(START_KEY)
END_KEY_LENGTH = len(END_KEY)

#miscilanious
IP_Dict = {'barr':"1.1.1:1"} #IP Dictionary, barr entry put in for testing purposes
RESEND_TIME = 300 #Seconds for the number of resends to be noted

def loggerInit():
    """
    loggerInit simply initializes the logger file that the log statements can be found in
    :return: None
    """
    global logger


    print "Starting the Logger"

    # initialize the logger
    logger = logging.getLogger("ABOVE VLF Acquisition Logger")
    logger.setLevel(logging.DEBUG)
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
    LOG_FILE = os.path.join(LOG_PATH,LOG_FILENAME)
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=LOGFILE_MAX_BYTES, backupCount=LOGFILE_BACKUP_COUNT)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S UTC")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    print "Logger has now been started, please see log file at %s/%s" % (LOG_PATH, LOG_FILENAME)
    print "**********************************************************************"
    # write initial messages
    logger.info("+++++++ ABOVE VLF File Manager Log +++++++")
    logger.info("Starting File Manager......")


def unpackFile(path, fileName):
    """
    Unpacks the files from binary into integers as well as the header
    :param path: The path to the file
    :param fileName: the name of the file to be unpacked
    :return: Header(as a list of strings), Channel 1(as a list of integers), Channel 2 (As a list of integers)
    Please see project documentation to find the directions of Channel 1 and Channel 2
    """
    global logger

    header = ""
    startKey = ""
    dataList = []
    chan1 = []
    chan2 = []
    found = False
    logger.info("Starting file " + fileName)

    #Checks if file exists first
    if not os.path.isfile(os.path.join(path, fileName)):
        logger.warning("could not find " + fileName)
        return None, None, None

    #Quick check to make sure file is not really small and most likely corrupted
    filesize = os.path.getsize(os.path.join(path, fileName))
    if filesize < 1000:
        logger.warning(fileName + " is below 1000 bytes")
        #contents.close()
        contents = None
        return None, None, None

    #Opens the file in a loop
    with open(os.path.join(path, fileName), 'rb') as contents:


        #looks for the closing bracket in the header of the file
        while found==False:
            char = contents.read(1)
            #print char
            header += char
            if char == "}":
                found = True

        #Removes the brackets, splits into a list, and extracts the software version
        header = header[1:-1]
        header_contents = header.split(",")
        SoftwareVersion = header_contents[4]

        #Assembles information based on the software version.
        #Please see the documentation for information regarding the headers
        #When new SoftwareVersions are implimented, please update this script acordingly
        if SoftwareVersion == '1.3':
            try:
                Date = header_contents[0]
                Time = header_contents[1]
                Offset = header_contents[2]
                GPSFix = header_contents[3]
                FirmwareVersion = header_contents[5]
                SiteID = header_contents[6]
                AntennasSampled = header_contents[7]
                InstrumentID = header_contents[8]
                FiveVolt = header_contents[9]
                TwelveVolt = header_contents[10]
                BatteryTemp = header_contents[11]
                ClockSpeed = header_contents[12]
                BoardTemp = header_contents[13]
                WifiStrength = header_contents[14]
                FileSize = 40000
                START_KEY_LENGTH = 10
                END_KEY_LENGTH = 9
                NumberOfChunks = 45
                START_KEY = "Data_Start"
                END_KEY = "Data_End "
            except IndexError:
                logger.warning("Unable to unpack header")
                return None, None, None

        elif SoftwareVersion == '2.0':
            try:
                Date = header_contents[0]
                Time = header_contents[1]
                Offset = header_contents[2]
                GPSFix = header_contents[3]
                FirmwareVersion = header_contents[5]
                SiteID = header_contents[6]
                AntennasSampled = header_contents[7]
                InstrumentID = header_contents[8]
                FiveVolt = header_contents[9]
                TwelveVolt = header_contents[10]
                BatteryTemp = header_contents[11]
                ClockSpeed = header_contents[12]
                BoardTemp = header_contents[13]
                WifiStrength = header_contents[14]
                SampleRate = header_contents[15]
                FileSize = header_contents[16]
                START_KEY_LENGTH = header_contents[17]
                END_KEY_LENGTH = header_contents[18]
                NumberOfChunks = 45
                START_KEY = "Data_Start"
                #END_KEY_LENGTH = "Data_Start"
                END_KEY = "Data_End "
            except IndexError:
                logger.warning("Unable to unpack header")

        elif SoftwareVersion == '2.1':
            try:
                Date = header_contents[0]
                Time = header_contents[1]
                Offset = header_contents[2]
                GPSFix = header_contents[3]
                FirmwareVersion = header_contents[5]
                SiteID = header_contents[6]
                AntennasSampled = header_contents[7]
                InstrumentID = header_contents[8]
                FiveVolt = header_contents[9]
                TwelveVolt = header_contents[10]
                BatteryTemp = header_contents[11]
                ClockSpeed = header_contents[12]
                BoardTemp = header_contents[13]
                WifiStrength = header_contents[14]
                SampleRate = header_contents[15]
                FileSize = header_contents[16]
                NumberOfChunks = header_contents[17]
                END_KEY = "Data_End"
                END_KEY_LENGTH = len(END_KEY)
            except IndexError:
                logger.warning("Unable to unpack header")
        else:
            logger.warning("Unknown software version")

        #Reads the start key for data from software versions prior to 2.1, as of 2.1 the start key is no longer present
        if float(SoftwareVersion) < 2.1:
            startKey = contents.read(int(START_KEY_LENGTH))
            if startKey == START_KEY:
                logger.info("Found start key for file "+fileName)
            else:
                logger.warning("No start key found " + fileName + " is corrupted")
                contents.close()
                return None, None, None

        #Looks for the end key in the file
        try:
            logger.debug("Reading the data")
            #data = contents.read(int(FileSize))
            data = contents.read()
            endKey = data[int(-1 * int(END_KEY_LENGTH)):]
            data = data[:int(-1 * int(END_KEY_LENGTH))]
            #endKey = data[len(data)-10:len(data)]
            #endKey = contents.read()
        except IOError:
            logger.warning("IOE error trying to read the end key")
            endKey = None
            contents.close()
            return None, None, None

    #Check the end key
    if endKey == END_KEY:
        logger.debug("Found end key ")
    else:
        logger.debug("No end key found in" + fileName)

    #Unpacks the data from binary into signed integer
    for i in range(0, len(data), 2):
        value = data[i:i+2]
        if len(value) == 2:
            number = struct.unpack('>h', data[i:i+2])
            #print number
            dataList.append(number[0])
        else:
            break
    logger.debug("total points found is " + str(len(dataList)))

    #Splits data into two channels
    for j in range(0, len(dataList)):
        if j % 2 != 0:
            chan2.append(dataList[j])
            #if dataList[j] != 0:
                #print("chan2 has a non 0 " + str(j))
        else:
            chan1.append(dataList[j])

    #Checks to make sure both channels contain the right number data points. If this is not true the file is corrupted
    if len(chan2) != int(FileSize)/4:
        logger.warning("Chanel 2 did not contains the right number of data points, " + fileName + " is corrupted")
        contents.close()
        return None, None, None
    if len(chan1) != int(FileSize)/4:
        logger.warning("Chanel 1 did not containg the right number of data points, " + fileName + " is corupted")
        contents.close()
        return None, None, None
    contents.close()
    return header_contents, chan1, chan2


def fileCombination(Chan1, Chan2, Header, fileName, filePath):
    """
    Combines the file chunks into one master file
    file format is the same as the file chunks, please refer to documentation
    :param Chan1: Data from Channel 1, as a list
    :param Chan2: Data from Channel 2, as a list
    :param Header: Header information, as a list
    :param fileName: The destination file name
    :param filePath: The destination file path
    :return: None
    """

    global logger

    Data = []
    logger.info("combining data into one data set")
    for i in range(0, len(Chan1)):
        Data.append(Chan1[i])
        Data.append(Chan2[i])

    softwareVersion = Header[4]

    #edits the header entry for the file size
    Header[16] = sys.getsizeof(Data)
    Header = ",".join(str(x) for x in Header)

    logger.info("writing single data file at %s" % (str(os.path.join(filePath, fileName))))
    with open(os.path.join(filePath, fileName), 'wb+') as combinedFile:

        if float(softwareVersion) < 2.1:
            combinedFile.write("{%s}Data_Start" % Header)
        else:
            combinedFile.write("{%s}" % Header)

        for i in range(0, len(Data)):
            combinedFile.write(struct.pack('>h',  Data[i]))
        combinedFile.write("Data_End")
    logger.info("Done writing %s" % fileName)

def sendToRTEMP(Header, malformed_packets):
    """
    Responisble for sending health keeping information to the RTEMP server at the University of Calgary
    :param Header: Header contents, as a list
    :return: None
    """
    global logger
    global LAST_PACKET_TIMESTAMP

    #extracts information
    timeStamp = datetime.utcnow()
    version = "2.0"
    project = "above"
    site = Header[6]
    device = Header[8]
    date = Header[0]
    time = Header[1]
    batt_temp = Header[11]
    gps_fix = Header[3]
    temp = Header[12]
    rssi = Header[14]
    V_batt = Header[11]
    V_twelve = Header[10]
    V_five = Header[9]

    current_time = datetime.utcnow()
    #We can't send RTEMP packets to quickly, otherwise we can overload the server
    if LAST_PACKET_TIMESTAMP is not None:
        timeDiff = current_time - LAST_PACKET_TIMESTAMP
        timeDiff = timeDiff.total_seconds()
        if timeDiff < 10:
            Time.sleep(10)
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

    if len(array) > 0:
        resends = 0
        for entry in reversed(array):
            timeStamp = datetime(entry[0])
            timeDiff = timeStamp - current_time
            timeDiff = timeDiff.total_seconds()
            if timeDiff < RESEND_TIME:
                resends += entry[1]
            else:
                break
    else:
        resends = 0
    try:
        f = open(os.path.join(ROOT_FILE_PATH, "Dictionary", "DataResends.txt"), 'w')
        f.write("")
        f.close()
    except IOError, e:
        logger.debug("Unable to clear dataResends file, error: %s" % str(e))


    #Assembles the basic information required
    #To change the data sent, simply change this string. Key values and data are separated by a single space
    #Make sure you tell Darren as well
    RTEMP_packet = "batt_temp %s gps_fix %s temp %s V_batt %s V_12 %s V_5 %s rssi %s IP_addr %s malformed_packets %s " \
                   "number_of_resends %s" % (batt_temp, gps_fix, temp, V_batt, V_twelve, V_five, rssi, str(IP_addr),
                                             str(malformed_packets), str(resends))
    #Find the size of the information
    packet_size = sys.getsizeof(RTEMP_packet)

    #There is a maximum packet size of ~1400 Bytes that can be in the UDP packet, to ensure that the entire packet
    #Can be transmitted, the maximum packet size is set to 1024 Bytes.
    #If more information is needed, then the packets are queued appropriately
    if packet_size < MAX_PACKET_SIZE:
        RTEMP_header = "monitor %s version %s project %s site %s device %s date %s time %s PACKET_NUMBER %s " \
                       "PACKET_QUEUE_LENGTH %s" % (timeStamp, version, project, site, device, date, time, str(1),
                                                   str(0))
        RTEMP_message = "%s %s" % (RTEMP_header, RTEMP_packet)
        logger.info("Sending RTEMP Packet")
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            soc.sendto(RTEMP_message, (RTEMP_IP, RTEMP_PORT))
        except socket.error, e:
            logger.warning("Unable to send RTEMP Packet, error: %s" % str(e))

    else:
        numberOfPackets = packet_size%MAX_PACKET_SIZE + 1
        for i in range(0, numberOfPackets):
            RTEMP_header = "monitor %s version %s project %s site %s device %s date %s time %s PACKET_NUMBER %s " \
                       "PACKET_QUEUE_LENGTH %s" % (timeStamp, version, project, site, device, date, time, str(1),
                                                   str(numberOfPackets - i - 1))
            RTEMP_message = "%s %s" % (RTEMP_header, RTEMP_packet[i*MAX_PACKET_SIZE:(i+1) * MAX_PACKET_SIZE])
            logger.info("Sending RTEMP packet %s/%s" % (str(i), str(numberOfPackets)))
            try:
                soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                soc.sendto(RTEMP_message, (RTEMP_IP, RTEMP_PORT))
            except socket.error, e:
                logger.warning("Unable to send RTEMP Packet, error: %s" % str(e))
            #Ensures we don't overload the server
            Time.sleep(10)


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
            for f in glob.glob("*_00.chunk.dat"):
                Chan1 = []
                Chan2 = []
                Headers = []
                f = f.split("_")
                #Get the base file name
                file_name = "%s_%s_%s_%s_%s_" % (f[0], f[1], f[2], f[3], f[4])
                search_file = "%s*" % file_name

                #Gets the directory information
                splitPaths = paths.split("/")
                print splitPaths
                #hourDir = "%s/%s/%s" % (splitPaths[-3], splitPaths[-2], splitPaths[-1])
                #chunkDir = os.path.join(CHUNK_DATA_PATH, hourDir)
                siteID = ""
                numberOfFiles = len(glob.glob(search_file))
                CuruptedFiles = 0
                #loops over the file chunks, and unpacks them
                for chunk in glob.glob(search_file):
                    curuptedData = False
                    logger.info("Unpacking file %s" % (str(chunk)))
                    header, data1, data2 = unpackFile(paths, chunk)

                    #If the file is curupted, then the file is moved to the graveyard and combine the data we have
                    #into a larger chunk
                    if header is None:
                        logger.warning("Malformed file %s" % str(chunk))

                        if not os.path.exists(ERROR_PATH):
                            os.makedirs(ERROR_PATH)
                        try:
                            shutil.move(os.path.join(paths, chunk),
                                            os.path.join(ERROR_PATH, chunk))
                        except IOError, e:
                            logger.warning("Unable to move chunk %s, error: %s" % (str(chunk), str(e)))

                        if len(Headers) == 0:
                            continue

                        full_file_path = os.path.join(FULL_DATA_PATH, hourDir, siteID)
                        full_file_name = "%sFull_File-%s.dat" % (file_name, str(CuruptedFiles))
                        logger.info("Combining Files due to corrupted file")
                        if not os.path.exists(full_file_path):
                            os.makedirs(full_file_path)
                        fileCombination(Chan1, Chan2, Headers[0], full_file_name, full_file_path)
                        CuruptedFiles += 1

                        continue



                    hour = header[1][2:4]
                    year = "20%s" % header[0][4:6]
                    month = header[0][2:4]
                    day = header[0][0:2]
                    site = header[6]
                    hourDir = os.path.join(year, month, day, site, hour)

                    if float(header[4]) < 2.1:
                        expectedFiles = 45
                    else:
                        expectedFiles = header[17]
                    #If not all 45 files are present, and the data has been sitting for longer than the time specified
                    #in CuruptedTime than the file set is assumed to be malformed, and moved to the graveyard
                    if numberOfFiles < expectedFiles:
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
                            curuptedData = True
                            logger.warning("Found file set with missing chunks more than an hour old, moving file set")
                            for curuptedChunk in glob.glob(search_file):
                                if not os.path.exists(ERROR_PATH):
                                    os.makedirs(ERROR_PATH)

                                try:
                                    shutil.move(os.path.join(paths, curuptedChunk),
                                            os.path.join(ERROR_PATH, curuptedChunk))
                                except IOError, e:
                                    logger.warning("Unable to move chunk %s, error: %s" % (str(curuptedChunk), str(e)))
                            #break




                    Headers.append(header)
                    for i in range(0, len(data1)):
                        Chan1.append(data1[i])
                        Chan2.append(data2[i])
                    chunkPath = os.path.join(FULL_DATA_PATH, hourDir, "Chunks")
                    if not os.path.exists(chunkPath):
                        os.makedirs(chunkPath)
                    try:
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
                    fileCombination(Chan1, Chan2, Headers[0], full_file_name, full_file_path)
                    sendToRTEMP(Headers[0], CuruptedFiles)

    #Start this part for recursive checking, disabled for checking
    #threading.Timer(TIME_DELAY, cleanUp).start()


def main():
    #Main Function
    global logger

    logger.info("Starting initial clean up")

    cleanUp()

    #threading.Timer(TIME_DELAY, main).start()


#Main Entry Point
if __name__ == '__main__':

    print "**********************************************************************"
    print "Starting the file manager script"

    loggerInit()

    main()