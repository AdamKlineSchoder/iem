#!/bin/sh

MS_MAPFILE=/opt/iem/data/wms/q2.map
export MS_MAPFILE

/opt/iem/cgi-bin/mapserv/mapserv
