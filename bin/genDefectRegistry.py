import glob
import os
import re
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
