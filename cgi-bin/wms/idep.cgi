#!/bin/sh

MS_MAPFILE=/opt/iem/data/wms/idep.map
export MS_MAPFILE

/opt/iem/cgi-bin/mapserv/mapserv
