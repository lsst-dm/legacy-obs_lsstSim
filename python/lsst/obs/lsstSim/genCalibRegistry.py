#!/usr/bin/env python

import os
import re
import sqlite3
import sys

import lsst.daf.butlerUtils as butlerUtils
import lsst.afw.image as afwImage
import lsst.skypix as skypix

location = sys.argv[1]

templates = {}
templates['bias'] = "bias/imsim_0_%(raft)s_%(sensor)s_%(channel)s_E000.fits"
templates['dark'] = "dark/imsim_1_%(raft)s_%(sensor)s_%(channel)s_E000.fits"
templates['flat'] = "flat_%(filter)s/imsim_2_%(raft)s_%(sensor)s_%(channel)s_E000.fits"
templates['fringe'] = "flat_%(filter)s/imsim_2_%(raft)s_%(sensor)s_%(channel)s_E000.fits"

calibs = templates.keys()
scanners = {}
for c in calibs:
    scanners[c] = butlerUtils.FsScanner(templates[c])

if os.path.exists("calibRegistry.sqlite3"):
    os.unlink("calibRegistry.sqlite3")

conn = sqlite3.connect("calibRegistry.sqlite3")
for c in calibs:
    cmd = "create table %s (id integer primary key autoincrement" % (c,)
    for f in scanners[c].getFields():
        cmd += ", "
        if scanners[c].isInt(f):
            cmd += f + " int"
        elif scanners[c].isFloat(f):
            cmd += f + " float"
        else:
            cmd += f + " text"
    cmd += ", width int, height int"
    cmd += ")"
 
    conn.execute(cmd)

    cmd = "create table %s_md (id integer references raw(id)," % (c,)
    cmd += "key text, value text)"
    conn.execute(cmd)

conn.commit()

def jointCallback(calib, path, dataId):
    cmd = "insert into %s values (NULL" % (calib,)
    idList = []
    for f in scanners[calib].getFields():
        cmd += ", ?"
        if f == "raft":
            idList.append(re.sub(r'R(\d)(\d)', r'R:\1,\2', dataId[f]))
        elif f == "sensor":
            idList.append(re.sub(r'S(\d)(\d)', r'S:\1,\2', dataId[f]))
        elif f == "channel":
            idList.append(re.sub(r'C(\d)(\d)', r'\1\2', dataId[f]))
        else:
            idList.append(dataId[f])
    md = afwImage.readMetadata(path)
    width = md.get('NAXIS1')
    height = md.get('NAXIS2')
    idList.append(width)
    idList.append(height)
    cmd += ", ?, ?)"
    conn.execute(cmd, idList)
    conn.commit()

    c = conn.cursor()
    c.execute("select last_insert_rowid()")
    for row in c:
        id = row[0]
        break

    for k in md.paramNames(True):
        cmd = "insert into %s_md values (?, ?, ?)" % (calib,)
        conn.execute(cmd, (id, k, str(md.get(k))))

    conn.commit()

for c in calibs:
    callback = lambda path, dataId: jointCallback(c, path, dataId)
    scanners[c].processPath(location, callback)

conn.close()
