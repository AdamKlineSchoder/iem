"""Use the REST service to setup any new segments for the new season

 * JSON data is in Google 3857
"""
from __future__ import print_function

from shapely.geometry import LineString, MultiLineString
import requests
from ingest_roads_rest import URI
from pyiem.util import get_dbconn


def main():
    """Go Main, please"""
    pgconn = get_dbconn('postgis')
    cursor = pgconn.cursor()
    cursor.execute("""
    DELETE from roads_current
    """)
    print("removed %s rows from roads_current" % (cursor.rowcount, ))
    req = requests.get(URI, timeout=30)
    jobj = req.json()
    archive_begin = "2018-10-09 00:00"
    print("adding %s rows to roads_base" % (len(jobj['features']), ))
    for feat in jobj['features']:
        props = feat['attributes']
        # Geometry is [[pt]] and we only have single segments
        path = MultiLineString([LineString(feat['geometry']['paths'][0])])
        # segid is defined by the database insert
        major = props['ROUTE_NAME']
        minor = props['NAMEID'].split(":", 1)[1]
        (typ, num) = major.replace("-", " ").split()
        int1 = num if typ == 'I' else None
        us1 = num if typ == 'US' else None
        st1 = num if typ == 'IA' else None
        if major == 'Airline Highway':
            typ = 'IA'
            num = 0
        sys_id = props['ROUTE_RANK']
        longname = props['LONG_NAME']
        geom = ("ST_Transform(ST_SetSrid(ST_GeomFromText('%s'), 3857), 26915)"
                ) % (path.wkt)
        idot_id = props['SEGMENT_ID']
        cursor.execute("""
        INSERT into roads_base (major, minor, us1, st1, int1, type, longname,
        geom, idot_id, archive_begin) VALUES (%s, %s, %s, %s, %s, %s, %s,
        """ + geom + """, %s, %s) RETURNING segid
        """, (major[:10], minor, us1, st1, int1, sys_id, longname,
              idot_id, archive_begin))
        segid = cursor.fetchone()[0]
        cursor.execute("""
            UPDATE roads_base
            SET simple_geom = ST_Simplify(geom, 0.01) WHERE segid = %s
        """, (segid,))
        # Figure out which WFO this segment is in...
        cursor.execute("""
            SELECT u.wfo,
            ST_Distance(u.geom, ST_Transform(b.geom, 4326))
            from ugcs u, roads_base b WHERE
            substr(ugc, 1, 2) = 'IA' and b.segid = %s
            and u.end_ts is null ORDER by ST_Distance ASC
        """, (segid,))
        wfo = cursor.fetchone()[0]
        cursor.execute("""
            UPDATE roads_base SET wfo = %s WHERE segid = %s
        """, (wfo, segid))
        # Add a roads_current entry, 85 is a hack
        cursor.execute("""
            INSERT into roads_current(segid, valid, cond_code)
            VALUES (%s, %s, 85)
        """, (segid, archive_begin))
    cursor.close()
    pgconn.commit()


if __name__ == '__main__':
    main()
