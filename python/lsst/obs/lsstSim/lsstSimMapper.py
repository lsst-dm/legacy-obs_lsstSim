# 
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
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

import os
import re
import time
import lsst.daf.base as dafBase
import lsst.daf.persistence as dafPersist
import lsst.daf.butlerUtils as butlerUtils
import lsst.afw.image as afwImage
import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
import lsst.afw.cameraGeom as afwCameraGeom
import lsst.afw.cameraGeom.utils as cameraGeomUtils
import lsst.afw.image.utils as imageUtils
import lsst.pex.logging as pexLog
import lsst.pex.policy as pexPolicy

from lsst.obs.camera import CameraMapper

class LsstSimMapper(dafPersist.Mapper):
    def __init__(self, root=".", registry=None, calibRoot=None):
        dafPersist.Mapper.__init__(self, policy="LsstSimMapper.paf", module="obs_lsstSim",
								   policyDir="policy", root=root, registry=registry, calibRoot=calibRoot)

        self.keys = ["visit", "snap", "raft", "sensor", "channel", "skyTile", "filter"]

        self.filterIdMap = {
                'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'y': 5, 'i2': 5}

    def _transformId(self, dataId):
        actualId = dataId.copy()
        if actualId.has_key("sensorName"):
            m = re.search(r'R:(\d),(\d) S:(\d),(\d)', actualId['sensorName'])
            actualId['raft'] = m.group(1) + "," + m.group(2)
            actualId['sensor'] = m.group(3) + "," + m.group(4)
        if actualId.has_key("ccdName"):
            m = re.search(r'R:(\d),(\d) S:(\d),(\d)', actualId['ccdName'])
            actualId['raft'] = m.group(1) + "," + m.group(2)
            actualId['sensor'] = m.group(3) + "," + m.group(4)
        if actualId.has_key("channelName"):
            m = re.search(r'ID(\d+)', actualId['channelName'])
            channelNumber = int(m.group(1))
            channelX = channelNumber % 8
            channelY = channelNumber // 8
            actualId['channel'] = str(channelY) + "," + str(channelX)
        if actualId.has_key("ampName"):
            m = re.search(r'ID(\d+)', actualId['ampName'])
            channelNumber = int(m.group(1))
            channelX = channelNumber % 8
            channelY = channelNumber // 8
            actualId['channel'] = str(channelY) + "," + str(channelX)
        if actualId.has_key("exposure"):
            actualId['snap'] = actualId['exposure']
        if actualId.has_key("ccd"):
            actualId['sensor'] = actualId['ccd']
        if actualId.has_key("amp"):
            actualId['channel'] = actualId['amp']
        return actualId

    def _mapActualToPath(self, template, actualId):
        pathId = actualId.copy()
        if pathId.has_key("raft"):
            pathId['raft'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['raft'])
        if pathId.has_key("sensor"):
            pathId['sensor'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['sensor'])
        if pathId.has_key("channel"):
            pathId['channel'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['channel'])
        return template % pathId

    def _extractDetectorName(self, dataId):
        return "R:%(raft)s S:%(sensor)s" % dataId

    def _extractAmpId(self, dataId):
        m = re.match(r'(\d),(\d)', dataId['channel'])
        # Note that indices are swapped in the camera geometry vs. official
        # channel specification.
        return (self._extractDetectorName(dataId),
                int(m.group(2)), int(m.group(1)))

    def standardize_raw(self, mapping, item, dataId):
        dataId = self._transformId(dataId)
        exposure = afwImage.makeExposure(
                afwImage.makeMaskedImage(item.getImage()))
        md = item.getMetadata()
        exposure.setMetadata(md)
        wcs = afwImage.makeWcs(md)

        if md.exists("VERSION") and md.getInt("VERSION") < 40000:
        # Precess WCS based on actual observation date
            epoch = dafBase.DateTime(md.get("MJD-OBS"), dafBase.DateTime.MJD,
                    dafBase.DateTime.TAI).get(dafBase.DateTime.EPOCH)
            origin = wcs.getSkyOrigin()
            refCoord = afwCoord.Fk5Coord(
                    origin.getLongitude(afwCoord.DEGREES),
                    origin.getLatitude(afwCoord.DEGREES), epoch)
            newRefCoord = refCoord.precess(2000.)
            crval = afwGeom.PointD()
            crval.setX(newRefCoord.getRa(afwCoord.DEGREES))
            crval.setY(newRefCoord.getDec(afwCoord.DEGREES))
            wcs = afwImage.Wcs(crval, wcs.getPixelOrigin(),
                    wcs.getCDMatrix())

        exposure.setWcs(wcs)
        wcsMetadata = wcs.getFitsMetadata()
        for kw in wcsMetadata.paramNames():
            md.remove(kw)
        return self._standardize(mapping, exposure, dataId)
