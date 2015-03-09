#include <fstream>
#include <iostream>
#include <math.h>

/*
    version: 1.0
    sd_reader.pp
    Created By: Casey Daniel
    Date:March 2015

    This script reads the contents of the ABOVE SD cards, gathers individual data files, and places them in the specified
    directory following the directory format and file names used by ABOVE.

    There are 2 required input args from the command line, input file and out directory. These can be entered as
    ./sdCard if=Inputfile of=OutputDirecotry
    or
    ./sdCard Inputfile OutputDirectory

    There are also 2 optional arguments.
    -hf to fix the header information if it is known that some fields are incorect, as in the first 2 rounds of SD cards
    -sd SDSIZE to change the sd card size from the defaule 128GB.

    Changelog:
        1.0:
            First working version.
 */

using namespace std;

//Constants
string dataLocation;
string outDir;
unsigned long long int sectorSize = 512;
unsigned long long int bytesRead = 0;
long long int sdSize = 128000000000;
char data_stop[10] = "Data_Stop";
int headerFix = 0;

char* fixHeader(char* header) {
    /*
    Some of the header contents written on the eariler SD cards were incorect. Mainly the file size, and number of files
    This functions returns the header string with fixed contets. Brute force was the only way here.
     */
    string date = "";
    string time = "";
    string site = "";
    string intId = "";
    string totalFiles = "";
    string fileNo = "";
    string fileSize = "";
    string GPS = "";
    string HeaderVersion = "";
    string firmware = "";
    string temp = "";
    string software = "";
    string fiveVolt = "";
    string twelveVolt = "";
    string batt = "";
    string clock = "";
    string wifi = "";
    string sd = "";
    string sample = "";
    int commasFound = 0;
    for(int i = 1; header[i] |= '\0', i++;) {

        // increment the number of commas that have been found
        if (header[i] == ',') {
            commasFound ++;
            continue;
        }

        //check for the end f the header
        if (header[i] == '}') {
            break;
        }

        //for some reason the first one never gets added
        if (i==2) {
            date += header[1];
        }
        if (i==1) {
            continue;
        }

        // append to appropriate strings based on the number of commas that have been passed in the header
        if (commasFound == 0) {
            date += header[i];
        }

        else if (commasFound == 1 && time.length() < 6) {
            time += header[i];
        }
        else if (commasFound == 2) {
            fileNo += header[i];
        }
        else if (commasFound == 3) {
            GPS += header[i];
        }
        else if (commasFound == 4) {
            HeaderVersion += header[i];
        }
        else if (commasFound == 5) {
            firmware += header[i];
        }
        else if (commasFound == 6) {
            site += header[i];
        }
        else if(commasFound == 7) {
            software += header[i];
        }
        else if (commasFound == 8) {
            intId += header[i];
        }
        else if(commasFound == 9) {
            fiveVolt += header[i];
        }
        else if (commasFound == 10) {
            twelveVolt += header[i];
        }
        else if (commasFound == 11) {
            batt += header[i];
        }
        else if (commasFound == 12) {
            temp += header[i];
        }
        else if (commasFound == 13) {
            clock += header[i];
        }
        else if (commasFound == 14) {
            wifi += header[i];
        }
        else if (commasFound == 15) {
            sample += header[i];
        }
        else if (commasFound == 16) {
            fileSize += header[i];
        }
        else if (commasFound == 17) {
            totalFiles += header[i];
        }
        else if(commasFound == 18) {
            sd += header[i];
        }

        //paranoia of infinite loops
        if (i > 350) {
            break;
        }
    }
    string newHeaderString = '{' + date + ',' + time + ",0," + GPS + ',' + HeaderVersion + ',' + firmware + ',' + site + ','
            + software + ',' + intId + ',' + fiveVolt + ',' + twelveVolt + ',' + batt + ',' + clock + ',' +
            wifi + ',' + sample + ",600000," + "1," + sd + '}';
    char* newHeader = new char[(int)newHeaderString.length() + 1];
    newHeader[newHeaderString.length() +1] = '\0';
    strcpy(newHeader, newHeaderString.c_str());
    return newHeader;
}


char* findHeader(char* inputData) {
    //Finds the end of the header, and returns the header contents
    int i = 1;

    //look for the end of the header
    while(true) {
        //cout << data[i] << '\n';
        if (inputData[i] == '}') {
            // found the end of the header
            //cout << "found the end of the header " << i << '\n';
            break;
        }
        if (i > 200) { // don't get into an infinite loop here
            cout << "something went wrong here" << '\n';
            break;
        }

        i++;
    }

    // copy the header to a new char array
    char* header = new char[i+1];
    memcpy(header, &inputData[0], (size_t) (i +1));
    header[i+1] = '\0';

    return header;
}

void WriteData(std::ifstream& file_stream, char* data) {
    /*
      fuction to handle the writing of the directory. Takes the file stream object, as well as any current data from the
      sector
     */
    string date = "";
    string time = "";
    string site = "";
    string intId = "";
    string fileNo = "";
    string fileSize = "";

    //Extract the header from the start
    char* header = findHeader(data);
    //if the header fix argument was given, fix the header portions
    if (headerFix == 1) {
        header = fixHeader(header); // This function is used to fix the header values, most of all the file size.
    }

    //loop over the header to find the date, time, site ID, Instrument ID, and expected file size.
    int commasFound = 0;
    for(int i = 1; header[i] |= '\0', i++;) {

        // increment the number of commas that have been found
        if (header[i] == ',') {
            commasFound ++;
            continue;
        }

        //check for the end f the header
        if (header[i] == '}') {
            break;
        }

        //for some reason the first one never gets added
        if (i==2) {
            date += header[1];
        }

        // append to appropriate strings based on the number of commas that have been passed in the header
        if (commasFound == 0) {
            date += header[i];
        }
        if (commasFound == 1 && time.length() < 6) {
            time += header[i];
        }
        if (commasFound == 2) {
            fileNo += header[i];
        }
        if (commasFound == 6) {
            site += header[i];
        }
        if (commasFound == 8) {
            intId += header[i];
        }
        if (commasFound == 15) {
            fileSize += header[i];
        }

        if (site == "piwa") {
            site = "pina";
        } else if (site == "smth") {
            site = "fsmi";
        }

        //paranoia of infinite loops
        if (i > 150) {
            break;
        }
    }

    string formattedDate = "20" + date.substr(4,2) + date.substr(2,2) + date.substr(0,2);
    // Read in the data size
    int fileSizeInt = atoi(fileSize.c_str());
    if (fileSizeInt > 600000) {
        cout << "WHATTTTT FILE SIZE OF " << fileSize << " "<< date << " " << time << '\n';
        fileSizeInt = 600000;
    }

    char *binaryData = (char*) malloc((size_t) fileSizeInt);
    //char* binaryData = new char[fileSizeInt + 1];
    file_stream.read(binaryData, fileSizeInt);
    bytesRead += fileSizeInt;

    //update the site names if needed. If more changes are made, place them here
    if (site == "piwa") {
        site = "pina";
    } else if (site == "smth") {
        site = "fsmi";
    }

    string dateDir = outDir + formattedDate.substr(0,4) + "/" + date.substr(2,2) + "/" + date.substr(0,2) + "/" + site
            + "/" + time.substr(0,2) + "/";

    string fileName = dateDir + formattedDate + "_" + time + "_" + site + "_" + intId + "_Full_Data.dat";
    cout << fileName << '\n';

    //create the directory with the date.
    string mkdirCommand = "mkdir -p " + dateDir;
    system(mkdirCommand.c_str());

    //write data to file
    try {
        //cout << "Write the data file " << '\n';
        //cout << header << " " << strlen(header) << '\n';
        ofstream outFile;
        outFile.open(fileName.c_str());
        outFile.write(header, strlen(header));
        //outFile.write(binaryData, sizeof(binaryData));
        outFile.write(binaryData, fileSizeInt);
        outFile.write(data_stop, sizeof(data_stop));
        outFile.close();
    } catch (ofstream::failure e ) {
        cout << "Unable to write the file " << fileName << '\n';
    }

    //read till the start of the next sector, and de-malloc the data
    unsigned long long int nextSector = (unsigned long long int) ceil(((double) bytesRead)/(double) sectorSize);
    unsigned long long int startOfNextSector;
    startOfNextSector = nextSector * 512;
    unsigned long long int bytesToRead =  (startOfNextSector - bytesRead);
    char dump[bytesToRead];
    file_stream.read(dump, (int) bytesToRead);
    bytesRead += bytesToRead;
    free(binaryData);
}
//Main Entry Point
int main(int argc, char* argv[]) {

    //Check the number of input args. Should be minimum 2 (input file and out directory) plus 3 more optional arguments
    //for the header fix and sd size.
    if (argc < 3  || argc > 6) {
        cout << "incorrect paramters inputed. Please restart with the input and output files";
        return 1;
    }

    //Loops through the input args, and checks to see if its an input file or out dir, or the argument for the header fix
    //If not explicitly set using id= or od=, it will assume the format ./sdCard inputFile outDir
    //the file and/or directory can also be in the middle of quotations.
    for (int k = 1; k < argc; k++) {
        string inputArg = std::string(argv[k]);
        if (inputArg.substr(0, 3) == "if=") {
            dataLocation = inputArg.substr(3, inputArg.length());
            cout << "Pulling data file " << dataLocation << '\n';

        } else if (inputArg.substr(0, 4) == "if='" || inputArg.substr(0, 4) == "if=\"") {
            dataLocation = inputArg.substr(3, inputArg.length() - 1);
            cout << "Pulling data file " << dataLocation << '\n';

        } else if (inputArg.substr(0, 3) == "od=") {
            outDir = inputArg.substr(3, inputArg.length());
            cout << "putting data in the directory " << outDir << '\n';

        } else if (inputArg.substr(0, 4) == "od='" || inputArg.substr(0, 4) == "od=\"") {
            outDir = inputArg.substr(3, inputArg.length() - 1);
            cout << "putting data in the directory " << outDir << '\n';

        } else if (inputArg == "-hf") {
            headerFix = 1;
            cout << "Will fix the header" << '\n';

        } else if (inputArg == "-sd") {
            k++; //increment k to get the file size
            sdSize = (long long) atol(argv[k]);
            cout << "SD size of " << sdSize << '\n';

        } else if (k == 1) {
            if (inputArg.substr(0,1) == "'" || inputArg.substr(0,1) == "\"") {
                dataLocation = inputArg.substr(1,inputArg.length()-1);
            } else {
                dataLocation = inputArg;
            }
            cout << "Pulling data file " << dataLocation << '\n';

        } else if (k == 2) {
            if (inputArg.substr(0,1) == "'" || inputArg.substr(0,1) == "\"") {
                outDir = inputArg.substr(1,inputArg.length()-1);
            } else {
                outDir = inputArg;
            }
            cout << "putting data in the directory " << outDir << '\n';
        }
    }

    //check to make sure there not null
    if (!&outDir || !&dataLocation) {
        cout << "Could not find a valid input and/or out directory. Please see the documentation to correctly format this input";
        return 1;
    }

    //open the data file
    ifstream file_stream;
    file_stream.open(dataLocation);

    //Large number of loops, didn't want to do an infinite one because paranoia
    for( int j = 0; j < 250000000; j++ ) {
        //malloc a sector
        char* data = (char*) malloc((size_t) sectorSize);

        try {

            // read the data file... this will be fun
            file_stream.read(data, (int) sectorSize);
            bytesRead += sectorSize;

            //check for the start of a secotr
            if (data[0] == '{') {
                WriteData(file_stream, data);

            // The first block may be empty, quick check to see if the first block needs to be skipped
            } else if (j == 0 && data[0] != '{') {
                cout << "Skipping the first block" << '\n';
                continue;

            } else {
                //Can't read more than whats in the SD card
                if (bytesRead > sdSize) {
                    break;
                }
            }

        }
        catch (ifstream::failure& e) {
            cout << "Error" << "\n";
            break;
        }
        //de-malloc the sectors
        free(data);

    }
    file_stream.close();
    cout << "Completed Data Extraction";
    return 0;
}