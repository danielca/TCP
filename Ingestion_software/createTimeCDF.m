function [] = createTimeCDF( CDFFilePath, CDFFileName, Chan1, Chan2, headerSplit )
%UNTITLED2 Create CDF Files of the given Data
%   Detailed explanation goes here
    
    cdfid = cdflib.create([CDFFilePath '/' CDFFileName]);
    %Assign the attributes
    %See http://spdf.gsfc.nasa.gov/istp_guide/gattributes.html For 
    %Informaiton on the attributes
    Source_name = cdflib.createAttr(cdfid,'Source_name','global_scope');
    cdflib.putAttrgEntry(cdfid, Source_name,0,'CDF_CHAR', 'ABV>ABOVE Ground Bassed Observatory');
    Mission_group = cdflib.createAttr(cdfid,'Mission_group','global_scope');
    cdflib.putAttrgEntry(cdfid,Mission_group,0, 'CDF_CHAR', 'Ground-Bassed Investigations');
    %PUT LOGIC HERE FOR LOGICAL SOURCE ABOUT SITES AND DATES
    siteFullName = '';
    siteShortName = headerSplit(7);
    if strcmp(siteShortName,'barr')
        siteFullName = 'Barrier Lake, Alberta, Lat: 51.01, Lon: -115.05';
    elseif strcmp(siteShortName, 'cmrs')
        siteFullName = 'Camrose, Alberta Lat: 53.08, Long: -112.54';
    elseif strcmp(siteShortName,'atha')
        siteFullName = 'Athabasca, Alberta, Lat: 54.60, Lon: -113.65';
    elseif strcmp(siteShortName,'pina')
        siteFullName = 'Pinawa, Manitoba, Lat: 50.16, Lon: -96.08';
    elseif strcmp(siteShortName,'fsmi')
        siteFullName = 'Fort Smith, Manitoba, Lat: 59.99, Lon: -111.84';
    else
        siteFullName = 'Test';

    end
    

    logicalSrc = cdflib.createAttr(cdfid, 'Logical_source', 'global_scope');
    cdflib.putAttrgEntry(cdfid,logicalSrc,0, 'CDF_CHAR', strcat('abv_l1_tseries_', siteShortName{1,1}));
    logcialSrcDesc = cdflib.createAttr(cdfid, 'Logical_source_description', 'global_scope');
    cdflib.putAttrgEntry(cdfid,logcialSrcDesc, 0,'CDF_CHAR', strcat('ABOVE Full resolution timeseries, 0.2-75kHz magnetif field at ', siteFullName));
    logicalFile = cdflib.createAttr(cdfid, 'Logical_file_id', 'global_scope');
    cdflib.putAttrgEntry(cdfid,logicalFile,0,'CDF_CHAR', CDFFileName(1:end-4));

    project = cdflib.createAttr(cdfid, 'Project', 'global_scope');
    cdflib.putAttrgEntry(cdfid,project,0,'CDF_CHAR', 'ABOVE');
    discipline = cdflib.createAttr(cdfid, 'Discipline', 'global_scope');
    cdflib.putAttrgEntry(cdfid,discipline,0,'CDF_CHAR','Space Physics>Magnetospheric Science, Space Physics>Lonospheric Science');
    dataType = cdflib.createAttr(cdfid, 'Data_type', 'global_scope');
    cdflib.putAttrgEntry(cdfid, dataType,0, 'CDF_CHAR', 'raw');
    dataVersion = cdflib.createAttr(cdfid, 'Data_version', 'global_scope');
    cdflib.putAttrgEntry(cdfid,dataVersion,0,'CDF_CHAR','1');
    PIName = cdflib.createAttr(cdfid, 'PI_name','global_scope');
    cdflib.putAttrgEntry(cdfid, PIName,0,'CDF_CHAR','C. Cully');
    PIA = cdflib.createAttr(cdfid, 'PI_affiliation','global_scope');
    cdflib.putAttrgEntry(cdfid, PIA,0,'CDF_CHAR','University of Calgary');
    text = cdflib.createAttr(cdfid, 'TEXT', 'global_scope');
    cdflib.putAttrgEntry(cdfid,text,0,'CDF_CHAR','Time series VLF Ground Bassed Observation');
    instrumentType = cdflib.createAttr(cdfid, 'Instrument_type', 'global_scope');
    cdflib.putAttrgEntry(cdfid,instrumentType,0,'CDF_CHAR', 'Ground Based VLF Reciever');
    genBy = cdflib.createAttr(cdfid, 'Generated_by', 'global_scope');
    cdflib.putAttrgEntry(cdfid,genBy,0,'CDF_CHAR','ABOVE');
    mod = cdflib.createAttr(cdfid, 'MODS', 'global_scope');
    cdflib.putAttrgEntry(cdfid,mod,0,'CDF_CHAR',' ');
    linkTxt = cdflib.createAttr(cdfid, 'LINK_TEXT','global_scope');
    cdflib.putAttrgEntry(cdfid,linkTxt,0,'CDF_CHAR','Data Avaliable from ABOVE Main Page');
    linkTitle = cdflib.createAttr(cdfid, 'LINK_TITLE','global_scope');
    cdflib.putAttrgEntry(cdfid,linkTitle,0,'CDF_CHAR','Above Main Page');
    link = cdflib.createAttr(cdfid, 'HTTP_LINK','global_scope');
    cdflib.putAttrgEntry(cdfid, link, 0, 'CDF_CHAR','http://www.ucalgary.ca/above/');
    ack = cdflib.createAttr(cdfid, 'Acknowledgement','global_scope');
    cdflib.putAttrgEntry(cdfid,ack,0,'CDF_CHAR', 'Please include the following in any publications using this data: Infrastructure funding for ABOVE is provided by the Canada Foundation for Innovation and the province of Alberta. ABOVE data used in this work was collected with the support of the Canadian Space Agencys Geospace Observatory (GO Canada) contribution initiative.');

    
    desc = cdflib.createAttr(cdfid, 'Descriptor', 'global_scope');
    cdflib.putAttrgEntry(cdfid, desc, 0, 'CDF_CHAR', char(strcat(siteShortName, '>', siteFullName, ',Canada')));
    rules = cdflib.createAttr(cdfid, 'Rules_of_use', 'global_scope');
    cdflib.putAttrgEntry(cdfid, rules, 0, 'CDF_CHAR', 'Open Data for Scientific Use');
    
    
    %Now on with the actual Data 
    %For the first trick, the time array!
    Date = headerSplit(1);
    Date = Date{1,1};
    Year = str2double(['20' Date(5:6)]);
    Month = str2double(Date(3:4));
    Day = str2double(Date(1:2));
    TimeStamp = headerSplit(2);
    TimeStamp = TimeStamp{1,1};
    Hour = str2double(TimeStamp(1:2));
    Min = str2double(TimeStamp(3:4));
    Sec = str2double(TimeStamp(5:6));
    %Maybe fix to 0 sec?
    Mili = TimeStamp(8:end);
    if isempty(Mili)
        Mili = 0;
    else
        Mili = str2double(Mili);
    end

    Micro = 0;
    Nano = 0;
    
    %NOTE: EPOCH ARRAY ASSUMES THE SAMPLE TIME WILL REMAIN ONE SECOND LONG
    timeVec =  [Year; Month; Day; Hour; Min; Sec; Mili; Micro; Nano; 0];
    baseTime = cdflib.computeEpoch16(timeVec);
    partialSeconds = 0:6666666:(6666666*(149999));
    partialSeconds(size(partialSeconds)) = baseTime(2);
    epochs = ones(1,150000) * baseTime(1);
    epochs(size(epochs)) = baseTime(1) + 1;
    epochArr = [epochs; partialSeconds];

    
    
    %Write the Data to the CDF
    
    chanVar = cdflib.createVar(cdfid, 'abv_raw', 'CDF_INT2', 1, 2, true, true);
    cdflib.hyperPutVarData(cdfid, chanVar, [0 length(Chan1) 1], {0, 2, 1}, [int16(Chan1); int16(Chan2)]);
    
    timeVar = cdflib.createVar(cdfid, 'abv_raw_epoch', 'CDF_EPOCH16',1, [],true, []);
    cdflib.hyperPutVarData(cdfid, timeVar, [0 length(Chan1) 1], {0, 1, 1}, epochArr);

    comp = cdflib.createVar(cdfid, 'abv_raw_compno', 'CDF_UINT1', 1, 2, false, true);
    cdflib.hyperPutVarData(cdfid, comp, [0 1 1], {0, 2, 1}, uint8([1;2]));
    label = [char(strcat('Uncalibrated B (', siteShortName, ' NS)')) char(strcat('Uncalibrated B (', siteShortName, ' EW)'))];
    labelVar = cdflib.createVar(cdfid, 'abv_raw_labl', 'CDF_CHAR', 24, 2, false, true);
    cdflib.hyperPutVarData(cdfid, labelVar, [0, 1, 1], {0,2,1}, label)
    
    %Clockspeed and Sample Rate
    measuredClkSpeed = headerSplit(14);
    measuredClkSpeed = str2double(measuredClkSpeed{1,1});
    roundValue = round(measuredClkSpeed/100e6);
    measuredClckSpeed = measuredClkSpeed/roundValue;
    measuredSampleRate = headerSplit(16);
    measuredSampleRate = str2double(measuredSampleRate{1,1});
    
    clckSpeed = cdflib.createVar(cdfid, 'ClockSpeed', 'CDF_INT4', 1, [], true, []);
    cdflib.putVarData(cdfid, clckSpeed, 0, [], int32(measuredClkSpeed));
    
    sampleRate = cdflib.createVar(cdfid, 'SampleRate', 'CDF_INT4', 1, [], true, []);
    cdflib.putVarData(cdfid, sampleRate, 0, [], int32(measuredSampleRate));
    

    %And were back to more meta-data
    %Create the attributes
    
    units = cdflib.createAttr(cdfid, 'UNITS', 'variable_scope');
    label = cdflib.createAttr(cdfid, 'LABL_PTR_1', 'variable_scope');
    format = cdflib.createAttr(cdfid, 'FORMAT', 'variable_scope');
    fill = cdflib.createAttr(cdfid, 'FILLVAL', 'variable_scope');
    feildNam = cdflib.createAttr(cdfid, 'FIELDNAM', 'variable_scope');
    display = cdflib.createAttr(cdfid, 'DISPLAY_TYPE', 'variable_scope');
    dep2 = cdflib.createAttr(cdfid, 'DEPEND_2', 'variable_scope');
    dep3 = cdflib.createAttr(cdfid, 'DEPEND_3', 'variable_scope');
    dep1 = cdflib.createAttr(cdfid, 'DEPEND_1', 'variable_scope');
    dep0 = cdflib.createAttr(cdfid, 'DEPEND_0', 'variable_scope');
    catDesc = cdflib.createAttr(cdfid, 'CATDESC', 'variable_scope');
    notes = cdflib.createAttr(cdfid, 'VAR_NOTES', 'variable_scope');
    validMin = cdflib.createAttr(cdfid, 'VALIDMIN', 'variable_scope');
    validMax = cdflib.createAttr(cdfid, 'VALIDMAX', 'variable_scope');
    varType = cdflib.createAttr(cdfid, 'VAR_TYPE', 'variable_scope');
    axis = cdflib.createAttr(cdfid, 'LABLAXIS', 'variable_scope');
    timeBase = cdflib.createAttr(cdfid, 'TIME_BASE', 'variable_scope');

    %metadata for the Channels
    cdflib.putAttrEntry(cdfid, catDesc, chanVar, 'CDF_CHAR','Uncalibrated timeseries of ELF/VLF (300 Hz-75 kHz) magnetic field at ATHA.');
    %cdflib.putAttrEntry(cdfid, dep0, chanVar, 'CDF_CHAR', 'Epoch');
    cdflib.putAttrEntry(cdfid, dep0, chanVar, 'CDF_CHAR', 'abv_raw_epoch');
    cdflib.putAttrEntry(cdfid, dep1, chanVar, 'CDF_CHAR', 'abv_raw_compno');
    cdflib.putAttrEntry(cdfid, display, chanVar, 'CDF_CHAR', 'time_series');
    cdflib.putAttrEntry(cdfid, feildNam, chanVar, 'CDF_CHAR', 'Uncalibrated B (ATHA)');
    cdflib.putAttrEntry(cdfid, fill, chanVar, 'CDF_INT2', int16(-1.0E31));
    cdflib.putAttrEntry(cdfid, format, chanVar, 'CDF_CHAR', 'I8');
    cdflib.putAttrEntry(cdfid, label, chanVar, 'CDF_CHAR', 'abv_raw_labl');
    cdflib.putAttrEntry(cdfid, units, chanVar, 'CDF_CHAR', 'ADC');
    cdflib.putAttrEntry(cdfid, validMax, chanVar, 'CDF_INT2', [int16(32768); int16(32768)]);
    cdflib.putAttrEntry(cdfid, validMin, chanVar, 'CDF_INT2', [int16(-32768); int16(-32768)]);
    cdflib.putAttrEntry(cdfid, notes, chanVar, 'CDF_CHAR', 'Antennas are aligned to magnetic North-South and magnetic East-West. Both components are included in the file.');
    cdflib.putAttrEntry(cdfid, varType, chanVar, 'CDF_CHAR', 'data');

    %Label metadata
    cdflib.putAttrEntry(cdfid, catDesc, labelVar, 'CDF_CHAR', 'abv_raw_labl');
    cdflib.putAttrEntry(cdfid, feildNam, labelVar, 'CDF_CHAR', 'abv_raw_labl');
    cdflib.putAttrEntry(cdfid, varType, labelVar, 'CDF_CHAR', 'metadata');
    cdflib.putAttrEntry(cdfid, format, labelVar, 'CDF_CHAR', 'A');

    %Component metadata
    cdflib.putAttrEntry(cdfid, catDesc, comp, 'CDF_CHAR', 'abv_raw_compno');
    cdflib.putAttrEntry(cdfid, feildNam, comp, 'CDF_CHAR', 'abv_raw_compno');
    cdflib.putAttrEntry(cdfid, varType, comp, 'CDF_CHAR', 'metadata');
    cdflib.putAttrEntry(cdfid, format, comp, 'CDF_CHAR', 'I1');
    cdflib.putAttrEntry(cdfid, validMin, comp, 'CDF_UINT1', uint8(0));
    cdflib.putAttrEntry(cdfid, validMax, comp, 'CDF_UINT1', uint8(3));
    
    %epoch array metadata
    cdflib.putAttrEntry(cdfid, catDesc, timeVar, 'CDF_CHAR', 'abv_raw_epoch');
    cdflib.putAttrEntry(cdfid, feildNam, timeVar, 'CDF_CHAR', 'abv_raw_epoch');
    cdflib.putAttrEntry(cdfid, units, timeVar, 'CDF_CHAR', 'ns');
    cdflib.putAttrEntry(cdfid, axis, timeVar, 'CDF_CHAR', 'UT')
    cdflib.putAttrEntry(cdfid, varType, timeVar, 'CDF_CHAR', 'support_data');
    cdflib.putAttrEntry(cdfid, validMax, timeVar, 'CDF_EPOCH16', cdflib.computeEpoch16([2100; 12; 31; 23; 59; 59; 999; 999; 999; 999]));
    cdflib.putAttrEntry(cdfid, validMin, timeVar, 'CDF_EPOCH16', cdflib.computeEpoch16([2001; 01; 01; 00; 00; 00; 000; 000; 000; 000]));
    cdflib.putAttrEntry(cdfid, fill, timeVar, 'CDF_EPOCH16', [-1.0E31, -1.0E31]);
    cdflib.putAttrEntry(cdfid, timeBase, timeVar, 'CDF_CHAR', '0 AD');
    
    
    %Sample rage metadata
    cdflib.putAttrEntry(cdfid, catDesc, sampleRate, 'CDF_CHAR', 'Number of samples per second');
    cdflib.putAttrEntry(cdfid, varType, sampleRate, 'CDF_CHAR', 'metadata');
    cdflib.putAttrEntry(cdfid, feildNam, sampleRate, 'CDF_CHAR', 'Number of samples per second');
    cdflib.putAttrEntry(cdfid, format, sampleRate, 'CDF_CHAR', 'I16');
    cdflib.putAttrEntry(cdfid, validMin, sampleRate, 'CDF_INT4', int32(0));
    cdflib.putAttrEntry(cdfid, validMax, sampleRate, 'CDF_INT4', int32(1.0E31));
    cdflib.putAttrEntry(cdfid, fill, sampleRate, 'CDF_INT4', int32(-1.0E31));
    
    %Clk Speed metadata
    cdflib.putAttrEntry(cdfid, catDesc, clckSpeed, 'CDF_CHAR', 'Number of clocks per sample');
    cdflib.putAttrEntry(cdfid, varType, clckSpeed, 'CDF_CHAR', 'metadata');
    cdflib.putAttrEntry(cdfid, feildNam, clckSpeed, 'CDF_CHAR', 'Number of clocks per sample');
    cdflib.putAttrEntry(cdfid, format, clckSpeed, 'CDF_CHAR', 'I16');
    cdflib.putAttrEntry(cdfid, validMin, clckSpeed, 'CDF_INT4', int32(0));
    cdflib.putAttrEntry(cdfid, validMax, clckSpeed, 'CDF_INT4', int32(1.0E31));
    cdflib.putAttrEntry(cdfid, fill, clckSpeed, 'CDF_INT4', int32(-1.0E31));
    
    cdflib.close(cdfid);
    clear cdfid

end


