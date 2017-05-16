"""text report of number of days with precip above threshold"""
import datetime

import psycopg2
from pandas.io.sql import read_sql
import numpy as np
from pyiem.network import Table as NetworkTable
from pyiem.util import get_autoplot_context
CATS = np.array([0.01, 0.5, 1., 2., 3., 4.])


def get_description():
    """ Return a dict describing how to call this plotter """
    desc = dict()
    desc['data'] = True
    desc['report'] = True
    desc['description'] = """ """
    desc['arguments'] = [
        dict(type='station', name='station', default='IA2203',
             label='Select Station', network='IACLIMATE'),
    ]
    return desc


def plotter(fdict):
    """ Go """
    import matplotlib
    matplotlib.use('agg')
    pgconn = psycopg2.connect(database='coop', host='iemdb', user='nobody')
    ctx = get_autoplot_context(fdict, get_description())

    station = ctx['station']

    table = "alldata_%s" % (station[:2], )
    nt = NetworkTable("%sCLIMATE" % (station[:2], ))

    startyear = nt.sts[station]['archive_begin'].year
    # 0.01, 0.5, 1, 2, 3, 4
    df = read_sql("""
        SELECT year, month,
        sum(case when precip >= %s then 1 else 0 end) as cat1,
        sum(case when precip >= %s then 1 else 0 end) as cat2,
        sum(case when precip >= %s then 1 else 0 end) as cat3,
        sum(case when precip >= %s then 1 else 0 end) as cat4,
        sum(case when precip >= %s then 1 else 0 end) as cat5,
        sum(case when precip >= %s then 1 else 0 end) as cat6
        from """ + table + """ WHERE station = %s GROUP by year, month
        ORDER by year, month
    """, pgconn, params=(CATS[0], CATS[1], CATS[2], CATS[3], CATS[4],
                         CATS[5], station), index_col=['year', 'month'])

    res = """\
# IEM Climodat https://mesonet.agron.iastate.edu/climodat/
# Report Generated: %s
# Climate Record: %s -> %s
# Site Information: [%s] %s
# Contact Information: Daryl Herzmann akrherz@iastate.edu 515.294.5978
# Number of days per year with precipitation at or above threshold [inch]
# Partitioned by month of the year, 'ANN' represents the entire year
""" % (datetime.date.today().strftime("%d %b %Y"),
       nt.sts[station]['archive_begin'].date(), datetime.date.today(), station,
       nt.sts[station]['name'])

    for i, cat in enumerate(CATS):
        col = "cat%s" % (i+1,)
        res += ("YEAR %4.2f JAN FEB MAR APR MAY JUN "
                "JUL AUG SEP OCT NOV DEC ANN\n") % (cat,)
        for yr in range(startyear, datetime.date.today().year + 1):
            res += "%s %4.2f " % (yr, cat)
            for mo in range(1, 13):
                if (yr, mo) in df.index:
                    res += "%3.0f " % (df.at[(yr, mo), col], )
                else:
                    res += "%3s " % ('M', )
            res += "%3.0f\n" % (df.loc[(yr, slice(1, 12)), col].sum(), )

    return None, df, res


if __name__ == '__main__':
    plotter(dict())
