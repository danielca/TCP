#! /usr/bin/env python
"""
Print_IP_List.py

The purpose of this script is to simply read in the IP dictionary used by the server and print it to screen.
"""
IP_Dict = {}
import pickle
import os

file_path = "/data/vlf/Dictionary"
try:
    ips = open(os.path.join(file_path, "Ip_Dict.pkl"), 'r')
    IP_Dict = pickle.load(ips)
    ips.close()
    for key, value in IP_Dict.iteritems():
        print key, "    ", IP_Dict[key]
except IOError, e:
    print "Unable to open file"