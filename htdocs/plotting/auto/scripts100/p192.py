"""Generalized mapper of AZOS data"""
import datetime

import pytz
import numpy as np
from pandas.io.sql import read_sql
from pyiem import reference
from pyiem.plot.use_agg import plt
from pyiem.plot import MapPlot
from pyiem.network import Table as NetworkTable
from pyiem.util import get_autoplot_context, get_dbconn

PDICT = {'cwa': 'Plot by NWS Forecast Office',
         'state': 'Plot by State'}
PDICT2 = {'vsby': 'Visibility'}


def get_description():
    """ Return a dict describing how to call this plotter """
    desc = dict()
    desc['data'] = True
    desc['cache'] = 600
    desc['description'] = """Generates analysis maps of ASOS/AWOS
    station data."""
    utcnow = datetime.datetime.utcnow()
    desc['arguments'] = [
        dict(type='select', name='t', default='state', options=PDICT,
             label='Select plot extent type:'),
        dict(type='networkselect', name='wfo', network='WFO',
             default='DMX', label='Select WFO: (ignored if plotting state)'),
        dict(type='state', name='state',
             default='IA', label='Select State: (ignored if plotting wfo)'),
        dict(type='select', name='v', default='vsby', options=PDICT2,
             label='Select statistic to plot:'),
        dict(type='datetime', name='valid',
             default=utcnow.strftime("%Y/%m/%d %H00"),
             label='Valid Analysis Time (UTC)', optional=True,
             min="1986/01/01 0000"),
        dict(type='cmap', name='cmap', default='gray', label='Color Ramp:'),
    ]
    return desc


def get_df(ctx, bnds, buf=2.25):
    """Figure out what data we need to fetch here"""
    if ctx.get('valid'):
        valid = ctx['valid'].replace(tzinfo=pytz.utc)
        dbconn = get_dbconn("asos")
        df = read_sql("""
        WITH mystation as (
            select id, st_x(geom) as lon, st_y(geom) as lat,
            state, wfo from stations
            where (network ~* 'ASOS' or network = 'AWOS') and
            ST_contains(ST_geomfromtext(
                'SRID=4326;POLYGON((%s %s, %s %s, %s %s, %s %s, %s %s))
                        '), geom)
        )
        SELECT station, vsby, state, wfo, lat, lon,
        abs(extract(epoch from (%s - valid))) as tdiff from
        alldata a JOIN mystation m on (a.station = m.id)
        WHERE a.valid between %s and %s ORDER by tdiff ASC
        """, dbconn, params=(bnds[0] - buf, bnds[1] - buf,
                             bnds[0] - buf, bnds[3] + buf,
                             bnds[2] + buf, bnds[3] + buf,
                             bnds[2] + buf, bnds[1] - buf,
                             bnds[0] - buf, bnds[1] - buf,
                             valid,
                             valid - datetime.timedelta(minutes=30),
                             valid + datetime.timedelta(minutes=30)))
        df = df.groupby('station').first()
    else:
        dbconn = get_dbconn('iem')
        valid = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        df = read_sql("""
            SELECT state, wfo,
      id, network, vsby, ST_x(geom) as lon, ST_y(geom) as lat
    FROM
      current c JOIN stations s ON (s.iemid = c.iemid)
    WHERE
      (s.network ~* 'ASOS' or s.network = 'AWOS') and s.country = 'US' and
      valid + '80 minutes'::interval > now() and
      vsby >= 0 and vsby <= 10 and
      ST_contains(ST_geomfromtext(
                        'SRID=4326;POLYGON((%s %s, %s %s, %s %s, %s %s, %s %s))
                        '), geom)
        """, dbconn, params=(bnds[0] - buf, bnds[1] - buf,
                             bnds[0] - buf, bnds[3] + buf,
                             bnds[2] + buf, bnds[3] + buf,
                             bnds[2] + buf, bnds[1] - buf,
                             bnds[0] - buf, bnds[1] - buf))
    return df, valid


def plotter(fdict):
    """ Go """
    ctx = get_autoplot_context(fdict, get_description())

    if ctx['t'] == 'state':
        bnds = reference.state_bounds[ctx['state']]
        title = reference.state_names[ctx['state']]
    else:
        bnds = reference.wfo_bounds[ctx['wfo']]
        nt = NetworkTable("WFO")
        title = "NWS CWA %s [%s]" % (nt.sts[ctx['wfo']]['name'], ctx['wfo'])
    df, valid = get_df(ctx, bnds)
    if df.empty:
        raise ValueError("No data was found for your query")
    mp = MapPlot(sector=('state' if ctx['t'] == 'state' else 'cwa'),
                 state=ctx['state'],
                 cwa=(ctx['wfo'] if len(ctx['wfo']) == 3 else ctx['wfo'][1:]),
                 axisbg='white',
                 title='%s for %s' % (PDICT2[ctx['v']], title),
                 subtitle=('Map valid: %s UTC'
                           ) % (valid.strftime("%d %b %Y %H:%M"),),
                 nocaption=True,
                 titlefontsize=16)
    mp.contourf(df['lon'].values, df['lat'].values, df['vsby'].values,
                np.array([0.01, 0.1, 0.25, 0.5, 1, 2, 3, 5, 8, 9.9]),
                units='miles', cmap=plt.get_cmap(ctx['cmap']))
    if ctx['t'] == 'state':
        df2 = df[df['state'] == ctx['state']]
    else:
        df2 = df[df['wfo'] == ctx['wfo']]

    mp.plot_values(df2['lon'].values, df2['lat'].values,
                   df2['vsby'].values, '%.1f')
    mp.drawcounties()
    if ctx['t'] == 'cwa':
        mp.draw_cwas()

    return mp.fig, df


if __name__ == '__main__':
    plotter(dict())
