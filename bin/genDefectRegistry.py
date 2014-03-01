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
import sqlite3
import sys

import pyfits

import eups

baseDir = eups.productDir("obs_lsstSim")
registryDir = os.path.join(os.path.normpath(baseDir), "description", "defects")
registryPath = os.path.join(registryDir, "defectRegistry.sqlite3")

# create new database
if os.path.exists(registryPath):
    print "Deleting existing %r" % (registryPath,)
    os.unlink(registryPath)
print "Creating %r" % (registryPath,)
conn = sqlite3.connect(registryPath)

# create "defect" table
cmd = "create table defect (id integer primary key autoincrement" + \
    ", path text, version int, ccd text" + \
    ", validStart text, validEnd text)"
conn.execute(cmd)
conn.commit()

# fill table
cmd = "INSERT INTO defect VALUES (NULL, ?, ?, ?, ?, ?)"
numEntries = 0
for filePath in glob.glob(os.path.join(registryDir, "rev_*", "defects*.fits")):
    m = re.search(r'rev_(\d+)/defects(\d+)\.fits', filePath)
    if not m:
        sys.stderr.write("Skipping file with invalid name: %r\n" % (filePath,))
        continue
    print "Processing %r" % (filePath,)

    fitsTable = pyfits.open(filePath)
    ccd = fitsTable[1].header["NAME"]
    conn.execute(cmd, (
        filePath,
        int(m.group(1)),
        ccd,
        "1970-01-01",
        "2037-12-31",
    ))
    numEntries += 1
conn.commit()
print "Added %d entries" % (numEntries)

conn.close()
