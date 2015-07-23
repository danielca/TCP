%plot_maker.m This program makes the summary plot
%
%   The script will go through files fromt he previous day and today, 
%   find any full data files and make a summary plot that will be found in 
%   the immage path. This script is meant to be used on the ABOVE server.
%
%   Created by: Casey Daniel
%   Date: 2014/07/31
%
%   Version: 1.0.3
%
%   Changelog:
%       0.1.0:
%           -N/A
%       1.0.0:
%           -Added in an FFT filter notching out ingeter multiples of 60Hz
%           -Search should now include Partial full files
%       1.0.1:
%           -Data now trims the last 5 points instead of depending on the 
%            FileSize parameter, as that one had a rocky start
%           -Figures are now saved at a reasonable size
%           -Other small fixes
%       1.0.2:
%           -Fixed bug where bottom spectrgam was the wrong channel
%       1.0.3:
%           -Changed file name structure so that seconds is now excluded
%
%   Bug Tracker:
%       -None
%
%   TODO:
%       -Be smarter about the directory search
%
%--------------------------------------------------------------------------

%cap the number of matlab threads



%Constants
windowSize = 2048;                                     % Window size for the spectrogram
overLap = windowSize * 0.75;                           % Overlap width  
sampleFreq = 150000;                                   % Sampling rate, samples/second
Window = hann(windowSize);                             % Window function for the spectrogram
rootPath = '/data/vlf/full_files';                     % Server root path
ImmagePath = '/data/vlf/summaryPlots';                 % Server immage path
Bandwidth = 10;                                        % 10 Bins wide

%Main funcion
%set the logging

%Get yesterday's and todays date for the search
today = now;
yesterday = addtodate(today, -1, 'day');
yesterday = datestr(yesterday, 26);
today = datestr(today,26);

%Break out the components of the date
year1 = yesterday(1:4);
month1 = yesterday(6:7);
day1 = yesterday(9:10);
year2 = today(1:4);
month2 = today(6:7);
day2 = today(9:10);

%Combine the directory files
datedir1 = [year1 '/' month1 '/' day1];
datedir2 = [year2 '/' month2 '/' day2];
display('I have actually started')
%Search the subdirectories of root path for the full data files for
%yesterday and today
yesterderdayFiles = rdir([rootPath, '/', datedir1, '/**/*Full_Data.dat']);
todayFiles = rdir([rootPath, ,'/', datedir2, '/**/*Full_Data.dat']);

%Combine the searches
foundFiles = [yesterderdayFiles;todayFiles];
display(foundFiles)
%Loop over all the files
for j = 1:length(foundFiles)
    fileName = foundFiles(j).name; % File path an name
    %extract the actual file name from the path
    display(fileName);
    pos = strfind(fileName,'/');
    pos = pos(end);
    if fileName(37) == '-'
        summaryFileName = [fileName(pos+1:end-14) '-' fileName(38)];
    else
        summaryFileName = fileName(pos+1:end-14);
    end
    %Make the date path, append to the root immage path, and create a root
    %immage path
    try
        datePath = [summaryFileName(1:4) '/' summaryFileName(5:6) '/' summaryFileName(7:8) '/' summaryFileName(17:20) '/' summaryFileName(10:11)];
        summaryPlotPath = [ImmagePath '/' datePath];
        summaryPlotName = [summaryPlotPath '/' summaryFileName(1:13), summaryFileName(16:27) , '_summary_plot.png'];
        CDFFilePath = [CDFPath '/' datePath];
        CDFFileName = ['abv_raw', summaryFileName(16:21), summaryFileName(1:8), summaryFileName(10:13),  '_v01.cdf'];
    catch
        display('Unable to parse file name');
        continue;
    end
    %Check to see if the immage path is a directory, if not make one
    if exist(summaryPlotPath, 'dir') ~= 7
        mkdir(summaryPlotPath);
    end
    
    %Check the path for the CDF File
    display(CDFFilePath)
    if exist(CDFFilePath, 'dir') ~= 7
        mkdir(CDFFilePath)
    end
    
    %Check to see if both cdf and summary plot exists to speed things along
    if exist(summaryPlotName, 'file') == 2 && exist(CDFFileName, 'file') == 2
        continue;
    end
    

    %Open the data file
    dataFile = fopen(fileName);
    header = blanks(115);
    i = 1;
    dataContents = fread(dataFile);

    %Look for the '}' character
    while i < 200
        char = dataContents(i);
        header(i) = char;
        if char == '}'
            break
        end
        i = i + 1;
    end

    %Save the header contents
    header = header(2:i-1);
    headerSplit = strsplit(header,',');


    %start reading the data
    fseek(dataFile, i + 0,'bof');
    Info = dir(fileName);
    Data = fread(dataFile,[1 Info.bytes], 'bit16', 0, 'b'); 
    fseek(dataFile, Info.bytes-10, 'bof');

    %Decide if end key check is needed, and what to do with it
    %endKey = textscan(dataFile, '%s');
    %endKey = endKey{1}{1};
    fclose(dataFile);

    %Trim the data to the correct size
    Data = Data(1:end-5);

    %Gather the data into the channels
    Chan1 = Data(1:2:end);
    Chan2 = Data(2:2:end);

    %check the lengths of Chan1 and Chan2 to ensure they match
    if length(Chan1) ~= length(Chan2)
        continue
    end

    %Check to see if the summary plot already exists.
    if exist(summaryPlotName, 'file') ~= 2
        %Define the noise frequency vectore as every 60Hz up to 75KHz
        noiseFreqs = 60:60:75000;

        %Filter the data
        %[Chan1, Chan2 ] = FFTFilter(Chan1, Chan2, sampleFreq, noiseFreqs, Bandwidth);

        try
            createPlot(Chan1, Chan2, Window, overLap, windowSize, sampleFreq )
        catch ME
            continue;
        end
    
    end;
    
    %Create the CDF File
    
    if exist([CDFFilePath '/' CDFFileName], 'file') ~= 2
        createTimeCDF( CDFFilePath, CDFFileName, Chan1, Chan2, headerSplit )
    end    
end


%We now conclude this script, thank you for your time.
%We know you have a choice in your scripts and we thank you for your patron

