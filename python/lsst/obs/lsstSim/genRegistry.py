#!/usr/bin/env python

import os
import re
import sqlite3
import sys

import fsScanner
import lsst.afw.image as afwImage
import lsst.skypix as skypix

location = sys.argv[1]

rawTemplate = "imsim_%(visit)d_%(raft)s_%(sensor)s_%(channel)s_E%(exposure)03d.fits"

scanner = fsScanner.FsScanner(rawTemplate)

if os.path.exists("registry.sqlite3"):
    os.unlink("registry.sqlite3")

conn = sqlite3.connect("registry.sqlite3")
cmd = "create table raw (id integer primary key autoincrement,"
first = True
for f in scanner.getFields():
    if not first:
        cmd += ", "
    if scanner.isIntField(f):
        cmd += f + " int"
    else:
        cmd += f + " text"
    first = False
cmd += ", width int, height int, filter text"
cmd += ")"
 
conn.execute(cmd)

cmd = "create table raw_md (id integer references raw(id), key text, value text)"
conn.execute(cmd)
cmd = "create table raw_skytiles (id integer references raw(id), tile int)"
conn.execute(cmd)

conn.commit()

def ARCSEC_TO_RAD(arcsec):
    return arcsec / 3600.0 * 3.14159265358979/180.0

qsp = skypix.createQuadSpherePixelization()

def callback(path, dataId):
    cmd = "insert into raw values (NULL"
    idList = []
    for f in scanner.getFields():
        cmd += ", ?"
        if scanner.isIntField(f):
            idList.append(int(dataId[f]))
        elif f == "raft":
            idList.append(re.sub(r'R(\d)(\d)', r'R:\1,\2', dataId[f]))
        elif f == "sensor":
            idList.append(re.sub(r'S(\d)(\d)', r'S:\1,\2', dataId[f]))
        elif f == "channel":
            idList.append(re.sub(r'C(\d)(\d)', r'C:\1,\2', dataId[f]))
        else:
            idList.append(dataId[f])
    md = afwImage.readMetadata(path)
    width = md.get('NAXIS1')
    height = md.get('NAXIS2')
    filter = md.get('FILTER')
    idList.append(width)
    idList.append(height)
    idList.append(filter)
    cmd += ", ?, ?, ?)"
    conn.execute(cmd, idList)
    conn.commit()

    c = conn.cursor()
    c.execute("select last_insert_rowid()")
    for row in c:
        id = row[0]
        break

    for k in md.paramNames(True):
        cmd = "insert into raw_md values (?, ?, ?)"
        conn.execute(cmd, (id, k, md.get(k)))

    conn.commit()

    wcs = afwImage.makeWcs(md)
    # idList.append(wcs)
    tiles = qsp.intersect(skypix.imageToPolygon(
        wcs, width, height, ARCSEC_TO_RAD(15)))
    for t in tiles:
        cmd = "insert into raw_skytiles values (?, ?)"
        conn.execute(cmd, (id, t))

    conn.commit()

scanner.processDir(location, callback)

conn.close()
