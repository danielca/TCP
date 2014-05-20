#! /usr/bin/env python
#
# Testing program for client side of TCP transmission
import socket


# globals
TCP_HOSTNAME = "136.159.51.230"
TCP_PORT = 26000
BUFFER_SIZE = 1024
MESSAGE = "[CTRL:wakeup]"
End_Message = "[CTRL:close]"
CONTROL_DATA_RESPONSE = "[CTRL:d-ok]"
#Header for falsified data
fheader = "[CTRL:hskvals]{150514,233025.004,1,G3,2.0,20140509a,test,3,abovetest,151,145,167,255,0,-47,667,220,10,9}"

#This is the falsified data created for tesing purposes
fdata = 1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890

#String sent to server, simulating what is actually sent from sites
fmessage = "Data_Start%sData_Stop" % (fdata)

try:
    ipAddress = socket.gethostbyname(TCP_HOSTNAME)
except Exception, e:
    print "Error resolving hostname '%s', aborting" % (TCP_HOSTNAME)

#Waking server up
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ipAddress, TCP_PORT))
s.send(MESSAGE)
data = s.recv(BUFFER_SIZE)
s.close()


#Opening connection for the information to be sent from the client to theserver
#header first, then response message, sending false data string, then
#closing connection and getting a closing response from server.
ts = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ts.connect((ipAddress, TCP_PORT))
ts.send(fheader)
fdata_recv = ts.recv(BUFFER_SIZE)
ts.send(fmessage)
ts.send(End_Message)
ts.close()

print "Received response:", data
print "Received test response:", fdata_recv