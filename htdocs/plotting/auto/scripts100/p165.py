"""Map of dates"""
import datetime
from collections import OrderedDict

import numpy as np
from pandas.io.sql import read_sql
from pyiem.util import get_autoplot_context, get_dbconn

PDICT = OrderedDict([
    ('IA', 'Iowa'),
    ('IL', 'Illinois'),
    ('KS', 'Kansas'),
    ('KY', 'Kentucky'),
    ('MI', 'Michigan'),
    ('MN', 'Minnesota'),
    ('MO', 'Missouri'),
    ('NE', 'Nebraska'),
    ('ND', 'North Dakota'),
    ('OH', 'Ohio'),
    ('SD', 'South Dakota'),
    ('WI', 'Wisconsin'),
    ('midwest', 'Mid West US')])
PDICT3 = {'contour': 'Contour + Plot Values',
          'values': 'Plot Values Only'}
PDICT2 = {'spring_below': 'Last Spring Date Below',
          'fall_below': 'First Fall Date Below'}
SQLOPT = {
    'spring_below': (" max(case when low < %s and month < 7 then "
                     " extract(doy from day) else -1 end) "),
    'fall_below': (" min(case when low < %s and month >= 7 then "
                   " extract(doy from day) else 400 end) ")}


def get_description():
    """ Return a dict describing how to call this plotter """
    desc = dict()
    desc['data'] = True
    desc['description'] = """This map presents the first fall date or last spring
    date with a temperature at/above or below some threshold.  The year is
    split on 1 July for the purposes of this plotting app.
    """
    today = datetime.datetime.today() - datetime.timedelta(days=1)
    desc['arguments'] = [
        dict(type='select', name='sector', default='IA',
             label='Select Sector:', options=PDICT),
        dict(type='select', name='var', default='spring_below',
             label='Select Plot Type:', options=PDICT2),
        dict(type='select', name='popt', default='contour',
             label='Plot Display Options:', options=PDICT3),
        dict(type='year', name='year',
             default=today.year,
             label='Start Year:', min=1893),
        dict(type='int', name='threshold',
             default=32,
             label='Temperature Threshold (F):'),
    ]
    return desc


def plotter(fdict):
    """ Go """
    import matplotlib
    matplotlib.use('agg')
    from pyiem.plot import MapPlot
    pgconn = get_dbconn('coop')
    ctx = get_autoplot_context(fdict, get_description())
    sector = ctx['sector']
    varname = ctx['var']
    year = ctx['year']
    popt = ctx['popt']
    threshold = ctx['threshold']
    table = "alldata_%s" % (sector,)
    df = read_sql("""
    WITH data as (
        SELECT station, """ + SQLOPT[varname] + """ as doy
        from """ + table + """
        WHERE year = %s GROUP by station
    )
    select station, doy, st_x(geom) as lon, st_y(geom) as lat
    from data d JOIN stations t on (d.station = t.id) WHERE
    t.network = %s and substr(station, 3, 4) != '0000'
    and substr(station, 3, 1) != 'C' and doy not in (0, 400) ORDER by doy
    """, pgconn, params=(threshold, year, '%sCLIMATE' % (sector,)),
                  index_col='station')
    if df.empty:
        return "No data found!"

    def f(val):
        ts = datetime.date(year, 1, 1) + datetime.timedelta(days=(val - 1))
        return ts.strftime("%-m/%-d")

    df['pdate'] = df['doy'].apply(f)

    mp = MapPlot(sector='state', state=sector,
                 continental_color='white', nocaption=True,
                 title="%s %s %s$^\circ$F" % (year, PDICT2[varname],
                                              threshold),
                 subtitle='based on NWS COOP and IEM Daily Estimates')
    levs = np.linspace(df['doy'].min() - 3, df['doy'].max() + 3, 7, dtype='i')
    levlables = map(f, levs)
    if popt == 'contour':
        mp.contourf(df['lon'], df['lat'], df['doy'], levs,
                    clevlabels=levlables)
    mp.plot_values(df['lon'], df['lat'], df['pdate'], labelbuffer=5)
    mp.drawcounties()

    return mp.fig, df


if __name__ == '__main__':
    plotter(dict())
