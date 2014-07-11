#! /usr/bin/env python
"""
tcp_client.py
Author: Casey Daniel
Date: 11 June 2014
version: 1.1.0

Description:
  This script is used for the purpose of testing the tcp server used for the ABOVE array. As of version 1.0, this
  script is geared towards tcp server version 2.1. Sample data is added in for the purpose of testing. The site
  ID is tst2. This script is looped to allow for through testing.

Changelog:
  1.0:
    -N/A

  1.1.0:
    -Bug Fixes

Bug tracker:
  -NA

TODO:
  -Add in binary data transmission
  -Handle data resend in a better manner, currently it's just ignored
"""
import socket
import random
import sys
import datetime
import threading
import time
import struct


##############
#GLOBALS
##############

#Ip Inofrmation
TCP_ADDR = "136.159.51.230"
TCP_PORT = 27000
BUFFER_SIZE = 1024

#Control Strings
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

#misc
TIME_DELAY = 3*60  # run every 3 min




#makes the header and data list
def makePacket(date, time, packetNo, maxPackets):
    binary_data = struct.pack(">h", 10)
    #make 100 random integers from -100 to 100
    for i in range(1, 20000):
        rand_num = random.randint(-100, 100)
        binary_data += struct.pack(">h", rand_num)

    #get the sizes of the packets
    #Get the time and date for the header


    #Assemble the header for version 2.1
    #{120514,233025.004,1,G3,2.1,20140509a,test,20140509,above,151,145,167,255,0,-47,667,40000,1,1000}
    header = "{%s,%s,%s,G3,2.1,20140509a,tst2,20140509,above,151,145,167,255,0,-47,667,%s,%s,100}" % \
             (str(date), str(time), str(packetNo), str(40000), str(maxPackets))
    return binary_data, header

#function to actually send the packets to the server
def dataSending(socket):
    #loop over 45 files, just like the instrument
    date = datetime.datetime.utcnow().strftime("%d%m%y")
    time = datetime.datetime.utcnow().strftime("%H%M%S.%f")
    time = time[:10]
    for i in range(0, 45):
        missedPackets = 0
        binary_data, header = makePacket(date, time, i, 45)
        #send the header controll string
        socket.send(CONTROL_HSK_RECEIVE)
        #get the response
        socket.send(header)
        response = socket.recv(BUFFER_SIZE)
        print response

        #check the responses against what could actually come in
        if response.startswith("[CTRL:dr-00:00]"):
            #data request received, send the data
            socket.send(binary_data)
            socket.send("Data_Stop\0")

            response2 = socket.recv(BUFFER_SIZE)

            if response2.startswith(CONTROL_DATA_RESPONSE_OK):
                continue
            else:
                response = response2

        if response.startswith(CONTROL_DATA_RESPONSE_NOK):
            #packet has been mised
            missedPackets += 1
            if missedPackets > 4:
                socket.send(CONTROL_CLOSE)
                return

            socket.send(CONTROL_HSK_RECEIVE)
            socket.send(header)

        if response == "":
            return

    return


#main function
def main():
    #initialize the socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_ADDR, TCP_PORT))
    s.settimeout(15)

    #send the wake up controll string
    s.send(CONTROL_WAKEUP_CALL_RECEIVE)
    counter = 0
    #get and check the response
    while 1:
        counter += 1
        recv = s.recv(BUFFER_SIZE)
        print recv

        if recv.startswith("[CTRL:awake]"):
            dataSending(s)
            break
        if counter > 10:
            break
        counter += 1

    #close the connection
    s.send(CONTROL_CLOSE)
    s.close()

    #repeat this funcion every TIME_DELAY interval
    #threading.Timer(TIME_DELAY, main).start()

#main entry point
if __name__ == "__main__":
    #for i in range(100):
    main()
        #time.sleep(TIME_DELAY)