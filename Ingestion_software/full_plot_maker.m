%plot_maker.m This program makes the summary plot
%
%   The script will go through all files found below rootPath, find any
%   full data files and make a summary plot that will be found in the
%   immage path. This script is meant to be used on the ABOVE server
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
%
%   Bug Tracker:
%       -None
%
%   TODO:
%       -Be smarter about the directory search
%
%--------------------------------------------------------------------------

%Constants
windowSize = 2048;                                     % Window size for the spectrogram
overLap = windowSize * 0.75;                           % Overlap width  
sampleFreq = 150000;                                   % Sampling rate, samples/second
Window = hann(windowSize);                             % Window function for the spectrogram
logFile = 'data/vlf/logs/plot_maker_log.txt';          % Logging file
rootPath = '/Users/Casey/Desktop/MatlabTest/Data';    % Test root path
%rootPath = '/data/vlf/full_files';                     % Server root path
ImmagePath = '/Users/Casey/Desktop/SummaryPlots';     % Test Path
%ImmagePath = '/data/vlf/summaryPlots';                 % Server immage path
Bandwidth = 10;                                        % 10 Bins wide

%Main funcion
%set the logging
%diary logFile;

%Combine the searches
foundFiles = rdir([rootPath, '/**/*Full_Data*.dat']);
%Loop over all the files
for j = 1:length(foundFiles)
    fileName = foundFiles(j).name; % File path an name
    %extract the actual file name from the path
    pos = strfind(fileName,'/');
    pos = pos(end);
    if fileName(37) == '-'
        summaryFileName = [fileName(pos+1:end-14) '-' fileName(38)];
    else
        summaryFileName = fileName(pos+1:end-14);
    end
    %Make the date path, append to the root immage path, and create a root
    %immage path
    datePath = [summaryFileName(1:4) '/' summaryFileName(5:6) '/' summaryFileName(7:8) '/' summaryFileName(17:20) '/' summaryFileName(10:11)];
    summaryPlotPath = [ImmagePath '/' datePath];
    summaryPlotName = [summaryPlotPath '/' summaryFileName(1:13), summaryFileName(16:27) , '_summary_plot.png'];
    
    %Check to see if the immage path is a directory, if not make one
    if exist(summaryPlotPath, 'dir') ~= 7
        mkdir(summaryPlotPath);
    end
    %Check to see if the immage is already made, if so skip it
    if exist(summaryPlotName, 'file') == 2
        continue
    end
    display(summaryPlotName)
    
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
    
    
    %Define the noise frequency vectore as every 60Hz up to 75KHz
    noiseFreqs = 60:60:75000;
    
    %Filter the data
    %[Chan1, Chan2 ] = FFTFilter(Chan1, Chan2, sampleFreq, noiseFreqs, Bandwidth);
    
    %Compute the spectrograms for each channel 
    [S1, F1, T1] = spectrogram(Chan1, Window, overLap,windowSize, sampleFreq);
    [S2, F2, T2] = spectrogram(Chan2, Window, overLap,windowSize, sampleFreq);
    
    %Make the time serries vector for plotting
    timeSerries = linspace(1, length(Chan1), length(Chan1))/sampleFreq;
    maxTime = length(Chan1)/sampleFreq;
    
    %Set the values and labels for the y-axis of the spectrograms
    upperVectorValues = [0 15000 30000 45000 60000 75000];
    upperVectorLabels = {'0' '15' '30' '45' '60' '75'};
    lowerVectorValues = [0 2000 4000 6000 8000 10000];
    lowerVectorLabels = {'0' '2' '4' '6' '8' '10'};
    colorRange = [3,15];
    
    %Set the figure vairables
    close all;
    fig = figure(1);
    set(gcf, 'Visible', 'off');
    set(gca, 'FontSize', 100, 'fontWeight', 'bold');
    set(findall(gcf,'type','text'),'FontSize',100,'fontWeight','bold');
    
    %Now what you have all been waiting for, the plots!
    %North-South 0-75Khz Plot
    subplot('position',[0.08 0.81 0.9 0.12]);
    imagesc(T1, F1, log(abs(S1))); 
    set(gca,'YDir', 'normal');
    colorbar;
    caxis(colorRange);
    axis([0 maxTime 0 75000]);
    set(gca,'xtick',[])
    set(gca,'xticklabel',[])
    set(gca,'YTick', upperVectorValues);
    set(gca,'YTickLabel',upperVectorLabels); 
    
    title({[summaryFileName(1:4) '-' summaryFileName(5:6) '-' summaryFileName(7:8) ' ' summaryFileName(10:11) ':' summaryFileName(12:13) ':' summaryFileName(14:15) ' ' summaryFileName(17:20)],'North-South'});
    %20140714_175009_cmrs_above
    %North-South 0-10KHz plot
    subplot('position', [0.08 0.66 0.9 0.12]);
    imagesc(T1, F1, log(abs(S1)) ); 
    set(gca,'YDir', 'normal');
    c=colorbar;
    caxis(colorRange);
    ylabel(c,'logrithm of Arbitary Units')
    axis([0 maxTime 0 10000]);
    set(gca,'xtick',[])
    set(gca,'xticklabel',[])
    set(gca,'YTick',lowerVectorValues);
    set(gca,'YTickLabel',lowerVectorLabels);
    ylabel('Frequency (KHz)'); 
    
    %East-West 0-75KHz Plot
    subplot('position', [0.08 0.5 0.9 0.12]); 
    imagesc(T2, F2, log(abs(S2)) ); 
    set(gca,'YDir', 'normal');
    colorbar;
    caxis(colorRange);
    axis([0 timeSerries(end) 0 75000]);
    set(gca,'xtick',[])
    set(gca,'xticklabel',[])
    set(gca,'YTick',upperVectorValues);
    set(gca,'YTickLabel',upperVectorLabels);
    title('East-West');
        
    %East-West 0-10KHz Plot
    subplot('position', [0.08 0.36 0.9 0.12]);
    imagesc(T2, F2, log(abs(S2)) ); 
    set(gca,'YDir', 'normal');
    colorbar;
    caxis(colorRange);
    axis([0 timeSerries(end) 0 10000]);
    set(gca,'YTick',lowerVectorValues);
    set(gca,'YTickLabel',lowerVectorLabels);
    xlabel('Time (Seconds)');
    
    %Time serries North-South
    subplot('position', [0.08 0.2 0.815 0.05]);
    plot(timeSerries, Chan1);
    title('North-South');
    axis([0 timeSerries(end) -5000 5000]);
    set(gca,'xtick',[])
    set(gca,'xticklabel',[])
    ylabel('Amplitude');
    
    %Time serries East-West
    subplot('position', [0.08 0.1 0.815 0.05]);
    plot(timeSerries, Chan2);
    title('East-West')
    axis([0 timeSerries(end) -5000 5000]);
    xlabel('Time (Seconds)');
    
    %set plot size
    set(gcf, 'Position', [0 0 600.0 600.0]);
    set(gcf, 'PaperUnits', 'inches', 'PaperSize', [8.0 5.6], 'PaperPosition', [0 0 8 5.6]);
    
    break
    %Save said plots
    print(gcf, summaryPlotName, '-dpng', '-r150'); 
    
    %Close the plots to prevent memory leaks
    clf;
    close('all');
    
end

%We now conclude this script, thank you for your time.
%We know you have a choice in your scripts and we thank you for your patron