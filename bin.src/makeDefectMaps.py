#!/usr/bin/env python2
#
# LSST Data Management System
# Copyright 2014 LSST Corporation.
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
import numpy
import time
import pyfits
import lsst.afw.image as ai
import lsst.afw.detection as afwDetection
import lsst.afw.cameraGeom as cameraGeom
import sys
rx = int(sys.argv[1])
ry = int(sys.argv[2])
sx = int(sys.argv[3])
sy = int(sys.argv[4])
ha = None
if len(sys.argv) > 5:
    ha = str(sys.argv[5])
if ha is None:
    mi = ai.MaskedImageF("QE_R%i%i_S%i%i.fits.gz"%(rx, ry, sx, sy))
elif ha == 'A':
    mi = ai.MaskedImageF("QE_R%i%i_S%i%i_C0.fits.gz"%(rx, ry, sx, sy))
elif ha == 'B':
    mi = ai.MaskedImageF("QE_R%i%i_S%i%i_C1.fits.gz"%(rx, ry, sx, sy))
else:
    raise ValueError("passed an invalid value for ha")

im = mi.getImage()
arr = im.getArray()
deadidx = numpy.where(arr == 0.)
hotidx = numpy.where(arr > 1.1)
arr[deadidx] = 2.
arr[hotidx] = 3.
im2 = ai.makeImageFromArray(arr)
thresh = afwDetection.Threshold(1.1)
fs = afwDetection.FootprintSet(im2, thresh)
x0 = []
y0 = []
width = []
height = []
for f in fs.getFootprints():
    for bbox in afwDetection.footprintToBBoxList(f):
        bbox = cameraGeom.rotateBBoxBy90(bbox, 3, im.getBBox().getDimensions())
        x0.append(bbox.getMinX())
        y0.append(bbox.getMinY())
        width.append(bbox.getWidth())
        height.append(bbox.getHeight())

head = pyfits.Header()
cmap = {'A': (0, 0), 'B': (0, 1)}
if ha is not None:
    head.update('SERIAL', int('%i%i%i%i%i%i' %
                              (rx, ry, sx, sy, cmap[ha][0], cmap[ha][1])), 'Serial of the sensor')
    head.update('NAME', 'R:%i,%i S:%i,%i,%c'%(rx, ry, sx, sy, ha), 'Name of sensor for this defect map')
else:
    head.update('SERIAL', int('%i%i%i%i'%(rx, ry, sx, sy)), 'Serial of the sensor')
    head.update('NAME', 'R:%i,%i S:%i,%i'%(rx, ry, sx, sy), 'Name of sensor for this defect map')
head.update('CDATE', time.asctime(time.gmtime()), 'UTC of creation')

# Need to transpose from the phosim on disk orientation
col1 = pyfits.Column(name='y0', format='I', array=numpy.array(y0))
col2 = pyfits.Column(name='x0', format='I', array=numpy.array(x0))
col3 = pyfits.Column(name='width', format='I', array=numpy.array(width))
col4 = pyfits.Column(name='height', format='I', array=numpy.array(height))
cols = pyfits.ColDefs([col1, col2, col3, col4])
tbhdu = pyfits.new_table(cols, header = head)
hdu = pyfits.PrimaryHDU()
thdulist = pyfits.HDUList([hdu, tbhdu])
if ha is None:
    thdulist.writeto("defects%i%i%i%i.fits"%(rx, ry, sx, sy))
else:
    thdulist.writeto("defects%i%i%i%i%c.fits"%(rx, ry, sx, sy, ha))
