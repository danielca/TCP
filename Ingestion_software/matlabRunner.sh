#!/usr/bin/tcsh

setenv USER above
setenv LOGNAME plotmaker
setenv HOME /data/vlf
setenv PATH /data/vfl
setenv LANG en_US.UTF-8

matlab -nodisplay -nodesktop -r "run /usr/local/src/above/Ingestion_software/plot_maker.m"