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
from __future__ import print_function
import glob
from optparse import OptionParser
import os
import re
import shutil
try:
    import sqlite3
except ImportError:
    # try external pysqlite package; deprecated
    import sqlite as sqlite3
import sys
import lsst.daf.base as dafBase
from lsst.afw.fits import readMetadata
from lsst.afw.geom import makeSkyWcs
import lsst.skypix as skypix


def process(dirList, inputRegistry, outputRegistry="registry.sqlite3"):
    if os.path.exists(outputRegistry):
        print("Output registry exists; will not overwrite.", file=sys.stderr)
        sys.exit(1)
    if inputRegistry is not None:
        if not os.path.exists(inputRegistry):
            print("Input registry does not exist.", file=sys.stderr)
            sys.exit(1)
        shutil.copy(inputRegistry, outputRegistry)

    conn = sqlite3.connect(outputRegistry)

    done = {}
    if inputRegistry is None:
        # Create tables in new output registry.
        cmd = """CREATE TABLE raw (id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit INT, filter TEXT, snap INT,
            raft TEXT, sensor TEXT, channel TEXT,
            taiObs TEXT, expTime DOUBLE)"""
        # cmd += ", unique(visit, snap, raft, sensor, channel))"
        conn.execute(cmd)
        cmd = "CREATE TABLE raw_skyTile (id INTEGER, skyTile INTEGER)"
        # cmd += ", unique(id, skyTile), foreign key(id) references raw(id))"
        conn.execute(cmd)
        conn.execute("""CREATE TABLE raw_visit (visit INT, filter TEXT,
            taiObs TEXT, expTime DOUBLE, UNIQUE(visit))""")
        conn.commit()
    else:
        cmd = """SELECT visit || '_F' || filter || '_E' || snap ||
            '_R' || raft || '_S' || sensor || '_C' || channel FROM raw"""
        for row in conn.execute(cmd):
            done[row[0]] = True

    qsp = skypix.createQuadSpherePixelization()

    try:
        for dir in dirList:
            if os.path.exists(os.path.join(dir, "raw")):
                for visitDir in glob.glob(os.path.join(dir, "raw", "v*-f*",)):
                    processVisit(visitDir, conn, done, qsp)
            else:
                processVisit(dir, conn, done, qsp)
    finally:
        print("Cleaning up...", file=sys.stderr)
        conn.execute("DELETE FROM raw_visit")
        conn.commit()
        conn.execute("""INSERT INTO raw_visit
                SELECT DISTINCT visit, filter, taiObs, expTime FROM raw
                WHERE snap = 0""")
        conn.commit()
        conn.execute("""CREATE UNIQUE INDEX uq_raw ON raw
                (visit, snap, raft, sensor, channel)""")
        conn.execute("CREATE INDEX ix_skyTile_id ON raw_skyTile (id)")
        conn.execute("CREATE INDEX ix_skyTile_tile ON raw_skyTile (skyTile)")
        conn.close()


def processVisit(visitDir, conn, done, qsp):
    print(visitDir, "... started", file=sys.stderr)
    for raftDir in glob.glob(os.path.join(visitDir, "E00[01]", "R[0-4][0-4]")):
        processRaft(raftDir, conn, done, qsp)
    print(visitDir, "... completed", file=sys.stderr)


def processRaft(raftDir, conn, done, qsp):
    nProcessed = 0
    nSkipped = 0
    nUnrecognized = 0
    for fits in glob.glob(os.path.join(raftDir, "S[0-2][0-2]",
                                       "imsim_*_R[0-4][0-4]_S[0-2][0-2]_C[01][0-7]_E00[01].fits*")):
        m = re.search(r'v(\d+)-f(\w)/E00(\d)/R(\d)(\d)/S(\d)(\d)/' +
                      r'imsim_\1_R\4\5_S\6\7_C(\d)(\d)_E00\3\.fits', fits)
        if not m:
            print("Warning: Unrecognized file:", fits, file=sys.stderr)
            nUnrecognized += 1
            continue

        (visit, filter, snap, raft1, raft2, sensor1, sensor2,
         channel1, channel2) = m.groups()
        key = "%s_F%s_E%s_R%s,%s_S%s,%s_C%s,%s" % (visit, filter,
                                                   snap, raft1, raft2, sensor1, sensor2, channel1, channel2)
        if key in done:
            nSkipped += 1
            continue

        md = readMetadata(fits)
        expTime = md.get("EXPTIME")
        mjdObs = md.get("MJD-OBS")
        taiObs = dafBase.DateTime(mjdObs, dafBase.DateTime.MJD,
                                  dafBase.DateTime.TAI).toString(dafBase.DateTime.UTC)[:-1]
        conn.execute("""INSERT INTO raw VALUES
            (NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (visit, filter, snap, "%s,%s" % (raft1, raft2),
                      "%s,%s" % (sensor1, sensor2),
                      "%s,%s" % (channel1, channel2), taiObs, expTime))

        for row in conn.execute("SELECT last_insert_rowid()"):
            id = row[0]
            break

        wcs = makeSkyWcs(md)
        poly = skypix.imageToPolygon(wcs,
                                     md.get("NAXIS1"), md.get("NAXIS2"),
                                     padRad=0.000075)  # about 15 arcsec
        pix = qsp.intersect(poly)
        for skyTileId in pix:
            conn.execute("INSERT INTO raw_skyTile VALUES(?, ?)",
                         (id, skyTileId))

        conn.commit()

        nProcessed += 1

    print(raftDir,
          "... %d processed, %d skipped, %d unrecognized" %
          (nProcessed, nSkipped, nUnrecognized), file=sys.stderr)


if __name__ == "__main__":
    parser = OptionParser(usage="""%prog [options] DIR ...

DIR may be either a root directory containing a 'raw' subdirectory
or a visit subdirectory.""")
    parser.add_option("-i", dest="inputRegistry", help="input registry")
    parser.add_option("-o", dest="outputRegistry", default="registry.sqlite3",
                      help="output registry (default=registry.sqlite3)")
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("Missing directory argument(s)")
    process(args, options.inputRegistry, options.outputRegistry)
