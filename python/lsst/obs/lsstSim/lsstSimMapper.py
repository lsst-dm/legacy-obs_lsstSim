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
from lsst.daf.persistence import Mapper, ButlerLocation, LogicalLocation
import lsst.daf.butlerUtils as butlerUtils
import lsst.afw.image as afwImage
import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
import lsst.afw.cameraGeom as afwCameraGeom
import lsst.afw.cameraGeom.utils as cameraGeomUtils
import lsst.afw.image.utils as imageUtils
import lsst.pex.logging as pexLog
import lsst.pex.policy as pexPolicy

# Solely to get boost serialization registrations for Measurement subclasses
import lsst.meas.algorithms as measAlgo
import lsst.meas.multifit as measMultifit

class LsstSimMapper(Mapper):
    def __init__(self, policy=None, root=".", registry=None, calibRoot=None):
        Mapper.__init__(self)

        self.log = pexLog.Log(pexLog.getDefaultLog(), "LsstSimMapper")

        self.policy = policy
        if self.policy is None:
            self.policy = pexPolicy.Policy()
        defaultFile = pexPolicy.DefaultPolicyFile("obs_lsstSim",
                "LsstSimMapperDictionary.paf", "policy")
        self.repositoryPath = defaultFile.getRepositoryPath()
        defaultPolicy = pexPolicy.Policy.createPolicy(defaultFile,
                self.repositoryPath)
        self.policy.mergeDefaults(defaultPolicy)

        self.root = root
        if self.policy.exists('root'):
            self.root = self.policy.getString('root')
        self.calibRoot = calibRoot
        if self.policy.exists('calibRoot'):
            self.calibRoot = self.policy.getString('calibRoot')
        if self.calibRoot is None:
            self.calibRoot = self.root

        # Do any location map substitutions
        self.root = LogicalLocation(self.root).locString()
        self.calibRoot = LogicalLocation(self.calibRoot).locString()

        if not os.path.exists(self.root):
            self.log.log(pexLog.Log.WARN,
                    "Root directory not found: %s" % (root,))
        if not os.path.exists(self.calibRoot):
            self.log.log(pexLog.Log.WARN,
                    "Calibration root directory not found: %s" % (calibRoot,))

        for datasetType in ["raw", "bias", "dark", "flat", "fringe",
            "postISR", "postISRCCD", "sdqaAmp", "sdqaCcd",
            "icSrc", "icMatch", "visitim", "psf", "apCorr", "calexp", "src",
            "sourceHist", "badSourceHist", "source", "badSource",
            "invalidSource", "object", "badObject"]:
            key = datasetType + "Template"
            if self.policy.exists(key):
                setattr(self, key, self.policy.getString(key))

        self._setupRegistry(registry)
        self.keys = ["visit", "snap", "raft", "sensor", "channel", "skyTile"]
        self.keys.append("filter")

        self.cameraPolicyLocation = os.path.join(self.repositoryPath,
                self.policy.getString('cameraDescription'))
        cameraPolicy = cameraGeomUtils.getGeomPolicy(self.cameraPolicyLocation)
        self.camera = cameraGeomUtils.makeCamera(cameraPolicy)

        self.defectRegistry = None
        if self.policy.exists('defectPath'):
            self.defectPath = os.path.join(
                    self.repositoryPath, self.policy.getString('defectPath'))
            defectRegistryLocation = os.path.join(
                    self.defectPath, "defectRegistry.sqlite3")
            self.defectRegistry = \
                    butlerUtils.Registry.create(defectRegistryLocation)

        filterPolicy = pexPolicy.Policy.createPolicy(
                os.path.join(self.repositoryPath,
                    self.policy.getString('filterDescription')))
        imageUtils.defineFiltersFromPolicy(filterPolicy, reset=True)

        self.filterIdMap = {
                'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'y': 5, 'i2': 5}

    def getKeys(self):
        return self.keys

###############################################################################
#
# Utility functions
#
###############################################################################

    def _setupRegistry(self, registry):
        registryPath = registry
        if registryPath is None and self.policy.exists('registryPath'):
            registryPath = self.policy.getString('registryPath')
            registryPath = LogicalLocation(registryPath).locString()
            if not os.path.exists(registryPath):
                self.log.log(pexLog.Log.WARN,
                        "Unable to locate registry at registryPath: %s" %
                        (registryPath,))
                registryPath = None
        if registryPath is None:
            registryPath = os.path.join(self.root, "registry.sqlite3")
            if not os.path.exists(registryPath):
                self.log.log(pexLog.Log.WARN,
                        "Unable to locate registry in root: %s" %
                        (registryPath,))
                registryPath = None
        if registryPath is None:
            registryPath = "registry.sqlite3"
            if not os.path.exists(registryPath):
                self.log.log(pexLog.Log.WARN,
                        "Unable to locate registry in current dir: %s" %
                        (registryPath,))
                registryPath = None
        if registryPath is not None:
            self.log.log(pexLog.Log.INFO,
                    "Registry loaded from %s" % (registryPath,))
            self.registry = butlerUtils.Registry.create(registryPath)
        else:
            # TODO Try a FsRegistry(self.root) for raw (and all outputs?)
            self.log.log(pexLog.Log.WARN,
                    "No registry loaded; proceeding without one")
            self.registry = None

    def _needFilter(self, dataId):
        if dataId.has_key('filter'):
            return dataId
        actualId = dataId.copy()
        if not dataId.has_key('visit'):
            raise KeyError, \
                    "Data id missing visit key, cannot look up filter\n" + \
                    str(dataId)
        if not hasattr(self, 'registry') or self.registry is None:
            raise RuntimeError, "No registry available to find filter for visit"
        rows = self.registry.executeQuery(("filter",), ("raw_visit",),
                {'visit': "?"}, None, (dataId['visit'],))
        if len(rows) != 1:
            raise RuntimeError, \
                    "Unable to find unique filter for visit %d: %s" % \
                    (dataId['visit'], str(rows))
        actualId['filter'] = rows[0][0]
        return actualId

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

    def _mapActualToPath(self, actualId):
        pathId = actualId.copy()
        if pathId.has_key("raft"):
            pathId['raft'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['raft'])
        if pathId.has_key("sensor"):
            pathId['sensor'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['sensor'])
        if pathId.has_key("channel"):
            pathId['channel'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['channel'])
        return pathId

    def _extractDetectorName(self, dataId):
        return "R:%(raft)s S:%(sensor)s" % dataId

    def _extractAmpId(self, dataId):
        m = re.match(r'(\d),(\d)', dataId['channel'])
        # Note that indices are swapped in the camera geometry vs. official
        # channel specification.
        return (self._extractDetectorName(dataId),
                int(m.group(2)), int(m.group(1)))

    def _setAmpDetector(self, item, dataId):
        ampId = self._extractAmpId(dataId)
        detector = cameraGeomUtils.findAmp(
                self.camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        self._addDefects(dataId, amp=detector)
        item.setDetector(detector)

    def _setCcdDetector(self, item, dataId):
        ccdId = self._extractDetectorName(dataId)
        detector = cameraGeomUtils.findCcd(self.camera, afwCameraGeom.Id(ccdId))
        self._addDefects(dataId, ccd=detector)
        item.setDetector(detector)

    def _setFilter(self, item, dataId):
        md = item.getMetadata()
        filterName = None
        if md.exists("FILTER"):
            filterName = item.getMetadata().get("FILTER").strip()
        if filterName is None:
            rows = self.registry.executeQuery(("filter",), ("raw_visit",),
                    {'visit': "?"}, None, (dataId['visit'],))
            if len(rows) != 1:
                raise RuntimeError, \
                        "Unable to find unique filter for visit %d: %s" % \
                        (dataId['visit'], str(rows))
            filterName = rows[0][0]
        filter = afwImage.Filter(filterName)
        item.setFilter(filter)

    def _setTimes(self, item, dataId):
        md = item.getMetadata()
        calib = item.getCalib()
        if md.exists("EXPTIME"):
            expTime = md.get("EXPTIME")
            calib.setExptime(expTime)
            md.remove("EXPTIME")
        else:
            expTime = calib.getExptime()
        if md.exists("MJD-OBS"):
            obsStart = dafBase.DateTime(md.get("MJD-OBS"),
                    dafBase.DateTime.MJD, dafBase.DateTime.TAI)
            obsMidpoint = obsStart.nsecs() + long(expTime * 1000000000L / 2)
            calib.setMidTime(dafBase.DateTime(obsMidpoint))

    def _standardizeExposure(self, item, dataId, isAmp=False):
        stripFits(item.getMetadata())
        if isAmp:
            self._setAmpDetector(item, dataId)
        else:
            self._setCcdDetector(item, dataId)
        self._setFilter(item, dataId)
        self._setTimes(item, dataId)
        return item

    def _standardizeCalib(self, item, dataId, filterNeeded):
        stripFits(item.getMetadata())
        self._setAmpDetector(item, dataId)
        if filterNeeded:
            self._setFilter(item, dataId)
        return item

    def _defectLookup(self, dataId, ccdSerial):
        if self.defectRegistry is None:
            return None

        rows = self.registry.executeQuery(("taiObs",), ("raw_visit",),
                {"visit": "?"}, None, (dataId['visit'],))
        if len(rows) == 0:
            return None
        assert len(rows) == 1
        taiObs = rows[0][0]

        rows = self.defectRegistry.executeQuery(("path",), ("defect",),
                {"ccdSerial": "?"},
                ("DATETIME(?)", "DATETIME(validStart)", "DATETIME(validEnd)"),
                (ccdSerial, taiObs))
        if len(rows) == 0:
            return None
        assert len(rows) == 1
        return os.path.join(self.defectPath, rows[0][0])

    def _addDefects(self, dataId, amp=None, ccd=None):
        if ccd is None:
            ccd = afwCameraGeom.cast_Ccd(amp.getParent())
        if len(ccd.getDefects()) > 0:
            # Assume we have loaded them properly already
            return
        defectFits = self._defectLookup(dataId, ccd.getId().getSerial())
        if defectFits is not None:
            defectDict = cameraGeomUtils.makeDefectsFromFits(defectFits)
            ccdDefects = None
            for k in defectDict.keys():
                if k == ccd.getId():
                    ccdDefects = defectDict[k]
                    break
            if ccdDefects is None:
                raise RuntimeError, "No defects for ccd %s in %s" % \
                        (str(ccd.getId()), defectFits)
            ccd.setDefects(ccdDefects)

    def _computeAmpExposureId(self, visit, snap, raft, sensor, channel):
        """Compute the 64-bit (long) identifier for an amp exposure.

        @param visit (int)
        @param raft (str) "xy" e.g. "20"
        @param sensor (str) "xy" e.g. "11"
        @param channel (str) "yx" e.g. "05"
        """
        r1, r2 = raft
        s1, s2 = sensor
        c1, c2 = channel
        return (visit << 13) + (snap << 12) + \
                (long(r1) * 5 + long(r2)) * 160 + \
                (long(s1) * 3 + long(s2)) * 16 + \
                (long(c1) * 8 + long(c2))

    def _computeCcdExposureId(self, visit, raft, sensor):
        """Compute the 64-bit (long) identifier for a CCD exposure.

        @param visit (int)
        @param raft (str) "xy" e.g. "20"
        @param sensor (str) "xy" e.g. "11"
        """

        r1, r2 = raft
        s1, s2 = sensor
        return (visit << 9) + \
                (long(r1) * 5 + long(r2)) * 10 + \
                (long(s1) * 3 + long(s2))

    def _setAmpExposureId(self, propertyList, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(dataId)
        propertyList.set("Computed_ampExposureId",
                self._computeAmpExposureId(
                    dataId['visit'], dataId['snap'],
                    pathId['raft'], pathId['sensor'], pathId['channel']))
        return propertyList

    def _setCcdExposureId(self, propertyList, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(dataId)
        propertyList.set("Computed_ccdExposureId",
                self._computeCcdExposureId(
                    dataId['visit'], pathId['raft'], pathId['sensor']))
        return propertyList

###############################################################################

    def map_camera(self, dataId):
        dataId = self._transformId(dataId)
        return ButlerLocation(
                "lsst.afw.cameraGeom.Camera", "Camera",
                "PafStorage", self.cameraPolicyLocation, dataId)

    def std_camera(self, item, dataId):
        dataId = self._transformId(dataId)
        pol = cameraGeomUtils.getGeomPolicy(item)
        return cameraGeomUtils.makeCamera(pol)

###############################################################################

    def map_raw(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.rawTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.DecoratedImageU", "DecoratedImageU",
                "FitsStorage", path, dataId)

    def query_raw(self, key, format, dataId):
        dataId = self._transformId(dataId)
        where = {}
        values = []
        for k, v in dataId.iteritems():
            where[k] = '?'
            values.append(v)
        return self.registry.executeQuery(format, ("raw", "raw_skyTile"),
                where, None, values)

    def std_raw(self, item, dataId):
        dataId = self._transformId(dataId)
        exposure = afwImage.makeExposure(
                afwImage.makeMaskedImage(item.getImage()))
        md = item.getMetadata()
        exposure.setMetadata(md)
        wcs = afwImage.makeWcs(md)

        if md.exists("VERSION") and md.getInt("VERSION") < 16952:
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
        return self._standardizeExposure(exposure, dataId, True)

###############################################################################

    def map_eimage(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(dataId)
        path = os.path.join(self.root, self.eimageTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.DecoratedImageF", "DecoratedImageF",
                "FitsStorage", path, dataId)

###############################################################################

    def map_bias(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(dataId)
        path = os.path.join(self.calibRoot, self.biasTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_bias(self, item, dataId):
        return self._standardizeCalib(item, dataId, False)

###############################################################################

    def map_dark(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(dataId)
        path = os.path.join(self.calibRoot, self.darkTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_dark(self, item, dataId):
        dataId = self._transformId(dataId)
        return self._standardizeCalib(item, dataId, False)

###############################################################################

    def map_flat(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.calibRoot, self.flatTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_flat(self, item, dataId):
        dataId = self._transformId(dataId)
        return self._standardizeCalib(item, dataId, True)

###############################################################################

    def map_fringe(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.calibRoot, self.fringeTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_fringe(self, item, dataId):
        dataId = self._transformId(dataId)
        return self._standardizeCalib(item, dataId, True)

###############################################################################

    def map_postISR(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.postISRTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postISR(self, item, dataId):
        dataId = self._transformId(dataId)
        return self._standardizeExposure(item, dataId, True)

###############################################################################

    def map_postISRCCD(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.postISRCCDTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postISRCCD(self, item, dataId):
        dataId = self._transformId(dataId)
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_sdqaAmp(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.sdqaAmpTemplate % pathId)
        ampExposureId = self._computeAmpExposureId(
                dataId['visit'], dataId['snap'],
                pathId['raft'], pathId['sensor'], pathId['channel'])
        return ButlerLocation(
                "lsst.sdqa.PersistableSdqaRatingVector",
                "PersistableSdqaRatingVector",
                "BoostStorage", path,
                {"ampExposureId": ampExposureId, "sdqaRatingScope": "AMP"})

###############################################################################

    def map_sdqaCcd(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.sdqaCcdTemplate % pathId)
        ccdExposureId = self._computeCcdExposureId(
                dataId['visit'], pathId['raft'], pathId['sensor'])
        return ButlerLocation(
                "lsst.sdqa.PersistableSdqaRatingVector",
                "PersistableSdqaRatingVector",
                "BoostStorage", path,
                {"ccdExposureId": ccdExposureId, "sdqaRatingScope": "CCD"})

###############################################################################

    def map_visitim(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.visitimTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_visitim(self, item, dataId):
        dataId = self._transformId(dataId)
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_icSrc(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.icSrcTemplate % pathId)
        # Note that sources are identified by what is called an ampExposureId,
        # but in this case all we have is a CCD.
        ampExposureId = self._computeCcdExposureId(
                dataId['visit'], pathId['raft'], pathId['sensor'])
        filterId = self.filterIdMap[pathId['filter']]
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceVector",
                "PersistableSourceVector",
                "BoostStorage", path,
                {"ampExposureId": ampExposureId, "filterId": filterId})

###############################################################################

    def map_icMatch(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.icMatchTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceMatchVector",
                "PersistableSourceMatchVector", "FitsStorage", path, dataId)

###############################################################################

    def map_psf(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.psfTemplate % pathId)
        return ButlerLocation("lsst.afw.detection.Psf", "Psf", "BoostStorage", path, dataId)

###############################################################################

    def map_apCorr(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.apCorrTemplate % pathId)
        return ButlerLocation(
                "lsst.meas.algorithms.ApertureCorrection.ApertureCorrection",
                "ApertureCorrection", "PickleStorage", path, dataId)

###############################################################################

    def map_calexp(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.calexpTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_calexp(self, item, dataId):
        dataId = self._transformId(dataId)
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_src(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.srcTemplate % pathId)
        # Note that sources are identified by what is called an ampExposureId,
        # but in this case all we have is a CCD.
        ampExposureId = self._computeCcdExposureId(
                dataId['visit'], pathId['raft'], pathId['sensor'])
        filterId = self.filterIdMap[pathId['filter']]
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceVector",
                "PersistableSourceVector",
                "BoostStorage", path,
                {"ampExposureId": ampExposureId, "filterId": filterId})

###############################################################################

    def map_sourceHist(self, dataId):
        dataId = self._transformId(dataId)
        path = os.path.join(self.root, self.sourceHistTemplate % dataId)
        return ButlerLocation(
                "lsst.afw.image.DecoratedImageU",
                "DecoratedImageU",
                "FitsStorage", path, {})

    def map_badSourceHist(self, dataId):
        dataId = self._transformId(dataId)
        path = os.path.join(self.root, self.badSourceHistTemplate % dataId)
        return ButlerLocation(
                "lsst.afw.image.DecoratedImageU",
                "DecoratedImageU",
                "FitsStorage", path, {})

    def map_source(self, dataId):
        dataId = self._transformId(dataId)
        path = os.path.join(self.root, self.sourceTemplate % dataId)
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceVector",
                "PersistableSourceVector",
                "BoostStorage", path, {"skyTileId": dataId['skyTile']})

    def map_badSource(self, dataId):
        dataId = self._transformId(dataId)
        path = os.path.join(self.root, self.badSourceTemplate % dataId)
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceVector",
                "PersistableSourceVector",
                "BoostStorage", path, {"skyTileId": dataId['skyTile']})

    def map_invalidSource(self, dataId):
        dataId = self._transformId(dataId)
        path = os.path.join(self.root, self.invalidSourceTemplate % dataId)
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceVector",
                "PersistableSourceVector",
                "BoostStorage", path, {"skyTileId": dataId['skyTile']})

    def map_object(self, dataId):
        dataId = self._transformId(dataId)
        path = os.path.join(self.root, self.objectTemplate % dataId)
        return ButlerLocation(
                "lsst.ap.cluster.PersistableSourceClusterVector",
                "PersistableSourceClusterVector",
                "BoostStorage", path, {"skyTileId": dataId['skyTile']})

    def map_badObject(self, dataId):
        dataId = self._transformId(dataId)
        path = os.path.join(self.root, self.badObjectTemplate % dataId)
        return ButlerLocation(
                "lsst.ap.cluster.PersistableSourceClusterVector",
                "PersistableSourceClusterVector",
                "BoostStorage", path, {"skyTileId": dataId['skyTile']})

###############################################################################

for exposureType in ("bias", "dark", "flat", "fringe"):
    setattr(LsstSimMapper, "map_" + exposureType + "_md",
            getattr(LsstSimMapper, "map_" + exposureType))
    setattr(LsstSimMapper, "bypass_" + exposureType + "_md",
            lambda self, datasetType, pythonType, location, dataId: \
                    afwImage.readMetadata(location.getLocations()[0]))
for exposureType in ("raw", "postISR"):
    setattr(LsstSimMapper, "map_" + exposureType + "_md",
            getattr(LsstSimMapper, "map_" + exposureType))
    setattr(LsstSimMapper, "bypass_" + exposureType + "_md",
            lambda self, datasetType, pythonType, location, dataId: \
                    self._setAmpExposureId(
                        afwImage.readMetadata(location.getLocations()[0]),
                        dataId))
for exposureType in ("eimage", "postISRCCD", "visitim", "calexp"):
    setattr(LsstSimMapper, "map_" + exposureType + "_md",
            getattr(LsstSimMapper, "map_" + exposureType))
    setattr(LsstSimMapper, "bypass_" + exposureType + "_md",
            lambda self, datasetType, pythonType, location, dataId: \
                    self._setCcdExposureId(
                        afwImage.readMetadata(location.getLocations()[0]),
                        dataId))

###############################################################################

def stripFits(propertySet):
    for kw in ("SIMPLE", "BITPIX", "EXTEND", "NAXIS", "NAXIS1", "NAXIS2",
            "BSCALE", "BZERO"):
        if propertySet.exists(kw):
            propertySet.remove(kw)
