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
        self.filterIdMap = {
                'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'y': 5, 'i2': 5}

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

    def _raftSensorFromCcdName(self, ccdName):
        """Parse a ccd name and return raft and sensor

        @param[in] ccdName: detector name, as a string in the form R:x,x Sx,x[,c]
            where c is A or B (e.g. "R02_S11")
        @return (raft, sensor), each as a string in the form x,y[,c] (e.g. "02");
        @raise RuntimeError if ccdName cannot be parsed
        """
        m = re.match(r"R:(\d),(\d) S(\d),(\d)(,[aAbB])?$", ccdName)
        if m is None:
            raise RuntimeError("Cannot parse ccdName=%r" % (ccdName,))
        raft = m.group(1) + m.group(2)
        sensor = m.group(3) + m.group(4)
        if m.group(5) is not None:
            sensor += "," + m.group(5)
        return (raft, sensor)

    def _transformId(self, dataId):
        """Transform an ID dict into standard form for LSST

        Standard keys are as follows:
        - raft: in the form <x><y> or <x>,<y>
        - sensor: in the form <x><y>[<c>] or <x>,<y>,<c> where <c> = A or B
        - amp = channel: in the form <x><y> or <x>,<y>
        - ccd: ccd name in the form R:<x>,<y> S:<x>,<y>[,<c>] or R<x><y>_S<x><y>[<c>]
        - snap: exposure number: form?

        If multiple forms are shown, the value is transformed into the first one.

        If ccd is found, it is used to set raft and sensor (if not already set).
        If raft and sensor are found, they are used to set ccd (if not already set).

        Other supported keys, which are used to set the above, if found:
        - ccdName: an alias for ccd
        - channelName, ampName: aliases for channel
        - exposure: if found and snap is not present, used to set snap

        @param dataId[in] (dict) Dataset identifier; this must not be modified
        @return (dict) Transformed dataset identifier
        @raise RuntimeError if a value is not valid
        """
        actualId = dataId.copy()
        for ccdAlias in ("ccd", "ccdName"):
            if ccdAlias in actualId:
                ccdName = actualId[ccdAlias]
                m = re.match(r'R:?(\d),?(\d)[ _]S:?(\d),?(\d),?([AB])?$', ccdName, re.IGNORECASE)
                if m is None:
                    raise RuntimeError("Invalid value for %s: %r" % (ccdAlias, ccdName))
                actualId.setdefault("raft", m.group(1) + m.group(2))
                sensorName = m.group(3) + m.group(4)
                if m.group(5):
                    sensorName += m.group(5).upper()
                actualId.setdefault("sensor", sensorName)
                break
        if "raft" in actualId:
            raftName = actualId["raft"]
            if not re.match(r"\d,?\d$", raftName):
                raise RuntimeError("Invalid value for raft: %r" % (raftName,))
            actualId["raft"] = raftName.replace(",", "")
        if "sensor" in actualId:
            sensorName = actualId["sensor"]
            if not re.match(r"\d,?\d,?[AB]?$", sensorName, re.IGNORECASE):
                raise RuntimeError("Invalid value for sensor: %r" % (sensorName,))
            sensorName = sensorName.replace(",", "")
            actualId["sensor"] = sensorName
            if "raft" in actualId:
                actualId["ccd"] = "R:%s S:%s" % (",".join(actualId["raft"]), ",".join(sensorName))
        if "ampNum" in actualId and "channel" not in actualId:
            m = re.match(r'ID(\d+)$', actualId['amp'])
            channelNumber = int(m.group(1))
            channelX = channelNumber % 8
            channelY = channelNumber // 8
            channel = str(channelX) + str(channelY)
            actualId['channel'] = channel
        for channelAlias in ("channel", "amp", "channelName", "ampName"):
            if channelAlias in actualId:
                channel = actualId[channelAlias]
                if not re.match(r"\d,?\d$", channel):
                    raise RuntimeError("Invalid value for %s: %r" % (channelAlias, channel))
                channel = channel.replace(",", "")
                actualId["channel"] = channel
                break
        if "exposure" in actualId:
            actualId['snap'] = actualId['exposure']
        return actualId

    def validate(self, dataId):
        return self._transformId(dataId)

    def getDataId(self, visit, ccdId):
        """get dataId dict from visit and ccd identifier

        @param visit 32 or 64-bit depending on camera
        @param ccdId detector name: same as detector.getName()
        """
        dataId = {'visit': long(visit)}
        dataId['raft'], dataId['sensor'] = self._raftSensorFromCcdName(ccdId)
        return dataId

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

    def _computeCoaddExposureId(self, dataId, singleFilter):
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
            return id * 8 + self.filterIdMap[dataId['filter']]
        return id

    @staticmethod
    def getShortCcdName(ccdName):
        """Convert a CCD name to a form useful as a filename

        This LSST version converts spaces to underscores and elides colons and commas.
        """
        return ccdName.replace(" ", "_").replace(":", "").replace(",", "")

    def _getCcdSerial(self, dataId):
        """Return value of ccdSerial field in defects registry based on data ID

        The LSST uses an integer made from <raftX><raftY><sensorX><sensorY>,
        e.g. detector R02_S11 has ccdSerial 211
        """
        raft = dataId["raft"]
        sensor = dataId["sensor"]
        return int("%d%d%d%d" % (raft[0], raft[2], sensor[0], sensor[2]))

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

    def bypass_ampExposureId(self, datasetType, pythonType, location, dataId):
        return self._computeAmpExposureId(dataId)
    def bypass_ampExposureId_bits(self, datasetType, pythonType, location, dataId):
        return 45
    def bypass_ccdExposureId(self, datasetType, pythonType, location, dataId):
        return self._computeCcdExposureId(dataId)
    def bypass_ccdExposureId_bits(self, datasetType, pythonType, location, dataId):
        return 41

    def bypass_goodSeeingCoaddId(self, datasetType, pythonType, location, dataId):
        return self._computeCoaddExposureId(dataId, True)
    def bypass_goodSeeingCoaddId_bits(self, datasetType, pythonType, location, dataId):
        return 1 + 7 + 13*2 + 3

    # Deep coadds use tract, patch, and filter just like good-seeing coadds
    bypass_deepCoaddId = bypass_goodSeeingCoaddId
    bypass_deepCoaddId_bits = bypass_goodSeeingCoaddId_bits

    def bypass_chiSquaredCoaddId(self, datasetType, pythonType, location, dataId):
        return self._computeCoaddExposureId(dataId, False)
    def bypass_chiSquaredCoaddId_bits(self, datasetType, pythonType, location, dataId):
        return 1 + 7 + 13*2

###############################################################################

    def add_sdqaAmp(self, dataId):
        ampExposureId = self._computeAmpExposureId(dataId)
        return {"ampExposureId": ampExposureId, "sdqaRatingScope": "AMP"}

    def add_sdqaCcd(self, dataId):
        ccdExposureId = self._computeCcdExposureId(dataId)
        return {"ccdExposureId": ccdExposureId, "sdqaRatingScope": "CCD"}

###############################################################################

for dsType in ("raw", "postISR"):
    setattr(LsstSimMapper, "std_" + dsType + "_md",
            lambda self, item, dataId: self._setAmpExposureId(item, dataId))
for dsType in ("eimage", "postISRCCD", "visitim", "calexp", "calsnap"):
    setattr(LsstSimMapper, "std_" + dsType + "_md",
            lambda self, item, dataId: self._setCcdExposureId(item, dataId))
