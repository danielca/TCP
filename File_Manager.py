#! /usr/bin/env python
"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 File Manager Script
 Version: 1.0.0

 Created by: Casey Daniel
 Date: 13/05/2014

 Description:
  This script will run periodically on the same machine as the tcp server to combine the file chunks, send health
  keeping data back to RTEMP, as well as generate a summary plot thumbnail to be sent back to RTEMP.
  This task will start according to :param:TIME_DELAY. This is measured in seconds.

 Changelog:
    0.0.1:
      -N/A
    0.0.2:
      -Chunk files are now moved out of the main directory into a chunk directory
    0.0.3:
      -Combined loggers between the unpacking routine and the rest of the file
    1.0.0:
      -Script now combines into a master data file, in the same binary format at as the chucnk files
      -Tested, candidate to start on server


 TODO:
   -send data to RTEMP
   -Add MatLab script
   -create thumbnail and send to RTEMP
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


#################
#  Constants
#################
#Time Delay between clean-ups
TIME_DELAY = 60.0 #Seconds

#File Paths
RAW_FILE_PATH = "/data/vlf" #Sever Root Path
#RAW_FILE_PATH = "/Users/Casey/Desktop/AboveTest/AboveData/" #Test path for Casey's Mac
#CHUNK_DATA_PATH = "/Users/Casey/Desktop/AboveTest/Data/Chunks" #Test Path
CHUNK_DATA_PATH = "/data/vlf_chunks" #server path
#FULL_DATA_PATH = "/Users/Casey/Desktop/AboveTest/Data/FullFiles" #Test Path
FULL_DATA_PATH = "/data/vlf_full_files" #server path


# logging strings
LOG_PATH = "/Users/Casey/Desktop/AboveTest/Logs"
LOGFILE_MAX_BYTES = 1024000 * 100   #100MB
LOGFILE_BACKUP_COUNT = 5
LOG_FILENAME = "FileManager.log"
logger = None


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
                startKey = contents.read(10)
                #header = header + startKey
                #print("found the }")
                found = True
        if startKey == "Data_Start":
            logger.info("Found start key for file "+fileName)
        else:
            logger.warning("No start key found " + fileName + " is corrupted")
            contents.close()
            return None, None, None
        #Looks for the end key in the file
        try:
            logger.debug("Reading the data")
            data = contents.read(40000)
            #endKey = data[len(data)-10:len(data)]
            endKey = contents.read()
        except IOError:
            logger.warning("IOE error trying to read the end key")
            endKey=""
            contents.close()
            return None, None, None

    if endKey == "Data_Stop ":
        logger.debug("Found end key " )
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
    if len(chan2) != 10000:
        logger.warning("Chanel 2 did not containg the right number of data points, " + fileName + " is corupted")
        contents.close()
        return None, None, None
    if len(chan1) != 10000:
        logger.warning("Chanel 1 did not containg the right number of data points, " + fileName + " is corupted")
        contents.close()
        return None, None, None
    contents.close()

    header = header[1:len(header)-1]
    header_parts = header.split(',')
    return header_parts, chan1, chan2


def fileCombination(Chan1, Chan2, Header, fileName, filePath):
    global logger

    Data = []
    logger.info("combining data into one data set")
    for i in range(0, len(Chan1)):
        Data.append(Chan1[i])
        Data.append(Chan2[i])
    logger.info("writing single data file at %s" % (str(os.path.join(filePath, fileName))))
    with open(os.path.join(filePath, fileName), 'wb+') as combinedFile:
        combinedFile.write("%s%s" % (Header, "Data_Start"))
        for i in range(0, len(Data)):
            combinedFile.write(struct.pack('>h',  Data[i]))
        combinedFile.write("Data_End")
    logger.info("Done writing %s" % fileName)


def cleanUp():
    global logger
    logger.info("Starting clean up")
    print "starting"
    print RAW_FILE_PATH

    Chan1 = []
    Chan2 = []
    Headers = []

    for paths, dirs, files in os.walk(RAW_FILE_PATH):
        os.chdir(paths)
        for f in glob.glob("*_00.chunk.dat"):
            #print "found file " + str(f)
            f = f.split("_")
            file_name = "%s_%s_%s_%s_%s_" % (f[0], f[1], f[2], f[3], f[4])
            search_file = "%s%s" % (file_name, "*")
            curuptedData = False

            splitPaths = paths.split(("/"))
            hourDir = "%s/%s/%s" % (splitPaths[-3], splitPaths[-2], splitPaths[-1])
            chunkDir = os.path.join(CHUNK_DATA_PATH, hourDir)

            for chunk in glob.glob(search_file):
                print chunk
                if not curuptedData:
                    logger.info("Unpacking file %s" % (str(chunk)))
                    header, data1, data2 = unpackFile(paths, chunk)
                    if header is not None:
                        Headers.append(header)
                        for i in range(0, len(data1)):
                            Chan1.append(data1[i])
                            Chan2.append(data2[i])
                    else:
                        logger.warning("Invalid file %s" % (str(chunk)))
                        curuptedData = True
                logger.info("moving file %s to %s" % (str(chunk), chunkDir))
                if not os.path.isdir(chunkDir):
                    os.makedirs(chunkDir)
                shutil.move(os.path.join(paths, chunk), os.path.join(chunkDir, chunk))

            Full_File_Name = "%s%s" % (file_name, "full_file.dat")
            Full_File_Path = os.path.join(FULL_DATA_PATH, hourDir)

            if not os.path.isdir(Full_File_Path):
                os.makedirs(Full_File_Path)
            logger.info("Creating combined file")
            fileCombination(Chan1, Chan2, Headers[0], Full_File_Name, Full_File_Path)


    #Start this part for recursive checking, disabled for checking
    threading.Timer(TIME_DELAY, cleanUp).start()


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