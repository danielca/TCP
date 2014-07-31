%plot_maker.m This program makes the summary plot
%
%   The script will go through all files found below rootPath, find any
%   full data files and make a summary plot that will be found in the
%   immage path. This script is meant to be used on the ABOVE server
%
%   Created by: Casey Daniel
%   Date: 2014/07/31
%
%   Version: 0.1.0
%
%   Changelog:
%       0.1.0:
%           -N/A
%
%   Bug Tracker:
%       -None
%
%   TODO:
%       -Add in a FFT filter
%
%--------------------------------------------------------------------------

%Constants
windowSize = 2048;                                     % Window size for the spectrogram
overLap = windowSize * 0.75;                           % Overlap width  
sampleFreq = 150000;                                   % Sampling rate, samples/second
Window = hann(windowSize);                             % Window function for the spectrogram
rootPath = '/Users/Casey/Desktop/MatlabTest/Data';     % Test root path
ImmagePath = '/Users/Casey/Desktop/SummaryPlots';      % Test Path

%Main funcion
%Search the subdirectories of root path for the full data files
foundFiles = rdir([rootPath, '/**/*Full_Data.dat']);

%Loop over all the files
for j = 1:length(foundFiles)
    fileName = foundFiles(j).name; % File path an name
    
    %extract the actual file name from the path
    pos = strfind(fileName,'/');
    pos = pos(end);
    summaryFileName = fileName(pos+1:end-14);
    
    %Make the date path, append to the root immage path, and create a root
    %immage path
    datePath = [summaryFileName(1:4) '/' summaryFileName(5:6) '/' summaryFileName(7:8) '/' summaryFileName(17:20) '/' summaryFileName(10:11)];
    summaryPlotPath = [ImmagePath '/' datePath];
    summaryPlotName = [summaryPlotPath '/' summaryFileName, '_summary_plot.png'];
    
    %Check to see if the immage path is a directory, if not make one
    if exist(summaryPlotPath, 'dir') ~= 7
        mkdir(summaryPlotPath);
    end
    %Check to see if the immage is already made, if so skip it
    if exist(summaryPlotName, 'file') == 2
        continue
    end
    
    %Open the data file
    dataFile = fopen(fileName);
    header = blanks(115);
    i = 1;
    dataContents = fread(dataFile);
    %Look for the '}' character
    while i < 115
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
    fileSize = str2double(headerSplit(17)); 
    %start reading the data
    fseek(dataFile, i + 0,'bof');
    Info = dir(fileName);
    Data = fread(dataFile,[Info.bytes 1], 'bit16', 0, 'b'); 
    fseek(dataFile, Info.bytes-10, 'bof');

    %Decide if end key check is needed, and what to do with it
    %endKey = textscan(dataFile, '%s');
    %endKey = endKey{1}{1};
    fclose(dataFile);

    %Data = Data(1:fileSize/2);
    %Gather the data into the channels
    Chan1 = Data(1:2:end);
    Chan2 = Data(2:2:end);
    
    %Filter is a work in progress, commented out for now.
    %[Chan1, Chan2 ] = FFTFilter(Chan1, Chan2, sampleFreq);
    
    %Make the time serries vector for plotting
    timeSerries = linspace(1, length(Chan1), length(Chan1))/sampleFreq;
    maxTime = length(Chan1)/sampleFreq;

    %start making the plots!
    set(gcf, 'Visible', 'off');
    subplot(4,1,1);
    spectrogram(Chan1, Window, overLap,windowSize, sampleFreq, 'yaxis');
    colorbar;
    axis([0 maxTime 0 75000]);
    title('Channel 1');
    
    
    subplot(4,1,2);
    spectrogram(Chan2, Window, overLap,windowSize, sampleFreq, 'yaxis');
    colorbar;
    axis([0 timeSerries(end) 0 75000]);
    title('Channel 2');

    subplot(4,1,3);
    plot(timeSerries, Chan1);
    title('Channel 1');
    
    subplot(4,1,4);
    plot(timeSerries, Chan2);
    title({'Channel 2',})
    %Save said plots
    saveas(1,summaryPlotName);
end
%We now conclude this script, thank you for your time.