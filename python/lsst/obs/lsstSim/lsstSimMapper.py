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
    packageName = 'obs_lsstSim'

    _CcdNameRe = re.compile(r"R:(\d,\d) S:(\d,\d(?:,[AB])?)$")
    def __init__(self, inputPolicy=None, **kwargs):
        policyFile = pexPolicy.DefaultPolicyFile(self.packageName, "LsstSimMapper.paf", "policy")
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

    def _transformId(self, dataId):
        """Transform an ID dict into standard form for LSST

        Standard keys are as follows:
        - raft: in the form <x>,<y>
        - sensor: in the form <x>,<y>,<c> where <c> = A or B
        - channel: in the form <x>,<y>
        - snap: exposure number

        Other supported keys, which are used to set the above, if not already set:
        - ccd: an alias for sensor (hence NOT the full ccd name)
        - ccdName or sensorName: full ccd name in the form R:<x>,<y> S:<x>,<y>[,<c>]
            if found, used to set raft and sensor, if not already set
        - channelName, ampName: an alternate way to specify channel, in the form: IDxx
        - amp: an alias for channel
        - exposure: an alias for snap

        @param dataId[in] (dict) Dataset identifier; this must not be modified
        @return (dict) Transformed dataset identifier
        @raise RuntimeError if a value is not valid
        """
        actualId = dataId.copy()
        for ccdAlias in ("ccdName", "sensorName"):
            if ccdAlias in actualId:
                ccdName = actualId[ccdAlias].upper()
                m = self._CcdNameRe.match(ccdName)
                if m is None:
                    raise RuntimeError("Invalid value for %s: %r" % (ccdAlias, ccdName))
                actualId.setdefault("raft", m.group(1))
                actualId.setdefault("sensor", m.group(2))
                break
        if "ccd" in actualId:
            actualId.setdefault("sensor", actualId["ccd"])
        if "amp" in actualId:
            actualId.setdefault("channel", actualId["amp"])
        elif "channel" not in actualId:
            for ampName in ("ampName", "channelName"):
                if ampName in actualId:
                    m = re.match(r'ID(\d+)$', actualId[ampName])
                    channelNumber = int(m.group(1))
                    channelX = channelNumber % 8
                    channelY = channelNumber // 8
                    actualId['channel'] = str(channelX) + "," + str(channelY)
                    break
        if "exposure" in actualId:
            actualId.setdefault("snap", actualId["exposure"])

        # why strip out the commas after carefully adding them?
        if actualId.has_key("raft"):
            actualId['raft'] = re.sub(r'(\d),(\d)', r'\1\2', actualId['raft'])
        if actualId.has_key("sensor"):
            actualId['sensor'] = actualId['sensor'].replace(",", "")
        if actualId.has_key("channel"):
            actualId['channel'] = re.sub(r'(\d),(\d)', r'\1\2', actualId['channel'])
        return actualId

    def validate(self, dataId):
        for component in ("raft", "sensor", "channel"):
            if component not in dataId:
                continue
            val = dataId[component]
            if not isinstance(val, str):
                raise RuntimeError(
                    "%s identifier should be type str, not %s: %r" % (component.title(), type(val), val))
            if component == "sensor":
                if not re.search(r'^\d,\d(,[AB])?$', val):
                    raise RuntimeError("Invalid %s identifier: %r" % (component, val))
            else:
                if not re.search(r'^(\d),(\d)$', val):
                    raise RuntimeError("Invalid %s identifier: %r" % (component, val))
        return dataId

    def _extractDetectorName(self, dataId):
        return "R:%(raft)s S:%(sensor)s" % dataId

    def getDataId(self, visit, ccdId):
        """get dataId dict from visit and ccd identifier

        @param visit 32 or 64-bit depending on camera
        @param ccdId detector name: same as detector.getName()
        """
        dataId = {'visit': long(visit)}
        m = self._CcdNameRe.match(ccdId)
        if m is None:
            raise RuntimeError("Cannot parse ccdId=%r" % (ccdId,))
        dataId['raft'] = m.group(0)
        dataId['sensor'] = m.group(1)
        return dataId

    def _extractAmpId(self, dataId):
        m = re.match(r'(\d),(\d)', dataId['channel'])
        # Note that indices are swapped in the camera geometry vs. official
        # channel specification.
        return (self._extractDetectorName(dataId),
                int(m.group(1)), int(m.group(2)))

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
    # I don't actually know what to say about how many bits are taaken.  This is a WAG
    _nbit_id = 30
    def bypass_deepCoaddId_bits(self, *args, **kwargs):
        """The number of bits used up for patch ID bits"""
        return 64 - self._nbit_id

    def bypass_deepCoaddId(self, datasetType, pythonType, location, dataId):
        return self._computeCoaddExposureId(dataId, True)

    def bypass_deepMergedCoaddId_bits(self, *args, **kwargs):
        """The number of bits used up for patch ID bits"""
        return 64 - self._nbit_id

    def bypass_deepMergedCoaddId(self, datasetType, pythonType, location, dataId):
        return self._computeCoaddExposureId(dataId, False)

    @staticmethod
    def getShortCcdName(ccdId):
        """Convert a CCD name to a form useful as a filename

        This LSST version converts spaces to underscores and elides colons and commas.
        """
        return re.sub("[:,]", "", ccdId.replace(" ", "_"))

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
