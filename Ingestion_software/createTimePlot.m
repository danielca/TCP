function [] = createTimePlot(Chan1, Chan2, Window, overLap, windowSize, sampleFreq )
%UNTITLED4 Summary of this function goes here
%   Detailed explanation goes here
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


%Save said plots
print(gcf, summaryPlotName, '-dpng', '-r150'); 

%Close the plots to prevent memory leaks
clf;
close('all');

end

