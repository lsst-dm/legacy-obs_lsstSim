#!/usr/bin/env python2
# 
# LSST Data Management System
# Copyright 2008, 2009, 2010, 2011, 2012, 2013 LSST Corporation.
# 
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#
from __future__ import absolute_import, division
import glob
import os
import re
try:
    import sqlite3
except ImportError:
    # try external pysqlite package; deprecated
    import sqlite as sqlite3
import sys

if os.path.exists("defectRegistry.sqlite3"):
    os.unlink("defectRegistry.sqlite3")
conn = sqlite3.connect("defectRegistry.sqlite3")

cmd = "create table defect (id integer primary key autoincrement"
cmd += ", path text, version int, ccdSerial int"
cmd += ", validStart text, validEnd text)"
conn.execute(cmd)
conn.commit()

cmd = "INSERT INTO defect VALUES (NULL, ?, ?, ?, ?, ?)"

for f in glob.glob("rev_*/defects*.fits"):
    m = re.search(r'rev_(\d+)/defects(\d+)\.fits', f)
    if not m:
        print >>sys.stderr, "Unrecognized file: %s" % (f,)
        continue
    print f
    conn.execute(cmd, (f, int(m.group(1)), int(m.group(2)),
        "1970-01-01", "2037-12-31"))
conn.commit()
conn.close()
