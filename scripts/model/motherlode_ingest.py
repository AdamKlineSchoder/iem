"""
 Mine grid point extracted values for our good and the good of the IEM
 Use Unidata's motherlode server :)

"""
from __future__ import print_function
import sys
from io import StringIO
import datetime

import requests
import pytz
import pandas as pd
from pyiem.network import Table as NetworkTable
from pyiem.util import get_dbconn

NT = NetworkTable(['AWOS', 'IA_ASOS'])

BASE_URL = "http://thredds-jetstream.unidata.ucar.edu/thredds/ncss/grib/NCEP/"
BASE_URL2 = "http://thredds.ucar.edu/thredds/ncss/grib/NCEP/"
URLS = {'NAM': ("NAM/CONUS_12km/conduit/"
                "NAM_CONUS_12km_conduit_%Y%m%d_%H00.grib2/GC"),
        'GFS': "GFS/Global_0p5deg/GFS_Global_0p5deg_%Y%m%d_%H00.grib2/GC",
        'RAP': "RAP/CONUS_13km/RR_CONUS_13km_%Y%m%d_%H00.grib2/GC",
        }
VLOOKUP = {
 'sbcape': {'NAM': 'Convective_available_potential_energy_surface',
            'GFS': 'Convective_available_potential_energy_surface',
            'RAP': 'Convective_available_potential_energy_surface'},
 'sbcin': {'NAM': 'Convective_inhibition_surface',
           'GFS': 'Convective_inhibition_surface',
           'RAP': 'Convective_inhibition_surface'},
 'pwater': {'NAM': 'Precipitable_water_entire_atmosphere_single_layer',
            'GFS': 'Precipitable_water_entire_atmosphere_single_layer',
            'RAP': 'Precipitable_water_entire_atmosphere_single_layer'},
 'precipcon': {'RAP':
               'Convective_precipitation_surface_1_Hour_Accumulation',
               'NAM': 'Convective_precipitation_surface_3_Hour_Accumulation',
               'GFS':
               'Convective_precipitation_surface_Mixed_intervals_Accumulation',
               },
 'precip': {'RAP': 'Total_precipitation_surface_1_Hour_Accumulation',
            'NAM': 'Total_precipitation_surface_3_Hour_Accumulation',
            'GFS': 'Total_precipitation_surface_Mixed_intervals_Accumulation',
            }
           }


def xref(row, varname, model):
    """Safer lookup"""
    rowkey = VLOOKUP[varname][model]
    if rowkey not in row:
        print(("motherload_ingest failed to find %s in %s\nrow:%s"
               ) % (varname, model, row))
        sys.exit()
    return row[rowkey]


def run(mcursor, model, station, lon, lat, ts):
    """
    Ingest the model data for a given Model, stationid and timestamp
    """

    vstring = ""
    for v in VLOOKUP:
        if VLOOKUP[v][model] is not None:
            vstring += "var=%s&" % (VLOOKUP[v][model],)

    url = ("%s%s?%slatitude=%s&longitude=%s&temporal=all&vertCoord="
           "&accept=csv&point=true"
           ) % ((BASE_URL
                 if (datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) -
                     ts).total_seconds() < 86400
                 else BASE_URL2), ts.strftime(URLS[model]),
                vstring, lat, lon)
    try:
        fp = requests.get(url, timeout=120)
        if fp.status_code == 404:
            print("motherlode_ingest grid %s %s missing" % (model, ts))
            return 0
        sio = StringIO(fp.text)
    except Exception as exp:
        print(exp)
        print(url)
        print(('FAIL ts: %s station: %s model: %s'
               ) % (ts.strftime("%Y-%m-%d %H"), station, model))
        return

    table = "model_gridpoint_%s" % (ts.year,)
    sql = """
        DELETE from """ + table + """ WHERE
        station = %s and model = %s and runtime = %s
        """
    args = (station, model, ts)
    mcursor.execute(sql, args)
    if mcursor.rowcount > 0:
        print('Deleted %s rows for ts: %s station: %s model: %s' % (
                        mcursor.rowcount, ts, station, model))

    count = 0
    sio.seek(0)
    df = pd.read_csv(sio)
    for _, row in df.iterrows():
        for k in row.keys():
            row[k[:k.find("[")]] = row[k]
        sbcape = xref(row, 'sbcape', model)
        sbcin = xref(row, 'sbcin', model)
        pwater = xref(row, 'pwater', model)
        precipcon = xref(row, 'precipcon', model)
        precip = xref(row, 'precip', model)
        if precip < 0:
            precip = None
        if precipcon < 0:
            precipcon = None
        fts = datetime.datetime.strptime(row['time'], '%Y-%m-%dT%H:%M:%SZ')
        fts = fts.replace(tzinfo=pytz.utc)
        sql = """INSERT into """ + table + """ (station, model, runtime,
              ftime, sbcape, sbcin, pwater, precipcon, precip)
              VALUES (%s, %s , %s,
              %s, %s, %s, %s, %s, %s )"""
        args = (station, model, ts, fts, sbcape, sbcin, pwater, precipcon,
                precip)
        mcursor.execute(sql, args)
        count += 1
    return count


def run_model(mcursor, model, runtime):
    """Actually do a model and timestamp"""
    for sid in NT.sts:
        cnt = run(mcursor, model, "K"+sid,
                  NT.sts[sid]['lon'], NT.sts[sid]['lat'], runtime)
        if cnt == 0:
            print('No data K%s %s %s' % (sid, runtime, model))


def check_and_run(mcursor, model, runtime):
    ''' Check the database for missing data '''
    table = "model_gridpoint_%s" % (runtime.year,)
    mcursor.execute("""
        SELECT * from """+table+""" WHERE
        runtime = %s and model = %s
    """, (runtime, model))
    if mcursor.rowcount < 10:
        print(('Rerunning %s [runtime=%s] due to rowcount %s'
               ) % (model, runtime, mcursor.rowcount))
        run_model(mcursor, model, runtime)


def main(argv):
    """Do Something"""
    pgconn = get_dbconn('mos')
    mcursor = pgconn.cursor()
    gts = datetime.datetime.utcnow()
    if len(argv) == 5:
        gts = datetime.datetime(int(argv[1]), int(argv[2]),
                                int(argv[3]), int(argv[4]))
    gts = gts.replace(tzinfo=pytz.utc, minute=0, second=0,
                      microsecond=0)

    if gts.hour % 6 == 0:
        ts = gts - datetime.timedelta(hours=6)
        for model in ['GFS', 'NAM']:
            run_model(mcursor, model, ts)
            check_and_run(mcursor, model, ts - datetime.timedelta(days=7))

    ts = gts - datetime.timedelta(hours=2)
    run_model(mcursor, "RAP", ts)
    check_and_run(mcursor, 'RAP', ts - datetime.timedelta(days=7))
    mcursor.close()
    pgconn.commit()
    pgconn.close()


if __name__ == '__main__':
    # Go Go gadget
    main(sys.argv)
