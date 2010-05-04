import os
import re
import sqlite3
import sys

if os.path.exists("defectRegistry.sqlite3"):
    os.unlink("defectRegistry.sqlite3")
conn = sqlite3.connect("defectRegistry.sqlite3")

cmd = "create table defect (id integer primary key autoincrement"
cmd += ", path text, version int"
cmd += ", validStart text, validEnd text)"
conn.execute(cmd)
conn.commit()

cmd = "INSERT INTO defect VALUES (NULL, ?, ?, ?, ?)"
conn.execute(cmd, ("Full_STA_def.paf", 1, "1970-01-01", "2037-12-31"))
conn.commit()

conn.close()
