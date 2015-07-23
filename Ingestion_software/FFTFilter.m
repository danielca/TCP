function [Chan1, Chan2] = FFTFilter(Chan1, Chan2, sampleFreq, NoiseFreqs, Bandwidth)
    %FFT Filter
    %   Version: 1.0.0
    %   Created by: Casey Daniel
    %   Date: 12 Aug 2014
    %   This function takes Channel 1 and 2 and removes the frequencies
    %   found in NoiseFreqs and removes the number of bins in Bandwidth
    %   centered at the peak of the frequency. 
    %   A peak search is also preformed to ensure that the peak is being
    %   Removed.
    
    
    %Compute theDFTs
    FFT1 = fft(Chan1);
    FFT2 = fft(Chan2);
    Bandwidth = Bandwidth/2; % Divide by 2 to loop over each side of the peak

    %Loop over the desginated noise frequencies
    for i=1:length(NoiseFreqs)
        %Find the position of the freqency
        pos = round(NoiseFreqs(i)*(length(Chan1)/sampleFreq));
        %iniliaze amplitude vector
        amplitudes = zeros(1,11);
        
        %Gather the amplitudes of the bins
        if pos-5 > 6
            for j=pos-5:pos+5
                amplitudes(j) = abs(FFT1(j));
            end
        else
            for j=1:10
                amplitudes(j) = abs(FFT1(j));
            end
        end
        
        %Find the max index of the amplitudes
        [~, index] = max(amplitudes);
        peakPos = pos-10+index;
        
        %Loop over the bins centerd at the peak and replace them with zero
        %As well as the conjugate bins
        if peakPos-Bandwidth > 1
            for j=peakPos-Bandwidth:peakPos+Bandwidth
                FFT1(j) = 0;
                FFT1(length(FFT1)-j+2) = 0;
                FFT2(j) = 0;
                FFT2(length(FFT2)-j+2) = 0;
            end
        else
            for j=1:peakPos+Bandwidth
                FFT1(j) = 0;
                FFT1(length(FFT1)-j+2) = 0;
                FFT2(j) = 0;
                FFT2(length(FFT2)-j+2) = 0;
            end
        end

    end
    %Create the new signals
    Chan1 = ifft(FFT1);
    Chan2 = ifft(FFT2);
end



