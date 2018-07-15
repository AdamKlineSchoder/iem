# Runs at Midnight CST/CDT
DD=$(date -u +'%d')
MM=$(date -u +'%m')
YYYY=$(date -u +'%Y')

cd qc
python adjust_snet_precip.py

cd ../util
python i5_2_cybox.py &
sleep 30
python autolapses2box.py &

cd ../dbutil
sh save_snet_raw.sh
python asos2archive.py

# Need this done so that certain variables are there for DEP
cd ../asos
python compute_daily.py

# Need this done so that IEMRE daily grids are there for DEP
cd ../iemre
python daily_analysis.py $(date --date '1 day ago' +'%Y %m %d')

cd ../smos
python plot.py 12

# Wait a bit before doing this
sleep 600
cd ../qc
python correct_gusts.py
python check_station_geom.py
python check_vtec_eventids.py
python check_afos_sources.py

cd ../outgoing
python wxc_moon.py

cd ../iemre
python grid_rsds.py

cd ../dbutil 
python hads_delete_dups.py

cd ../hads
python dedup_hml_forecasts.py
python raw2obs.py

cd ../mrms
python create_daily_symlink.py $(date --date '1 day ago' +'%Y %m %d')
python mrms_monthly_plot.py

# Assume we have MERRA data by the 28th each month
if [ $DD -eq "28" ]
then
	cd ../dl
	python fetch_merra.py
	MM=$(date -u --date '1 month ago' +'%m')
	YYYY=$(date -u --date '1 month ago' +'%Y')
	cd ../coop
	python merra_solarrad.py $YYYY $MM
fi

# Process the GHCN dataset
if [ $DD -eq "10" ]
then
	cd ../ingestors/ncdc
	python ingest_ghcn.py ND
	python ingest_ghcn.py SD
	python ingest_ghcn.py NE
	python ingest_ghcn.py MO
	python ingest_ghcn.py IL
	python ingest_ghcn.py WI
	python ingest_ghcn.py MN
	python ingest_ghcn.py MI
	python ingest_ghcn.py IN
	python ingest_ghcn.py OH
	python ingest_ghcn.py KY
fi
