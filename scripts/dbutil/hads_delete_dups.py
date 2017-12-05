"""
 Our HADS database gets loaded up with duplicates, this cleans it up.

 called from RUN_MIDNIGHT.sh
"""
from __future__ import print_function
import datetime
import sys

import pytz
from pyiem.util import get_dbconn, utc


def query(sql, args=None):
    """
    Do a query and make it atomic
    """
    pgconn = get_dbconn('hads')
    hcursor = pgconn.cursor()
    sts = datetime.datetime.now()
    hcursor.execute("set work_mem='16GB'")
    hcursor.execute(sql, args if args is not None else [])
    ets = datetime.datetime.now()
    print("%7s [%8.4fs] %s" % (hcursor.rowcount, (ets - sts).total_seconds(),
                               sql))
    hcursor.close()
    pgconn.commit()


def workflow(valid):
    ''' Do the work for this date, which is set to 00 UTC '''
    # Delete schoolnet data, since we created it in the first place!
    tbl = "raw%s" % (valid.strftime("%Y_%m"),)
    sql = """DELETE from """ + tbl + """ WHERE station IN
              (SELECT id from stations WHERE network in ('KCCI','KELO','KIMT')
              )"""
    query(sql)

    # Extract unique obs to special table
    sql = """CREATE table tmp as select distinct * from """+tbl+"""
        WHERE valid BETWEEN %s and %s"""
    args = (valid, valid + datetime.timedelta(hours=24))
    query(sql, args)

    # Delete them all!
    sql = """delete from """+tbl+""" WHERE valid BETWEEN %s and %s"""
    query(sql, args)

    sql = "DROP index "+tbl+"_idx"
    query(sql)
    sql = "DROP index "+tbl+"_valid_idx"
    query(sql)

    # Insert from special table
    sql = "INSERT into "+tbl+" SELECT * from tmp"
    query(sql)

    sql = "CREATE index %s_idx on %s(station,valid)" % (tbl, tbl)
    query(sql)
    sql = "CREATE index %s_valid_idx on %s(valid)" % (tbl, tbl)
    query(sql)

    sql = "DROP TABLE tmp"
    query(sql)


def main(argv):
    """Go Main Go"""
    if len(argv) == 4:
        utcnow = utc(int(argv[1]), int(argv[2]), int(argv[3]))
        workflow(utcnow)
        return
    utcnow = datetime.datetime.utcnow()
    utcnow = utcnow.replace(hour=0, minute=0, second=0, microsecond=0,
                            tzinfo=pytz.utc)
    # Run for 'yesterday' and 35 days ago
    for day in [1, 35]:
        workflow(utcnow - datetime.timedelta(days=day))


if __name__ == '__main__':
    # See how we are called
    main(sys.argv)
