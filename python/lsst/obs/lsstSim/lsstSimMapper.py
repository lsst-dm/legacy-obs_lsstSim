from builtins import map
from past.builtins import basestring
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

__all__ = ["LsstSimMapper"]

import os
import re

import lsst.daf.base as dafBase
import lsst.afw.image.utils as afwImageUtils
import lsst.daf.persistence as dafPersist
from .makeLsstSimRawVisitInfo import MakeLsstSimRawVisitInfo

from lsst.obs.base import CameraMapper

# Solely to get boost serialization registrations for Measurement subclasses


class LsstSimMapper(CameraMapper):
    packageName = 'obs_lsstSim'

    MakeRawVisitInfoClass = MakeLsstSimRawVisitInfo

    _CcdNameRe = re.compile(r"R:(\d,\d) S:(\d,\d(?:,[AB])?)$")

    def __init__(self, inputPolicy=None, **kwargs):
        policyFile = dafPersist.Policy.defaultPolicyFile(self.packageName, "LsstSimMapper.yaml", "policy")
        policy = dafPersist.Policy(policyFile)

        self.doFootprints = False
        if inputPolicy is not None:
            for kw in inputPolicy.paramNames(True):
                if kw == "doFootprints":
                    self.doFootprints = True
                else:
                    kwargs[kw] = inputPolicy.get(kw)

        super(LsstSimMapper, self).__init__(policy, os.path.dirname(policyFile), **kwargs)
        self.filterIdMap = {'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'y': 5, 'i2': 5}

        # The LSST Filters from L. Jones 04/07/10
        afwImageUtils.resetFilters()
        afwImageUtils.defineFilter('u', lambdaEff=364.59, lambdaMin=324.0, lambdaMax=395.0)
        afwImageUtils.defineFilter('g', lambdaEff=476.31, lambdaMin=405.0, lambdaMax=552.0)
        afwImageUtils.defineFilter('r', lambdaEff=619.42, lambdaMin=552.0, lambdaMax=691.0)
        afwImageUtils.defineFilter('i', lambdaEff=752.06, lambdaMin=818.0, lambdaMax=921.0)
        afwImageUtils.defineFilter('z', lambdaEff=866.85, lambdaMin=922.0, lambdaMax=997.0)
        # official y filter
        afwImageUtils.defineFilter('y', lambdaEff=971.68, lambdaMin=975.0, lambdaMax=1075.0, alias=['y4'])
        # If/when y3 sim data becomes available, uncomment this and
        # modify the schema appropriately
        # afwImageUtils.defineFilter('y3', 1002.44) # candidate y-band

        # FTaken from hscMapper.py
        # The number of bits allocated for fields in object IDs, appropriate for
        # the default-configured Rings skymap.
        #
        # This shouldn't be the mapper's job at all; see #2797.
        LsstSimMapper._nbit_tract = 16
        LsstSimMapper._nbit_patch = 5
        LsstSimMapper._nbit_filter = 6
        LsstSimMapper._nbit_id = 64 - (LsstSimMapper._nbit_tract + \
                                       2 * LsstSimMapper._nbit_patch + \
                                       LsstSimMapper._nbit_filter)


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
        if "raft" in actualId:
            actualId['raft'] = re.sub(r'(\d),(\d)', r'\1\2', actualId['raft'])
        if "sensor" in actualId:
            actualId['sensor'] = actualId['sensor'].replace(",", "")
        if "channel" in actualId:
            actualId['channel'] = re.sub(r'(\d),(\d)', r'\1\2', actualId['channel'])
        return actualId

    def validate(self, dataId):
        for component in ("raft", "sensor", "channel"):
            if component not in dataId:
                continue
            val = dataId[component]
            if not isinstance(val, basestring):
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
        dataId = {'visit': int(visit)}
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
        # visit, snap, raft, sensor, channel):
        """Compute the 64-bit (long) identifier for an amp exposure.

        @param dataId (dict) Data identifier with visit, snap, raft, sensor, channel
        """

        pathId = self._transformId(dataId)
        visit = pathId['visit']
        snap = pathId['snap']
        raft = pathId['raft']  # "xy" e.g. "20"
        sensor = pathId['sensor']  # "xy" e.g. "11"
        channel = pathId['channel']  # "yx" e.g. "05" (NB: yx, not xy, in original comment)

        r1, r2 = raft
        s1, s2 = sensor
        c1, c2 = channel
        return (visit << 13) + (snap << 12) + \
            (int(r1) * 5 + int(r2)) * 160 + \
            (int(s1) * 3 + int(s2)) * 16 + \
            (int(c1) * 8 + int(c2))

    def _computeCcdExposureId(self, dataId):
        """Compute the 64-bit (long) identifier for a CCD exposure.

        @param dataId (dict) Data identifier with visit, raft, sensor
        """

        pathId = self._transformId(dataId)
        visit = pathId['visit']
        raft = pathId['raft']  # "xy" e.g. "20"
        sensor = pathId['sensor']  # "xy" e.g. "11"

        r1, r2 = raft
        s1, s2 = sensor
        return (visit << 9) + \
            (int(r1) * 5 + int(r2)) * 10 + \
            (int(s1) * 3 + int(s2))

    def _computeCoaddExposureId(self, dataId, singleFilter):
        """Compute the 64-bit (long) identifier for a coadd.

        @param dataId (dict)       Data identifier with tract and patch.
        @param singleFilter (bool) True means the desired ID is for a single-
                                   filter coadd, in which case dataId
                                   must contain filter.
        """
                # taken from hscMapper.py                                                                                     |
        tract = int(dataId['tract'])
        if tract < 0 or tract >= 2**LsstSimMapper._nbit_tract:
            raise RuntimeError('tract not in range [0,%d)' % (2**LsstSimMapper._nbit_tract))
        patchX, patchY = [int(patch) for patch in dataId['patch'].split(',')]
        for p in (patchX, patchY):
            if p < 0 or p >= 2**LsstSimMapper._nbit_patch:
                raise RuntimeError('patch component not in range [0, %d)' % \
                                   2**LsstSimMapper._nbit_patch)
        oid = (((tract << LsstSimMapper._nbit_patch) + patchX) << LsstSimMapper._nbit_patch) + patchY
        if singleFilter:
            return (oid << LsstSimMapper._nbit_filter) + \
                afwImageUtils.Filter(dataId['filter']).getId()
        return oid

    def bypass_deepMergedCoaddId_bits(self, *args, **kwargs):
        """The number of bits used up for patch ID bits"""
        return 64 - self._nbit_id

    def bypass_deepMergedCoaddId(self, datasetType, pythonType, location, dataId):
        return self._computeCoaddExposureId(dataId, False)

    def bypass_dcrMergedCoaddId_bits(self, *args, **kwargs):
        """The number of bits used up for patch ID bits"""
        return self.bypass_deepMergedCoaddId_bits(*args, **kwargs)

    def bypass_dcrMergedCoaddId(self, datasetType, pythonType, location, dataId):
        return self.bypass_deepMergedCoaddId(datasetType, pythonType, location, dataId)

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
        md = item.getMetadata()
        if md.exists("VERSION") and md.getInt("VERSION") < 16952:
            # CRVAL is FK5 at date of observation
            dateObsTaiMjd = md.get("TAI")
            dateObs = dafBase.DateTime(dateObsTaiMjd,
                                       system=dafBase.DateTime.MJD,
                                       scale=dafBase.DateTime.TAI)
            correctedEquinox = dateObs.get(system=dafBase.DateTime.EPOCH,
                                           scale=dafBase.DateTime.TAI)
            md.set("EQUINOX", correctedEquinox)
            md.set("RADESYS", "FK5")
            print("****** changing equinox to", correctedEquinox)
        return super(LsstSimMapper, self).std_raw(item, dataId)

    def std_eimage(self, item, dataId):
        """Standardize a eimage dataset by converting it to an Exposure instead of an Image"""
        return self._standardizeExposure(self.exposures['eimage'], item, dataId, trimmed=True)

###############################################################################

    def bypass_ampExposureId(self, datasetType, pythonType, location, dataId):
        return self._computeAmpExposureId(dataId)

    def bypass_ampExposureId_bits(self, datasetType, pythonType, location, dataId):
        return 45

    def bypass_ccdExposureId(self, datasetType, pythonType, location, dataId):
        return self._computeCcdExposureId(dataId)

    def bypass_ccdExposureId_bits(self, datasetType, pythonType, location, dataId):
        return 41

    def bypass_deepCoaddId(self, datasetType, pythonType, location, dataId):
        return self._computeCoaddExposureId(dataId, True)

    def bypass_deepCoaddId_bits(self, datasetType, pythonType, location, dataId):
        return 1 + 7 + 13*2 + 3

    def bypass_dcrCoaddId(self, datasetType, pythonType, location, dataId):
        return self.bypass_deepCoaddId(datasetType, pythonType, location, dataId)

    def bypass_dcrCoaddId_bits(self, datasetType, pythonType, location, dataId):
        return self.bypass_deepCoaddId_bits(datasetType, pythonType, location, dataId)

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
