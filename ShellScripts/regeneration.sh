!#/bin/bash

mv /data/vlf/src/Ingestion_software/abailabilityPlotter.m /data/vlf/src/
mv /data/vlf/src/Ingestion_software/plot_maker.m /data/vlf/src/

/usr/local/MATLAB/R2014a/bin/matlab -nodisplay -nodesktop -nojvm -singlCompthread -r "run /data/vlf/src/Ingestion_software/full_plot_maker.m"
/usr/local/MATLAB/R2014a/bin/matlab -nodisplay -nodesktop -nojvm -singlCompthread -r "run /data/vlf/src/Ingestion_software/fullAvailabilityPlotter.m"

mv /data/vlf/src/abailabilityPlotter.m /data/vlf/src/Ingestion_software
mv /data/vlf/src/plot_maker.m /data/vlf/src/Ingestion_software/
