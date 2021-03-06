#!/usr/bin/env python
""" JSON service providing IEMRE data for a given point """
import sys
import os
import cgi
import datetime
import json

import numpy as np
from pyiem import iemre, datatypes
from pyiem.util import ncopen, ssw
import pyiem.prism as prismutil


def myrounder(val, precision):
    """round a float or give back None"""
    if val is None or np.isnan(val) or np.ma.is_masked(val):
        return None
    return round(val, precision)


def main():
    """Do Something Fun!"""
    form = cgi.FieldStorage()
    ts = datetime.datetime.strptime(form.getfirst("date"), "%Y-%m-%d")
    lat = float(form.getfirst("lat"))
    lon = float(form.getfirst("lon"))
    fmt = form.getfirst("format")
    if fmt != 'json':
        ssw("Content-type: text/plain\n\n")
        ssw("ERROR: Service only emits json at this time")
        return

    i, j = iemre.find_ij(lon, lat)
    offset = iemre.daily_offset(ts)

    res = {'data': [], }

    fn = iemre.get_daily_ncname(ts.year)

    ssw('Content-type: application/json\n\n')
    if not os.path.isfile(fn):
        ssw(json.dumps(res))
        sys.exit()

    if i is None or j is None:
        ssw(json.dumps({'error': 'Coordinates outside of domain'}))
        return

    if ts.year > 1980:
        nc = ncopen("/mesonet/data/prism/%s_daily.nc" % (ts.year, ))
        i2, j2 = prismutil.find_ij(lon, lat)
        prism_precip = nc.variables['ppt'][offset, j2, i2] / 25.4
        nc.close()
    else:
        prism_precip = None

    if ts.year > 2010:
        nc = ncopen(iemre.get_daily_mrms_ncname(ts.year))
        j2 = int((lat - iemre.SOUTH) * 100.0)
        i2 = int((lon - iemre.WEST) * 100.0)
        mrms_precip = nc.variables['p01d'][offset, j2, i2] / 25.4
        nc.close()
    else:
        mrms_precip = None

    nc = ncopen(fn)

    c2000 = ts.replace(year=2000)
    coffset = iemre.daily_offset(c2000)

    cnc = ncopen(iemre.get_dailyc_ncname())

    res['data'].append({
        'prism_precip_in': myrounder(prism_precip, 2),
        'mrms_precip_in': myrounder(mrms_precip, 2),
        'daily_high_f': myrounder(
           datatypes.temperature(
                nc.variables['high_tmpk'][offset, j, i], 'K').value('F'), 1),
        '12z_high_f': myrounder(
           datatypes.temperature(
                nc.variables['high_tmpk_12z'][offset, j, i],
                'K').value('F'), 1),
        'climate_daily_high_f': myrounder(
           datatypes.temperature(
                cnc.variables['high_tmpk'][coffset, j, i], 'K').value("F"), 1),
        'daily_low_f': myrounder(
           datatypes.temperature(
                nc.variables['low_tmpk'][offset, j, i], 'K').value("F"), 1),
        '12z_low_f': myrounder(
           datatypes.temperature(
                nc.variables['low_tmpk_12z'][offset, j, i],
                'K').value('F'), 1),
        'avg_dewpoint_f': myrounder(
           datatypes.temperature(
                nc.variables['avg_dwpk'][offset, j, i], 'K').value('F'), 1),
        'climate_daily_low_f': myrounder(
           datatypes.temperature(
                cnc.variables['low_tmpk'][coffset, j, i], 'K').value("F"), 1),
        'daily_precip_in': myrounder(
           nc.variables['p01d'][offset, j, i] / 25.4, 2),
        '12z_precip_in': myrounder(
           nc.variables['p01d_12z'][offset, j, i] / 25.4, 2),
        'climate_daily_precip_in': myrounder(
           cnc.variables['p01d'][coffset, j, i] / 25.4, 2),
        'srad_mj': myrounder(
           nc.variables['rsds'][offset, j, i] * 86400. / 1000000., 2),
        'avg_windspeed_mps': myrounder(
           nc.variables['wind_speed'][offset, j, i], 2),
      })
    nc.close()
    cnc.close()

    ssw(json.dumps(res))


if __name__ == '__main__':
    main()
