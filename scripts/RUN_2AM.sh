#!/bin/sh
DD=$(date +%d)

cd isuag
sh run_plots.sh
if [ $DD -eq "17" ]
	then
		python nmp_monthly_email.py
fi

# Run the climodat estimator to get sites that are valid at midnight
# only for Iowa at the moment as we have no other such sites outside of
# Iowa
cd ../climodat
python daily_estimator.py IA

cd ../climodat
sh run.sh &

cd ../coop
python hrrr_solarrad.py
if [ $DD -eq "01" ]
	then
	python first_guess_for_harry.py
fi

cd ../util
if [ $DD -eq "02" ]
	then
		sh monthly.sh $(date --date '3 days ago' +'%y %m')
fi

cd ../dl
python download_cfs.py &

cd ../cache
python warn_cache.py &

cd ../dbutil
python clean_afos.py
python compute_hads_sts.py
python clean_unknown_hads.py
python unknown_stations.py

cd ../ingestors/cocorahs
python redo_day.py IA

cd ../ncdc
if [ $DD -eq "15" ]
	then
	python ingest_fisherporter.py $(date --date '90 days ago' +'%Y %m')
	python ingest_fisherporter.py $(date --date '180 days ago' +'%Y %m')
	python ingest_fisherporter.py $(date --date '360 days ago' +'%Y %m')
fi


cd ../asos_1minute
if [ $DD -eq "09" ]
then
	python parse_ncdc_asos1minute.py
fi


cd ../../windrose
python daily_drive_network.py

cd ../prism
python ingest_prism.py $(date --date '7 days ago' +'%Y %m %d')
python ingest_prism.py $(date --date '60 days ago' +'%Y %m %d')
python ingest_prism.py $(date --date '90 days ago' +'%Y %m %d')
