TCP
This repository is used for the ABOVE TCP communications portions. In the main branch will be both a python test client
and the python server client.

There are two branches, one each for people developing. When a version is ready, it will be pushed to the main branch,
and deployed on the server.

This is now divided into several files, with descriptions below

tcp_server/
    tcp_server.py:
        This python script is the essential TCP Sever that receives incoming data from the instruments in the field.
        These files are written to a dump directory

    tcp_client.py:
        This is a sample client script, for the purpose of testing the tcp server

Ingestion_software/
    File_Manager.py:
        This script combines the binary chunks into a single file, and moves the data out of the dump directories.
        This script runs periodically, and will also include RTEMP communications in later revisions, as well as summary
        thumbnails sent to RTEMP.

    Print_IP_List.py:
        Simple script that reads in the ip dictionary file saved by the server and prints the list of IP's to the screen
        NOTE: MUST BE PLACED IN THE SAME DIRECTORY AS THE IP DICTONARY

Both branches contain Daemon.py This file is what allows the scripts to be run in the background.

To start and stop the tcp server and the ingestion scripts in the command line type ./file_name.py start or
./file_name.py stop

More documentation is soon to come.

This is currently in the early stages of development, if you have any questions please contact Casey Daniel at
cdaniel@ucalgary.ca or Dr. Chris Cully at cmcully@ucalgary.ca


===
