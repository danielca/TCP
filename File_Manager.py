"""
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 File Manager Script
 Version: 0.0.1

 Created by: Casey Daniel
 Date: 13/05/2014

 Description:
  This script will run periodically on the same machine as the tcp server to combine the file chunks, send health
  keeping data back to RTEMP, as well as generate a summary plot thumbnail to be sent back to RTEMP.
  This task will start according to :param:TIME_DELAY. This is measured in seconds.

 Changelog:
    0.0.1:
     -N/A


 TODO:
   -everything

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""
__name__ = '__main__'
import threading
import logging
import os

#################
#  Constants
#################
TIME_DELAY = 60 #Seconds
#RAW_FILE_PATH = "/data/vlf" #Sever Root Path
RAW_FILE_PATH = "/Users/Casey/Desktop/AboveTest/AboveRawData" #Test path for Casey's Mac
LOG_PATH = "/Users/Casey/Desktop/AboveTest/Logs"

# logging strings
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

    print "Logger has now been started, please see log file at %s/%s".format(LOG_PATH, LOG_FILENAME)
    print "**********************************************************************"
    # write initial messages
    logger.info("+++++++ ABOVE VLF File Manager Log +++++++")
    logger.info("Starting File Manager......")


def main():
    global logger
    logger.info("Starting clean up")
    

    threading.Timer(TIME_DELAY, main).start()


#Main Entry Point
if __name__ == '__main__':

    print "**********************************************************************"
    print "Starting the file manager script"

    loggerInit()
    main()