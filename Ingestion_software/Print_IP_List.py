#! /usr/bin/env python
"""
Print_IP_List.py

The purpose of this script is to simply read in the IP dictionary used by the server and print it to screen.
This must be in the same directory as Ip_Dict.pkl
"""
IP_Dict = {}
import pickle
try:
    ips = open("Dictionary", "Ip_Dict.pkl", 'r')
    IP_Dict = pickle.load(ips)
    ips.close()
    for key, value in IP_Dict.iteritems():
        print key, "    ", IP_Dict[key]
except IOError, e:
    print "Unable to open file"