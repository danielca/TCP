#include <fstream>
#include <iostream>
#include <math.h>

using namespace std;

//string dataLocation = "/dev/rdisk2";  // Variable for the mounting point of the SD Card.
string dataLocation = "/Volumes/Untitled/data/smith_data_backup.dat";  // Test location
int sectorSize = 512;
unsigned long bytesRead = 0;
string outDir = "/Volumes/Untitled/data/readData/";
char data_stop[10] = "Data_Stop";

char* fixHeader(char* header) {
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
    string date = "";
    string time = "";
    string site = "";
    string intId = "";
    string totalFiles = "";
    string fileNo = "";
    string fileSize = "";

    char* header1 = findHeader(data);
    char* header = fixHeader(header1); // This function is used to fix the header values, most of all the file size.

    //loop over the header to find the date, time, site ID, Instrument ID, and expected file size.
    int commasFound = 0;
    for(int i = 1; header[i] |= '}', i++;) {

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
        if (commasFound == 16) {
            fileSize += header[i];
        }
        if (commasFound == 17) {
            totalFiles += header[i];
        }


        //paranoia of infinite loops
        if (i > 150) {
            break;
        }
    }


    string formattedDate = "20" + date.substr(4,2) + date.substr(2,2) + date.substr(0,2);
    // Read in the data size
    int fileSizeInt = atoi(fileSize.c_str()) * atoi(totalFiles.c_str());
    if (fileSizeInt > 600000) {
        cout << "WHATTTTT FILE SIZE OF " << fileSize << '\n';
        fileSizeInt = 600000;
    }
    char *binaryData = new char[fileSizeInt];
    file_stream.read(binaryData, fileSizeInt);
    bytesRead += fileSizeInt;

    string dateDir = outDir + formattedDate.substr(0,4) + "/" + date.substr(2,2) + "/" + site + "/" + date.substr(0,2) + "/";
    string fileName = dateDir + formattedDate + "_" + time + "_" + site + "_" + intId + "_Full_Data.dat";
    //cout << fileName << '\n';

    //create the directory with the date.
    string mkdirCommand = "mkdir -p " + dateDir;
    system(mkdirCommand.c_str());

    //cout << "size " << sizeof(binaryData) << '\n';

    //write data to file
    try {
        //cout << "Write the data file " << '\n';
        //cout << header << " " << strlen(header) << '\n';
        ofstream outFile;
        outFile.open(fileName.c_str());
        outFile.write(header, strlen(header));
        outFile.write(binaryData, sizeof(binaryData));
        outFile.write(data_stop, sizeof(data_stop));
        outFile.close();
    } catch (ofstream::failure e ) {
        cout << "Unable to write the file " << fileName << '\n';
    }

    //read till the start of the next sector
    int nextSector = (int) ceil(((double) bytesRead)/512.0);
    int startOfNextSector;
    startOfNextSector = nextSector * 512;
    //cout << startOfNextSector << '\n';
    int bytesToRead = (int) (startOfNextSector - bytesRead);
    char dump[bytesToRead];
    file_stream.read(dump, bytesToRead);
    bytesRead += bytesToRead;
}

int main() {

    ifstream file_stream;
    file_stream.open(dataLocation);

    //file_stream.seekg(512000000); // TESTING ONLY!!!!!!!!!!!!


    for( int j = 0; j < 250000000; j++ ) {


        if (j >= 3){
           // cout << "test" << '\n';
        }

        char* data = new char[sectorSize]; // figure out a decent size for this.....


        try {

            // read the data file... this will be fun
            //cout << "Reading the data file" << '\n';
            file_stream.read(data, sectorSize);
            bytesRead += sectorSize;

            if (data[0] == '{') {
                WriteData(file_stream, data);

            // The first block may be empty, quick check to see if the first block needs to be skipped
            } else if (j == 0 && data[0] != '{') {
                cout << "Skipping the first block" << '\n';
                continue;

            } else {
                //cout << "no start here....." << bytesRead << '\n';
            }

        }
        catch (ifstream::failure& e) {
            cout << "Error" << "\n";
            break;
        }

        delete data;

    }
    file_stream.close();
    return 0;
}