#! /usr/bin/env python
#
# Testing program for client side of TCP transmission

import socket

# globals
TCP_HOSTNAME = "136.159.51.230"
TCP_PORT = 25000
BUFFER_SIZE = 1024
MESSAGE = "[CTRL:wakeup]"

try:
    ipAddress = socket.gethostbyname(TCP_HOSTNAME)
except Exception, e:
    print "Error resolving hostname '%s', aborting" % (TCP_HOSTNAME)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ipAddress, TCP_PORT))
s.send(MESSAGE)
data = s.recv(BUFFER_SIZE)
s.close()

print "Received response:", data