"""Ob timeseries"""
import datetime
from collections import OrderedDict

import pytz
import matplotlib.dates as mdates
from pandas.io.sql import read_sql
import pyiem.datatypes as dt
from pyiem.network import Table as NetworkTable
from pyiem.util import get_autoplot_context, get_dbconn, utc

PDICT = OrderedDict((
    ('default', 'Temperatures | Winds | Clouds + Vis'),
    ('two', 'Temperatures | Winds | Pressure'),
))


def date_ticker(ax, mytz):
    """Timestamp formatter"""
    (xmin, xmax) = ax.get_xlim()
    xmin = mdates.num2date(xmin)
    xmax = mdates.num2date(xmax)
    xmin = xmin.replace(minute=0)
    xmax = (xmax + datetime.timedelta(minutes=59)).replace(minute=0)
    now = xmin
    xticks = []
    xticklabels = []
    while now <= xmax:
        lts = now.astimezone(mytz)
        if lts.hour % 6 == 0:
            fmt = "%-I %p\n%-d %b" if lts.hour == 0 else "%-I %p"
            xticks.append(now)
            xticklabels.append(lts.strftime(fmt))
        if len(xticks) > 100:
            break
        now += datetime.timedelta(hours=1)

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)


def get_description():
    """ Return a dict describing how to call this plotter """
    desc = dict()
    desc['data'] = True
    desc['cache'] = 360
    desc['description'] = """This plot presents a time series of
    observations.  Please note the colors and axes labels used to denote
    which variable is which in the combination plots."""
    d3 = datetime.date.today() - datetime.timedelta(days=2)
    desc['arguments'] = [
        dict(type='sid', label='Select IEM Tracked Station',
             name='station', default='AMW', network='IA_ASOS'),
        dict(type='date', default=d3.strftime("%Y/%m/%d"), name='sdate',
             label='Start Date of Plot: (optional)', optional=True),
        dict(type='select', options=PDICT, default='default',
             label='Plot Type', name='p'),
    ]
    return desc


def get_data(network, station, tzname, sdate):
    """retrieve the data frame we want"""
    if sdate is None:
        pgconn = get_dbconn('iem')
        return read_sql("""
            SELECT tmpf, dwpf, sknt, gust, drct, skyc1, skyc2, skyc3, skyc4,
            skyl1, skyl2, skyl3, skyl4, vsby, alti,
            valid at time zone 'UTC' as utc_valid
            from current_log c JOIN stations t ON (t.iemid = c.iemid)
            WHERE t.network = %s and t.id = %s ORDER by valid ASC
        """, pgconn, params=(network, station), index_col='utc_valid')

    sts = utc(2018)
    sts = sts.astimezone(pytz.timezone(tzname))
    sts = sts.replace(year=sdate.year, month=sdate.month, day=sdate.day,
                      hour=0, minute=0)
    ets = sts + datetime.timedelta(hours=72)
    if network == 'AWOS' or network.endswith('ASOS'):
        pgconn = get_dbconn('asos')
        df = read_sql("""
            SELECT tmpf, dwpf, sknt, gust, drct, skyc1, skyc2, skyc3, skyc4,
            skyl1, skyl2, skyl3, skyl4, vsby, alti,
            valid at time zone 'UTC' as utc_valid
            from alldata WHERE station = %s and valid >= %s and valid < %s
            ORDER by valid ASC
        """, pgconn, params=(station, sts, ets), index_col='utc_valid')
    return df


def plotter(fdict):
    """ Go """
    import matplotlib
    matplotlib.use('agg')
    import matplotlib.pyplot as plt
    ctx = get_autoplot_context(fdict, get_description())
    station = ctx['station']
    network = ctx['network']
    sdate = ctx.get('sdate')
    plot_type = ctx['p']

    nt = NetworkTable(network)
    if not nt.sts:
        raise ValueError(("Network Identifier %s is unknown to IEM"
                          ) % (network,))
    if station not in nt.sts:
        raise ValueError(("Station %s does not exist in network %s"
                          ) % (station, network))
    tzname = nt.sts[station]['tzname']

    df = get_data(network, station, tzname, sdate)
    # if d1 is not None and d1 >= 0 and d1 <= 360:
    # if s is not None and s >= 0 and s < 200:
    # if t is not None and t >= -90 and t < 190:
    # if d is not None and d >= -90 and d < 190:
    # if v1 is not None and v1 >= 0 and v1 < 30:

    def ceilingfunc(row):
        """Our logic to compute a ceiling"""
        c = [row['skyc1'], row['skyc2'], row['skyc3'], row['skyc4']]
        if 'OVC' in c:
            pos = c.index('OVC')
            larr = [row['skyl1'], row['skyl2'], row['skyl3'], row['skyl4']]
            return larr[pos] / 1000.

    df['ceiling'] = df.apply(ceilingfunc, axis=1)

    fig = plt.figure(figsize=(9, 9))
    xalign = 0.1
    xwidth = 0.8
    ax = fig.add_axes([xalign, 0.7, xwidth, 0.25])

    xmin = df.index.min()
    xmax = df.index.max()
    # ____________PLOT 1___________________________
    df2 = df[df['tmpf'].notnull()]
    ax.plot(df2.index.values, df2['tmpf'], lw=2, label='Air Temp',
            color='#db6065', zorder=2)
    df2 = df[df['dwpf'].notnull()]
    ax.plot(df2.index.values, df2['dwpf'], lw=2, label='Dew Point',
            color='#346633', zorder=3)

    ax.set_title("[%s] %s\nRecent Time Series" % (
        station, nt.sts[station]['name']))
    ax.grid(True)
    ax.text(-0.1, 0, "Air Temperature [F]", color='#db6065', rotation=90,
            transform=ax.transAxes, verticalalignment='bottom')
    ax.set_ylim(bottom=(df['dwpf'].min() - 3))
    plt.setp(ax.get_xticklabels(), visible=True)
    date_ticker(ax, pytz.timezone(tzname))
    ax.set_xlim(xmin, xmax)

    # _____________PLOT 2____________________________
    ax = fig.add_axes([xalign, 0.4, xwidth, 0.25])
    df2 = df[df['drct'].notnull()]

    ax2 = ax.twinx()
    df2 = df[df['gust'].notnull()]
    ax2.fill_between(df2.index.values, 0,
                     dt.speed(df2['gust'], 'KT').value('MPH'),
                     color='#9898ff', zorder=2)
    df2 = df[df['sknt'].notnull()]
    ax2.fill_between(df2.index.values, 0,
                     dt.speed(df2['sknt'], 'KT').value('MPH'),
                     color='#373698', zorder=3)
    ax2.set_ylim(bottom=0)
    ax.set_yticks(range(0, 361, 45))
    ax.set_yticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', "N"])
    ax.set_ylim(0, 360.1)
    date_ticker(ax, pytz.timezone(tzname))
    ax.scatter(df2.index.values, df2['drct'], facecolor='None',
               edgecolor='#b8bc74', zorder=4)
    ax.set_zorder(ax2.get_zorder()+1)
    ax.patch.set_visible(False)
    ax.set_xlim(xmin, xmax)

    # _________ PLOT 3 ____
    ax = fig.add_axes([xalign, 0.1, xwidth, 0.25])
    if plot_type == 'default':
        ax2 = ax.twinx()
        ax2.scatter(df.index.values, df['ceiling'], label='Visibility',
                    marker='o', s=40, color='g')
        ax2.set_ylabel("Overcast Ceiling [k ft]", color='g')
        ax2.set_ylim(bottom=0)
        ax.scatter(df.index.values, df['vsby'], label='Visibility', marker='*',
                   s=40, color='b')
        ax.set_ylim(0, 14)
    elif plot_type == 'two':
        df2 = df[(df['alti'] > 20.) & (df['alti'] < 40.)]
        ax.grid(True)
        vals = dt.pressure(df2['alti'], 'IN').value('MB')
        ax.fill_between(df2.index.values, 0, vals, color='#a16334')
        ax.set_ylim(bottom=(vals.min() - 1), top=(vals.max() + 1))
        ax.set_ylabel("Pressure [mb]")

    date_ticker(ax, pytz.timezone(tzname))
    ax.set_xlabel("Plot Time Zone: %s" % (tzname,))
    ax.set_xlim(xmin, xmax)

    return fig, df


if __name__ == '__main__':
    plotter(dict())
