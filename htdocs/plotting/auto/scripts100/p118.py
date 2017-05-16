"""precip days per month"""
import datetime
from pandas.io.sql import read_sql
import psycopg2
from pyiem.util import get_autoplot_context
from pyiem.network import Table as NetworkTable

PDICT = {'precip_days': 'Precipitation Days',
         'snow_days': 'Snowfall Days'}


def get_description():
    """ Return a dict describing how to call this plotter """
    desc = dict()
    desc['data'] = True
    desc['report'] = True
    desc['description'] = """ """
    desc['arguments'] = [
        dict(type='station', name='station', default='IA2203',
             label='Select Station', network='IACLIMATE'),
        dict(type='select', name='var', options=PDICT, default='precip_days',
             label='Select Variable'),
    ]
    return desc


def plotter(fdict):
    """ Go """
    import matplotlib
    matplotlib.use('agg')
    pgconn = psycopg2.connect(database='coop', host='iemdb', user='nobody')
    ctx = get_autoplot_context(fdict, get_description())
    station = ctx['station'].upper()
    varname = ctx['var']

    table = "alldata_%s" % (station[:2], )
    nt = NetworkTable("%sCLIMATE" % (station[:2], ))
    df = read_sql("""
    SELECT year, month,
    sum(case when precip >= 0.01 then 1 else 0 end) as precip_days,
    sum(case when snow >= 0.01 then 1 else 0 end) as snow_days
    from """+table+""" WHERE station = %s
    GROUP by year, month
    """, pgconn, params=(station,), index_col=['year', 'month'])

    res = """\
# IEM Climodat https://mesonet.agron.iastate.edu/climodat/
# Report Generated: %s
# Climate Record: %s -> %s
# Site Information: [%s] %s
# Contact Information: Daryl Herzmann akrherz@iastate.edu 515.294.5978
# NUMBER OF DAYS WITH PRECIPITATION PER MONTH PER YEAR
# Days with a trace accumulation are not included
YEAR   JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC ANN
""" % (datetime.date.today().strftime("%d %b %Y"),
       nt.sts[station]['archive_begin'].date(), datetime.date.today(), station,
       nt.sts[station]['name'])

    for year in df.index.levels[0]:
        res += "%4i  " % (year,)
        total = 0
        for month in df.index.levels[1]:
            try:
                val = df.at[(year, month), varname]
                total += val
                res += " %3i" % (val, )
            except:
                res += "    "
        res += " %3i\n" % (total, )
    return None, df, res


if __name__ == '__main__':
    plotter(dict())
