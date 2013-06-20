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

import re

import lsst.daf.base as dafBase
import lsst.afw.image as afwImage
import lsst.afw.image.utils as afwImageUtils
import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
import lsst.pex.policy as pexPolicy

from lsst.daf.butlerUtils import CameraMapper

# Solely to get boost serialization registrations for Measurement subclasses
import lsst.meas.algorithms as measAlgo

class LsstSimMapper(CameraMapper):
    filterIdMap = {'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'y': 5, 'i2': 5}

    def __init__(self, inputPolicy=None, **kwargs):
        policyFile = pexPolicy.DefaultPolicyFile("obs_lsstSim", "LsstSimMapper.paf", "policy")
        policy = pexPolicy.Policy(policyFile)

        self.doFootprints = False
        if inputPolicy is not None:
            for kw in inputPolicy.paramNames(True):
                if kw == "doFootprints":
                    self.doFootprints = True
                else:
                    kwargs[kw] = inputPolicy.get(kw)

        super(LsstSimMapper, self).__init__(policy, policyFile.getRepositoryPath(), **kwargs)

        #The LSST Filters from L. Jones 04/07/10
        afwImageUtils.defineFilter('u', 364.59)
        afwImageUtils.defineFilter('g', 476.31)
        afwImageUtils.defineFilter('r', 619.42)
        afwImageUtils.defineFilter('i', 752.06)
        afwImageUtils.defineFilter('z', 866.85)
        afwImageUtils.defineFilter('y', 971.68, alias=['y4']) # official y filter
        # If/when y3 sim data becomes available, uncomment this and
        # modify the schema appropriately
        #afwImageUtils.defineFilter('y3', 1002.44) # candidate y-band

    @classmethod
    def _transformId(cls, dataId):
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
            actualId['channel'] = str(channelX) + "," + str(channelY)
        if actualId.has_key("ampName"):
            m = re.search(r'ID(\d+)', actualId['ampName'])
            channelNumber = int(m.group(1))
            channelX = channelNumber % 8
            channelY = channelNumber // 8
            actualId['channel'] = str(channelX) + "," + str(channelY)
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

    @classmethod
    def validate(cls, dataId):
        for component in ("raft", "sensor", "channel"):
            if component not in dataId:
                continue
            id = dataId[component]
            if not isinstance(id, str):
                raise RuntimeError, \
                        "%s identifier should be type str, not %s: %s" % \
                        (component.title(), type(id), repr(id))
            if not re.search(r'^(\d),(\d)$', id):
                raise RuntimeError, \
                        "Invalid %s identifier: %s" % (component, repr(id))
        return dataId

    @classmethod
    def _extractDetectorName(cls, dataId):
        return "R:%(raft)s S:%(sensor)s" % dataId

    @classmethod
    def getDataId(cls, visit, ccdId):
        """get dataId dict from visit and ccd identifier

        @param visit 32 or 64-bit depending on camera
        @param ccdId same as ccd.getId().getSerial()
        """
        x = str(ccdId)
        while len(x) < 4:
            x = '0' + x
        raft = x[0] + ',' + x[1]
        sensor  = x[2] + ',' + x[3]
        dataId = {'visit': long(visit), 'raft': raft, 'sensor': sensor}
        return dataId
    
    @classmethod
    def getDataIdFromCcdExposureId(cls, ccdExposureId):
        """Compute a data ID dict from a CCD exposure ID
        
        @param[in] ccdExposureId: CCD exposure ID, as computed by _computeCcdExposureId
        @return a data ID dict with keys visit, raft, sensor
        """
        visit = ccdExposureId >> 9
        rsId = ccdExposureId & 0b111111111
        sensorId = rsId % 10
        s2 = sensorId % 3
        s1 = (sensorId - s2) / 3
        
        raftId = (rsId - sensorId) / 10
        r2 = raftId % 5
        r1 = (raftId - r2) / 5
        return dict(
            visit = visit,
            sensor = "%d,%d" % (s1, s2),
            raft = "%d,%d" % (r1, r2),
        )

    @classmethod
    def _extractAmpId(cls, dataId):
        m = re.match(r'(\d),(\d)', dataId['channel'])
        # Note that indices are swapped in the camera geometry vs. official
        # channel specification.
        return (cls._extractDetectorName(dataId),
                int(m.group(1)), int(m.group(2)))

    @classmethod
    def _computeAmpExposureId(cls, dataId):
        #visit, snap, raft, sensor, channel):
        """Compute the 64-bit (long) identifier for an amp exposure.

        @param dataId (dict) Data identifier with visit, snap, raft, sensor, channel
        """

        pathId = cls._transformId(dataId)
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

    @classmethod
    def _computeCcdExposureId(cls, dataId):
        """Compute the 64-bit (long) identifier for a CCD exposure.

        @param dataId (dict) Data identifier with visit, raft, sensor
        """

        pathId = cls._transformId(dataId)
        visit = pathId['visit']
        raft = pathId['raft'] # "xy" e.g. "20"
        sensor = pathId['sensor'] # "xy" e.g. "11"

        r1, r2 = raft
        s1, s2 = sensor
        return (visit << 9) + \
                (long(r1) * 5 + long(r2)) * 10 + \
                (long(s1) * 3 + long(s2))

    @classmethod
    def _computeCoaddExposureId(cls, dataId, singleFilter):
        """Compute the 64-bit (long) identifier for a coadd.

        @param dataId (dict)       Data identifier with tract and patch.
        @param singleFilter (bool) True means the desired ID is for a single- 
                                   filter coadd, in which case dataId
                                   must contain filter.
        """
        tract = long(dataId['tract'])
        if tract < 0 or tract >= 128:
            raise RuntimeError('tract not in range [0,128)')
        patchX, patchY = map(int, dataId['patch'].split(','))
        for p in (patchX, patchY):
            if p < 0 or p >= 2**13:
                raise RuntimeError('patch component not in range [0, 8192)')
        id = (tract * 2**13 + patchX) * 2**13 + patchY
        if singleFilter:
            return id * 8 + cls.filterIdMap[dataId['filter']]
        return id

    @classmethod
    def _setAmpExposureId(cls, propertyList, dataId):
        propertyList.set("Computed_ampExposureId", cls._computeAmpExposureId(dataId))
        return propertyList

    @classmethod
    def _setCcdExposureId(cls, propertyList, dataId):
        propertyList.set("Computed_ccdExposureId", cls._computeCcdExposureId(dataId))
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
                origin.getLongitude(), origin.getLatitude(), epoch)
            newRefCoord = refCoord.precess(2000.)
            crval = afwGeom.PointD()
            crval.setX(newRefCoord.getRa().asDegrees())
            crval.setY(newRefCoord.getDec().asDegrees())
            wcs = afwImage.Wcs(crval, wcs.getPixelOrigin(),
                    wcs.getCDMatrix())
            exposure.setWcs(wcs)
        
        return exposure

###############################################################################

    @classmethod
    def bypass_ampExposureId(cls, datasetType, pythonType, location, dataId):
        return cls._computeAmpExposureId(dataId)
    @classmethod
    def bypass_ampExposureId_bits(cls, datasetType, pythonType, location, dataId):
        return 45
    @classmethod
    def bypass_ccdExposureId(cls, datasetType, pythonType, location, dataId):
        return cls._computeCcdExposureId(dataId)
    @classmethod
    def bypass_ccdExposureId_bits(cls, datasetType, pythonType, location, dataId):
        return 41

    @classmethod
    def bypass_goodSeeingCoaddId(cls, datasetType, pythonType, location, dataId):
        return cls._computeCoaddExposureId(dataId, True)
    @classmethod
    def bypass_goodSeeingCoaddId_bits(cls, datasetType, pythonType, location, dataId):
        return 1 + 7 + 13*2 + 3

    # Deep coadds use tract, patch, and filter just like good-seeing coadds
    bypass_deepCoaddId = bypass_goodSeeingCoaddId
    bypass_deepCoaddId_bits = bypass_goodSeeingCoaddId_bits

    @classmethod
    def bypass_chiSquaredCoaddId(cls, datasetType, pythonType, location, dataId):
        return cls._computeCoaddExposureId(dataId, False)
    @classmethod
    def bypass_chiSquaredCoaddId_bits(cls, datasetType, pythonType, location, dataId):
        return 1 + 7 + 13*2

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
        ad = dict(ampExposureId=ampExposureId, filterId=filterId)
        if self.doFootprints:
            ad["doFootprints"] = True
        return ad

    def _addSkytile(self, dataId):
        """Generic 'add' function to add skyTileId"""
        return {"skyTileId": dataId['skyTile']}

for dsType in ("icSrc", "src"):
    setattr(LsstSimMapper, "add_" + dsType, LsstSimMapper._addSources)
for dsType in ("source", "badSource", "invalidSource", "object"):
    setattr(LsstSimMapper, "add_" + dsType, LsstSimMapper._addSkytile)

###############################################################################

for dsType in ("raw", "postISR"):
    setattr(LsstSimMapper, "std_" + dsType + "_md",
            lambda self, item, dataId: self._setAmpExposureId(item, dataId))
for dsType in ("eimage", "postISRCCD", "visitim", "calexp", "calsnap"):
    setattr(LsstSimMapper, "std_" + dsType + "_md",
            lambda self, item, dataId: self._setCcdExposureId(item, dataId))
