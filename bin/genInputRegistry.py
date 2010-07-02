import glob
import os
import re
import sqlite as sqlite3
import sys
import lsst.daf.base as dafBase
import lsst.afw.image as afwImage
import lsst.skypix as skypix

if os.path.exists("registry.sqlite3"):
    os.unlink("registry.sqlite3")
conn = sqlite3.connect("registry.sqlite3")

cmd = "create table raw (id integer primary key autoincrement"
cmd += ", visit int, filter text, snap int"
cmd += ", raft text, sensor text, channel text"
cmd += ", taiObs text, expTime double)"
# cmd += ", unique(visit, snap, raft, sensor, channel))"
conn.execute(cmd)
cmd = "create table raw_skyTile (id integer, skyTile integer)"
# cmd += ", unique(id, skyTile), foreign key(id) references raw(id))"
conn.execute(cmd)
conn.execute("""create table raw_visit (visit int, filter text,
        taiObs text, expTime double, unique(visit))""")
conn.commit()

qsp = skypix.createQuadSpherePixelization()

root = sys.argv[1]
for snapdir in glob.glob(os.path.join(root, "raw", "v*-f*", "E00[01]")):
    for fits in glob.glob(os.path.join(snapdir, "R[0-4][0-4]", "S[0-2][0-2]",
        "imsim_*_R[0-4][0-4]_S[0-2][0-2]_C[01][0-7]_E00[01].fits*")):
        print fits
        m = re.search(r'raw/v(\d+)-f(\w)/E00(\d)/R(\d)(\d)/S(\d)(\d)/' +
                r'imsim_\1_R\4\5_S\6\7_C(\d)(\d)_E00\3\.fits',
                fits)
        if not m:
            print >>sys.stderr, "Warning: Unrecognized file:", fits
            continue

        visit, filter, snap, \
                raft1, raft2, sensor1, sensor2, channel1, channel2 = \
                m.groups()

        md = afwImage.readMetadata(fits)
        expTime = md.get("EXPTIME")
        mjdObs = md.get("MJD-OBS")
        taiObs = dafBase.DateTime(mjdObs, dafBase.DateTime.MJD,
                dafBase.DateTime.TAI).toString()[:-1]
        conn.execute("INSERT INTO raw VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
                (visit, filter, snap,
                    "%s,%s" % (raft1, raft2), "%s,%s" % (sensor1, sensor2),
                    "%s,%s" % (channel1, channel2), taiObs, expTime))
    
        for row in conn.execute("SELECT last_insert_rowid()"):
            id = row[0]
            break
    
        wcs = afwImage.makeWcs(md)
        poly = skypix.imageToPolygon(wcs, md.get("NAXIS1"), md.get("NAXIS2"),
                padRad=0.000075) # about 15 arcsec
        pix = qsp.intersect(poly)
        for skyTileId in pix:
            conn.execute("INSERT INTO raw_skyTile VALUES(?, ?)",
                    (id, skyTileId))

    conn.commit()

conn.execute("""insert into raw_visit
        select distinct visit, filter, taiObs, expTime from raw""")
conn.close()
