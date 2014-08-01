function [Chan1, Chan2] = FFTFilter(Chan1, Chan2, Fs, NoiseFreqs, Bandwidth)
    %UNTITLED3 Summary of this function goes here
    %   Detailed explanation goes here

    %Compute theDFTs
    FFT1 = fft(Chan1);
    FFT2 = fft(Chan2);
    Bandwidth = Bandwidth/2; % Divide by 2 to loop over each side of the peak

    %Loop over the desginated noise frequencies
    for i=1:length(NoiseFreqs)
        %Find the position of the freqency
        pos = round(NoiseFreqs(i)*(length(Chan1)/Fs));
        %iniliaze amplitude vector
        amplitudes = zeros(1,11);
        
        %Gather the amplitudes of the bins
        for j=pos-5:pos+5
            amplitudes(j) = abs(FFT1(j));
        end
        
        %Find the max index of the amplitudes
        [~, index] = max(amplitudes);
        peakPos = pos-10+index;
        
        %Loop over the bins centerd at the peak and replace them with zero
        %As well as the conjugate bins
        for j=peakPos-Bandwidth:peakPos+Bandwidth
            FFT1(j) = 0;
            FFT1(length(FFT1)-j) = 0;
            FFT2(j) = 0;
            FFT2(length(FFT2)-j) = 0;
        end

    end
    %Create the new signals
    Chan1 = ifft(FFT1);
    Chan2 = ifft(FFT2);
end



