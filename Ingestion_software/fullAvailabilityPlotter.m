size = 124;  % number of elements in the matrix curently 4/day so 124 entries across
step = 4; % The day is divided into 4 sections
avaliablityMatrix = zeros(5,size);
siteIDs = ['atha';'cmrs';'pina';'barr';'fsmi'];
siteIDs = cellstr(siteIDs);
rootDir = '/data/vlf/summaryPlots';

%matricies index for the days
index = 1:step:size;

years = [2014];  % Make sure this is correct before proceding
months = 1:1:12;

for y=1:length(years)
    %Convery year to a string
    Year = num2str(years(y));
    for m=1:length(months)
        %Convert the month to a 0 padded string
        Month = ['0' num2str(months(m))];
        Month = Month(end-1:end);
        monthDir = [rootDir '/' Year '/' Month];
        
        %check to see if the month directory exists
        if exist(monthDir, 'dir') == 0
            continue
        end
        %set the file name
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
        set(gcf, 'PaperUnits', 'inches', 'PaperSize', [10.0 7.1], 'PaperPosition', [0 0 10.0 7.1]);

        title([Year '-' Month ' Availability Chart']);
        xlabel('Day');
        ylabel('Site');

        %Save the plot
        print(gcf, fileName, '-dpng', '-r250'); 

        %Close the plots to prevent memory leaks
        clf;
        close('all');
            
    end
end
