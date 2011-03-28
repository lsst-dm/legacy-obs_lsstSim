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

import re

import lsst.daf.base as dafBase
import lsst.afw.image as afwImage
import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
import lsst.pex.policy as pexPolicy

from lsst.daf.butlerUtils import CameraMapper


class LsstSimMapper(CameraMapper):
    def __init__(self, **kwargs):
        policyFile = pexPolicy.DefaultPolicyFile("obs_lsstSim", "LsstSimMapper.paf", "policy")
        policy = pexPolicy.Policy(policyFile)
        super(LsstSimMapper, self).__init__(policy, policyFile.getRepositoryPath(), **kwargs)

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

        if actualId.has_key("raft"):
            actualId['raft'] = re.sub(r'(\d),(\d)', r'\1\2', actualId['raft'])
        if actualId.has_key("sensor"):
            actualId['sensor'] = re.sub(r'(\d),(\d)', r'\1\2', actualId['sensor'])
        if actualId.has_key("channel"):
            actualId['channel'] = re.sub(r'(\d),(\d)', r'\1\2', actualId['channel'])

        return actualId

    def _extractDetectorName(self, dataId):
        return "R:%(raft)s S:%(sensor)s" % dataId

    def _extractAmpId(self, dataId):
        m = re.match(r'(\d),(\d)', dataId['channel'])
        # Note that indices are swapped in the camera geometry vs. official
        # channel specification.
        return (self._extractDetectorName(dataId),
                int(m.group(2)), int(m.group(1)))

    def _computeAmpExposureId(self, dataId):
        #visit, snap, raft, sensor, channel):
        """Compute the 64-bit (long) identifier for an amp exposure.

        @param dataId (dict) Data identifier with visit, snap, raft, sensor, channel
        """

        pathId = self._transformId(dataId)
        visit = pathId['visit']
        snap = pathId['snap']
        raft = pathId['raft'] # "xy" e.g. "20"
        sensor = pathId['sensor'] # "xy" e.g. "11"
        channel = pathId['channel'] # "yx" e.g. "05" (NB: yx, not xy, in original comment)

        r1, r2 = raft
        s1, s2 = sensor
        c1, c2 = channel
        return (visit << 13) + (snap << 12) + \
                (long(r1) * 5 + long(r2)) * 160 + \
                (long(s1) * 3 + long(s2)) * 16 + \
                (long(c1) * 8 + long(c2))

    def _computeCcdExposureId(self, dataId):
        """Compute the 64-bit (long) identifier for a CCD exposure.

        @param dataId (dict) Data identifier with visit, raft, sensor
        """

        pathId = self._transformId(dataId)
        visit = pathId['visit']
        raft = pathId['raft'] # "xy" e.g. "20"
        sensor = pathId['sensor'] # "xy" e.g. "11"

        r1, r2 = raft
        s1, s2 = sensor
        return (visit << 9) + \
                (long(r1) * 5 + long(r2)) * 10 + \
                (long(s1) * 3 + long(s2))

    def _setAmpExposureId(self, propertyList, dataId):
        propertyList.set("Computed_ampExposureId", self._computeAmpExposureId(dataId))
        return propertyList

    def _setCcdExposureId(self, propertyList, dataId):
        propertyList.set("Computed_ccdExposureId", self._computeCcdExposureId(dataId))
        return propertyList

###############################################################################

    def std_raw(self, item, dataId):
        exposure = super(LsstSimMapper, self).std_raw(item, dataId)

        md = exposure.getMetadata()
        if md.exists("VERSION") and md.getInt("VERSION") < 16952:
        # Precess WCS based on actual observation date
            epoch = dafBase.DateTime(md.get("MJD-OBS"), dafBase.DateTime.MJD,
                    dafBase.DateTime.TAI).get(dafBase.DateTime.EPOCH)
            wcs = exposure.getWcs()
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
        
        return self._standardizeExposure(self.exposures['raw'], exposure, dataId)

###############################################################################

    def add_sdqaAmp(self, dataId):
        ampExposureId = self._computeAmpExposureId(dataId)
        return {"ampExposureId": ampExposureId, "sdqaRatingScope": "AMP"}

    def add_sdqaCcd(self, dataId):
        ccdExposureId = self._computeCcdExposureId(dataId)
        return {"ccdExposureId": ccdExposureId, "sdqaRatingScope": "CCD"}

    def _addSources(self, dataId):
        """Generic 'add' function to add ampExposureId and filterId"""
        # Note that sources are identified by what is called an ampExposureId,
        # but in this case all we have is a CCD.
        ampExposureId = self._computeCcdExposureId(dataId)
        pathId = self._transformId(dataId)
        filterId = self.filterIdMap[pathId['filter']]
        return {"ampExposureId": ampExposureId, "filterId": filterId}

    def _addSkytile(self, dataId):
        """Generic 'add' function to add skyTileId"""
        return {"skyTileId": dataId['skyTile']}

for dsType in ("icSrc", "src"):
    setattr(LsstSimMapper, "add_" + dsType, LsstSimMapper._addSources)
for dsType in ("source", "badSource", "invalidSource", "object", "badObject"):
    setattr(LsstSimMapper, "add_" + dsType, LsstSimMapper._addSkytile)

###############################################################################

for dsType in ("raw", "postISR"):
    setattr(LsstSimMapper, "std_" + dsType + "_md",
            lambda self, item, dataId: self._setAmpExposureId(item))
for dsType in ("eimage", "postISRCCD", "visitim", "calexp"):
    setattr(LsstSimMapper, "std_" + dsType + "_md",
            lambda self, item, dataId: self._setCcdExposureId(item))
