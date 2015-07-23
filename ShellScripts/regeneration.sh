!#/bin/bash

mv /data/vlf/src/Ingestion_software/abailabilityPlotter.m /data/vlf/src/
mv /data/vlf/src/Ingestion_software/plot_maker.m /data/vlf/src/

/data/vlf/MATLAB/R2014b/bin/matlab -nodisplay -nodesktop -r "run /data/vlf/src/Ingestion_software/full_plot_maker.m"
/data/vlf/MATLAB/R2014b/bin/matlab -nodisplay -nodesktop -r "run /data/vlf/src/Ingestion_software/fullAvailabilityPlotter.m"

mv /data/vlf/src/abailabilityPlotter.m /data/vlf/src/Ingestion_software
mv /data/vlf/src/plot_maker.m /data/vlf/src/Ingestion_software/
