#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 File Manager Script
 Version: 0.2.0

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


 TODO:
   -Decide on error handling
   -Add in directory for malformed Files
   -send data to RTEMP
   -un-comment the timer function, commented for testing purposes

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
ERROR_PATH = "/data/vlf/MalformedFiles"


# logging strings
LOG_PATH = "/Users/Casey/Desktop/AboveTest/Logs"
LOGFILE_MAX_BYTES = 1024000 * 100   #100MB
LOGFILE_BACKUP_COUNT = 5
LOG_FILENAME = "FileManager.log"
logger = None

#Time from file writen to be found corrupted if the full set is not available
CuruptedTime = 3600 #seconds


def loggerInit():
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
    global logger

    header = ""
    startKey = ""
    dataList = []
    chan1 = []
    chan2 = []
    found = False
    logger.info("Starting file " + fileName)
    if not os.path.isfile(os.path.join(path, fileName)):
        logger.warning("could not find " + fileName)
        return None, None, None

    filesize = os.path.getsize(os.path.join(path, fileName))
    if filesize < 1000:
        logger.warning(fileName + " is below 1000 bytes")
        #contents.close()
        contents = None
        return None, None, None


    with open(os.path.join(path, fileName), 'rb') as contents:


        #looks for the closing bracket in the header of the file

        while found==False:
            char = contents.read(1)
            #print char
            header = header + char
            if char == "}":
                #Once the close bracket is found, the next 10 characters should be the start key
                #startKey = contents.read(10)
                found = True

        #Removes the brackets, and extracts the software version
        header = header[1:-1]
        header_contents = header.split(",")
        SoftwareVersion = header_contents[4]

        #Assembles information based on the software version.
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
                StartKeyLength = 10
                EndKeyLength = 9
                NumberOfChunks = 45
                ExpectedStartKey = "Data_Start"
                ExpectedEndKey = "Data_End "
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
                StartKeyLength = header_contents[17]
                EndKeyLength = header_contents[18]
                NumberOfChunks = 45
                ExpectedStartKey = "Data_Start"
                ExpectedEndKey = "Data_End "
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
                StartKeyLength = header_contents[17]
                EndKeyLength = header_contents[18]
                NumberOfChunks = header_contents[19]
                ExpectedStartKey = "Data_Start"
                ExpectedEndKey = "Data_End "
            except IndexError:
                logger.warning("Unable to unpack header")
        else:
            logger.warning("Unknown software version")

        startKey = contents.read(int(StartKeyLength))
        if startKey == ExpectedStartKey:
            logger.info("Found start key for file "+fileName)
        else:
            logger.warning("No start key found " + fileName + " is corrupted")
            contents.close()
            return None, None, None
        #Looks for the end key in the file
        try:
            logger.debug("Reading the data")
            data = contents.read(int(FileSize))
            #endKey = data[len(data)-10:len(data)]
            endKey = contents.read()
        except IOError:
            logger.warning("IOE error trying to read the end key")
            endKey = None
            contents.close()
            return None, None, None

    if endKey == ExpectedEndKey:
        logger.debug("Found end key ")
    else:
        logger.debug("No end key found in" + fileName)
    #Unpacks the data from binary into signed ints
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
    #Checks to make sure both channels contain 10000 data points. If this is not true the file is curppted
    if len(chan2) != int(FileSize)/4:
        logger.warning("Chanel 2 did not containg the right number of data points, " + fileName + " is corupted")
        contents.close()
        return None, None, None
    if len(chan1) != int(FileSize)/4:
        logger.warning("Chanel 1 did not containg the right number of data points, " + fileName + " is corupted")
        contents.close()
        return None, None, None
    contents.close()
    return header_contents, chan1, chan2


def fileCombination(Chan1, Chan2, Header, fileName, filePath):
    global logger

    Data = []
    logger.info("combining data into one data set")
    for i in range(0, len(Chan1)):
        Data.append(Chan1[i])
        Data.append(Chan2[i])

    Header[16] = 4*len(Data)
    Header = ",".join(str(x) for x in Header)

    logger.info("writing single data file at %s" % (str(os.path.join(filePath, fileName))))
    with open(os.path.join(filePath, fileName), 'wb+') as combinedFile:
        combinedFile.write("%s%s%s%s" % ("{", Header, "}", "Data_Start"))
        for i in range(0, len(Data)):
            combinedFile.write(struct.pack('>h',  Data[i]))
        combinedFile.write("Data_End")
    logger.info("Done writing %s" % fileName)


def cleanUp():
    global logger
    logger.info("Starting clean up")

    for paths, dirs, files in os.walk(RAW_FILE_PATH):
        os.chdir(paths)
        for f in glob.glob("*_00.chunk.dat"):
            Chan1 = []
            Chan2 = []
            Headers = []
            f = f.split("_")
            file_name = "%s_%s_%s_%s_%s_" % (f[0], f[1], f[2], f[3], f[4])
            search_file = "%s%s" % (file_name, "*")

            splitPaths = paths.split(("/"))
            hourDir = "%s/%s/%s" % (splitPaths[-3], splitPaths[-2], splitPaths[-1])
            chunkDir = os.path.join(CHUNK_DATA_PATH, hourDir)
            siteID = ""
            numberOfFiles = len(glob.glob(search_file))
            CuruptedFiles = 0
            for chunk in glob.glob(search_file):
                curuptedData = False
                logger.info("Unpacking file %s" % (str(chunk)))
                header, data1, data2 = unpackFile(paths, chunk)

                if numberOfFiles < header[19]:
                    currentTime = datetime.utcnow()
                    fileTime = header[1]
                    fileDate = header[0]
                    fileTimeStamp = datetime(year=int("20" + fileDate[4:6]), month=int(fileDate[2:4]),
                                             day=int(fileDate[0:2]), hour=int(fileTime[0:2]), minute=int(fileTime[2:4]),
                                             second=int(fileTime[4:6]))
                    timeDiff = fileTimeStamp - currentTime
                    timeDiff = timeDiff.total_seconds()
                    if abs(timeDiff) > CuruptedTime:
                        curuptedData = True
                        logger.warning("Found file set with missing chunks, greater than an hour old")
                    else:
                        break

                if header is not None:
                    Headers.append(header)
                    for i in range(0, len(data1)):
                        Chan1.append(data1[i])
                        Chan2.append(data2[i])
                else:
                    logger.warning("Malformed header")
                    curuptedData = True

                if curuptedData:
                    logger.warning("Invalid file %s" % (str(chunk)))
                    logger.info("moving file %s to %s" % (str(chunk), os.path.join(ERROR_PATH, chunkDir)))
                    shutil.move(os.path.join(paths, chunk), os.path.join(ERROR_PATH, chunkDir, chunk))
                    curuptedData = True
                    Full_File_Name = "%s%s_%s%s" % (file_name, "full_file", str(CuruptedFiles), ".dat")
                    Full_File_Path = os.path.join(FULL_DATA_PATH, siteID, hourDir)
                    CuruptedFiles += 1
                    fileCombination(Chan1, Chan2, Headers[0], Full_File_Name, Full_File_Path)
                    Chan1 = []
                    Chan2 = []
                    Headers = []


                if not os.path.isdir(chunkDir):
                    logger.info("moving file %s to %s" % (str(chunk), chunkDir))
                    os.makedirs(chunkDir)
                if not curuptedData:
                    shutil.move(os.path.join(paths, chunk), os.path.join(chunkDir, chunk))

                if curuptedData == 0:
                    Full_File_Name = "%s%s" % (file_name, "full_file.dat")
                    Full_File_Path = os.path.join(FULL_DATA_PATH, siteID, hourDir)

                else:
                    Full_File_Name = "%s%s_%s%s" % (file_name, "full_file", str(CuruptedFiles), ".dat")
                    Full_File_Path = os.path.join(FULL_DATA_PATH, siteID, hourDir)

            if not os.path.isdir(Full_File_Path):
                os.makedirs(Full_File_Path)
            logger.info("Creating combined file")
            fileCombination(Chan1, Chan2, Headers[0], Full_File_Name, Full_File_Path)


    #Start this part for recursive checking, disabled for checking
    #threading.Timer(TIME_DELAY, cleanUp).start()


def main():

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