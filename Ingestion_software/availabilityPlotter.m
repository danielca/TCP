%Avaliability Plotter
%Created: 28 OCT 2014
%Author: Casey Daniel
%
% Version 0.0.1
%
% This script is to create the avaliabiltiy charts. This will make the
% charts bassed upon the current date, and create it for the entire month
%
% A quick note, this script does not check to see if one currently exists
% as it will update the file for the data curently avaliable.
%
% Changelog:
%   -N/A
size = 124;
step = 4;
avaliablityMatrix = zeros(5,size);
siteIDs = ['atha';'cmrs';'pina';'barr';'smth'];
siteIDs = cellstr(siteIDs);
rootDir = '/data/vlf/summaryPlots';
%rootDir = '/Users/Casey/Desktop/summaryPlots'; % test directory


%matricies index for the days
index = 1:step:size;

%get the month and year
Date = clock;
Year = Date(1);
Month = Date(2);

%0 pad the month and make the year a string
Year = num2str(Year);
Month = ['0' num2str(Month)];
Month = Month(end-1:end);

fileName = [rootDir,'/',Year,'/',Month,'/',Year,'-',Month,'-availability.png'];

for i=1:31 
    for k = 1:length(siteIDs)
        foundDirs = 0;
        for j = 0:5
            hour = ['0' int2str(j)];
            hour = hour(end-1:end);
            day = ['0' num2str(i)];
            day = day(end-1:end);
            dir = [rootDir '/' Year '/' Month '/' day '/' char(siteIDs(k)) '/' hour];
            if exist(dir, 'dir') == 7
                foundDirs = foundDirs + 1;
            end
        end
        if foundDirs > 5
            avaliablityMatrix(k, (index(i))) = 2;
        end
        if foundDirs < 6 && foundDirs > 0
            avaliablityMatrix(k, (index(i))) = 1;
        end
        
        %Check durring the day (hours 6-11)
        foundDirs = 0;
        for j = 6:11
            hour = ['0' int2str(j)];
            hour = hour(end-1:end);
            day = ['0' num2str(i)];
            day = day(end-1:end);
            dir = [rootDir '/' Year '/' Month '/' day '/' char(siteIDs(k)) '/' hour];
            if exist(dir, 'dir') == 7
                foundDirs = foundDirs + 1;
            end
        end
        if foundDirs > 5
            avaliablityMatrix(k, (index(i) + 1)) = 2;
        end
        if foundDirs < 6 && foundDirs > 0
            avaliablityMatrix(k, (index(i) + 1)) = 1;
        end
        
        %Check afternoon (hours 12-17)
        foundDirs = 0;
        for j = 12:17
            hour = ['0' int2str(j)];
            hour = hour(end-1:end);
            day = ['0' num2str(i)];
            day = day(end-1:end);
            dir = [rootDir '/' Year '/' Month '/' day '/' char(siteIDs(k)) '/' hour];
            if exist(dir, 'dir') == 7
                foundDirs = foundDirs + 1;
            end
        end
        if foundDirs > 5
            avaliablityMatrix(k, (index(i) + 2)) = 2;
        end
        if foundDirs < 6 && foundDirs > 0
            avaliablityMatrix(k, (index(i) + 2)) = 1;
        end
        
        %Check the evening (Hours 18-23)
        foundDirs = 0;
        for j = 18:23
            hour = ['0' int2str(j)];
            hour = hour(end-1:end);
            day = ['0' num2str(i)];
            day = day(end-1:end);
            dir = [rootDir '/' Year '/' Month '/' day '/' char(siteIDs(k)) '/' hour];
            if exist(dir, 'dir') == 7
                foundDirs = foundDirs + 1;
            end
        end
        if foundDirs > 5
            avaliablityMatrix(k, (index(i) + 3)) = 2;
        end
        if foundDirs < 6 && foundDirs > 0
            avaliablityMatrix(k, (index(i) + 3)) = 1;
        end
        foundDirs = 0;
        
    end
end

set(gcf, 'Visible', 'off');
set(gca, 'FontSize', 10, 'fontWeight', 'bold');
set(findall(gcf,'type','text'),'FontSize',10, 'fontWeight', 'bold');

imagesc(avaliablityMatrix);

XTicksLabels = linspace(1,31,31);
XTickPos = (1:step:size)-0.5;
map=transpose([ zeros(1,32)+1 1:-1./31:0 ; 0:1./31:1 zeros(1,32)+1 ; zeros(1,64)]);
colormap(map)
caxis([0 2]);

%set various options
set(gca, 'xticklabel', XTicksLabels);
set(gca, 'xtick', XTickPos);
set(gca, 'yticklabel', ['atha';'cmrs';'pina';'barr';'smth']);
set(gca, 'ytick', [0.5,1.5,2.5,3.5,4.5]);
set(gca, 'GridLineStyle', '-', 'LineWidth', 2);
set(gca, 'xgrid', 'on');
set(gca, 'ygrid', 'on');
set(gcf, 'Position', [0 0 600.0 600.0]);
set(gcf, 'PaperUnits', 'inches', 'PaperSize', [8 5.6], 'PaperPosition', [0 0 8 5.6]);

title([Year '-' Month ' Availability Chart']);
xlabel('Day');
ylabel('Site');

%Save the plot
print(gcf, fileName, '-dpng', '-r150'); 
    
%Close the plots to prevent memory leaks
clf;
close('all');