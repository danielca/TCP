#! /usr/bin/env python
"""
Summary_Plot.py

version 0.0.1

Description:
  This script is the second level ingestion script, and it takes in the full data files, runs them through a filter,
  and makes a summary plot

Changelog:
  0.0.1:
    -N/A

Bug tracker:
  -N/A

TODO:
  -Add in plotting script
  -Find a way to remember what files have been done already.

"""

import logging
import os
import struct
import glob
import threading

#####################
# Constants
#####################

# Data Strings
DATA_START_KEY = "Data_Start"
START_KEY_LEN = len(DATA_START_KEY)
DATA_STOP_KEY = "Data_Stop\0"
STOP_KEY_LEN = len(DATA_STOP_KEY)

# logging strings
LOG_PATH = "/Users/Casey/Desktop/AboveTest/Logs"  # Casey's mac
#LOG_PATH = "/data/vlf/testServer/logs"  # Server test path
LOGFILE_MAX_BYTES = 1024000 * 100   # 100MB
LOGFILE_BACKUP_COUNT = 5
LOG_FILENAME = "SummaryPlot.log"
logger = None

#Paths
DATA_PATH = "/Users/Casey/Desktop/AboveTest/Data/FullFiles"   # Test Path
#DATA_PATH = "/data/vlf_full_files"                            # server path
#DATA_PATH = "/data/vlf/testServer/FullFiles"                  # Server test path

#Misc
TIME_DELAY = 3 * 60  # Run every 3 minutes

def initLogger():
    """
    Initialization of the logging file
    :return: None
    """

    global logger
    print "Starting the Logger"

    # initialize the logger
    logger = logging.getLogger("ABOVE Summary Plot")
    logger.setLevel(logging.DEBUG)
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
    LOG_FILE = os.path.join(LOG_PATH, LOG_FILENAME)
    handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=LOGFILE_MAX_BYTES, backupCount=LOGFILE_BACKUP_COUNT)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S UTC")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    print "Logger has now been started, please see log file at %s/%s" % (LOG_PATH, LOG_FILENAME)
    print "**********************************************************************"
    # write initial messages
    logger.info("+++++++ ABOVE VLF Summary Plot +++++++")
    logger.info("Starting File Manager......")


def unpackFile(path, fileName):
    """
    This method unpacks the file specified by fileName and located in directory filePath.
    For more information about the channel contents please see the project documentation.
    :param path: Directory of the file
    :param fileName: Name of the file
    :return: header, Channel 1, Channel 2
    """
    full_path = os.path.join(path, fileName)
    header = ""
    #Open the data file
    try:
        with open(full_path, 'rb') as dataFile:
            header += dataFile.read(1)
            #reads the file character by character until '}' is found, marking the end of the header
            if header.endswith("}"):
                logger.info("found header %s" % header)
                headerSplit = header[1:-1].split(",")
                softwareVersion = float(headerSplit[4])

                # check the software version to see if a start key will be present
                if softwareVersion < 2.1:
                    start_key = dataFile.read(START_KEY_LEN)
                    if start_key == DATA_START_KEY:
                        logger.info("Found start key")
                    else:
                        logger.info("Unable to find data start key")
                        return None, None, None

                #read the rest of the file
                fileConents = dataFile.read()

                #check for the end key, possible variants depending on how the file was written
                if fileConents.endswith(DATA_STOP_KEY):
                    logger.debug("Found the data stop key")
                    data = fileConents[:(-1 * STOP_KEY_LEN)]

                elif fileConents.endswith("Data_Stop"):
                    logger.debug("Found data stop key")
                    data = fileConents[:(-1 * len("Data_Stop"))]

                elif fileConents.endswith("Data_Stop "):
                    logger.debug("Found the data stop key")
                    data = fileConents[:(-1 * len("Data_Stop "))]

                else:
                    logger.warning("Unable to find the data stop key")
                    return None, None, None

                #initializes the arrays to the appropriate sizes depending on the header of software version
                if softwareVersion >= 2.1:
                    dataList = [None] * float(headerSplit[16]/2)
                else:
                    dataList = [None] * 20000

                #Unpacks the data in puts it into dataList
                for i in range(0, len(data), 2):
                    dataList[i/2] = struct.unpack('>h', data[i:i+2])[0]

                #split the data into two separate channels, alternating chan1 and chan2
                chan1 = dataList[0::2]
                chan2 = dataList[1::2]

                return header, chan1, chan2
    except IOError, e:
        logger.warning("Ran into an IOError, error: %s" % str(e))


def dataFilter(data):
    #Place holder for the filter method
    return data

def main():
    """
    This main function does the bulk of the work
    First searching through the files, unpacking them, applying a quick filter, followed by making a summary plot
    :return:
    """
    #Something needs to trigger, or something to make sure the data file is not repeated
    file_tag = "*Full_Data.dat"
    for paths, dirs, files in os.walk(DATA_PATH):
        os.chdir(paths)
        for dataFile in glob.glob(file_tag):
            logger.debug("Unpacking file %s" % dataFile)
            header, Chan1, Chan2 = unpackFile(paths, dataFile)
            if header is None:
                continue
            Chan1 = dataFilter(Chan1)
            Chan2 = dataFilter(Chan2)
            #Insert something for plotting here

    threading.Timer(TIME_DELAY, main).start()

if __name__ == "__main__":
    print "*************************************************"
    print "           Starting Summary_Plot.py"
    initLogger()