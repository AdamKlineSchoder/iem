#!/bin/sh

MS_MAPFILE=/opt/iem/data/wms/us/mrms_nn.map
export MS_MAPFILE

/opt/iem/cgi-bin/mapserv/mapserv
