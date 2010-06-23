import os
import re
import time
import lsst.daf.base as dafBase
from lsst.daf.persistence import Mapper, ButlerLocation, LogicalLocation
import lsst.daf.butlerUtils as butlerUtils
import lsst.afw.image as afwImage
import lsst.afw.cameraGeom as afwCameraGeom
import lsst.afw.cameraGeom.utils as cameraGeomUtils
import lsst.afw.image.utils as imageUtils
import lsst.pex.logging as pexLog
import lsst.pex.policy as pexPolicy

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
            "icSrc", "visitim", "psf", "calexp", "src",
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
            if not os.path.exists(registryPath):
                registryPath = None
        if registryPath is None:
            registryPath = os.path.join(self.root, "registry.sqlite3")
            if not os.path.exists(registryPath):
                registryPath = None
        if registryPath is None:
            registryPath = "registry.sqlite3"
            if not os.path.exists(registryPath):
                registryPath = None
        if registryPath is not None:
            self.log.log(pexLog.Log.INFO,
                    "Registry loaded from %s" % (registryPath,))
            self.registry = butlerUtils.Registry.create(registryPath)
        else:
            # TODO Try a FsRegistry(self.root) for raw (and all outputs?)
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
        rows = self.registry.executeQuery(("filter",), ("raw",),
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
            rows = self.registry.executeQuery(("filter",), ("raw",),
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
                    dafBase.DateTime.MJD, dafBase.DateTime.UTC)
            obsMidpoint = obsStart.nsecs() + long(expTime * 1000000000L / 2)
            calib.setMidTime(dafBase.DateTime(obsMidpoint))

    def _mapExposure(self, dataId, exposureType,
            isCalib=False, needFilter=True):
        dataId = self._transformId(dataId)
        if needFilter:
            pathId = self._mapActualToPath(self._needFilter(dataId))
        else:
            pathId = self._mapActualToPath(dataId)
        if isCalib:
            root = self.calibRoot
        else:
            root = self.root
        path = os.path.join(root,
                getattr(self, exposureType + "Template") % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def _mapSubimage(self, dataId, exposureType, isCalib=False,
            needFilter=True):
        if not dataId.has_key("bbox"):
            return self._mapExposure(dataId, exposureType, isCalib, needFilter)

        bbox = dataId['bbox']
        del dataId['bbox']
        loc = self._mapExposure(dataId, exposureType, isCalib, needFilter)

        if isinstance(bbox, afwImage.BBox):
            llcX = bbox.getLLC().getX()
            llcY = bbox.getLLC().getY()
            width = bbox.getWidth()
            height = bbox.getHeight()
        else:
            llcX = bbox[0][0]
            llcY = bbox[0][1]
            width = bbox[1]
            height = bbox[2]
        ad = loc.getAdditionalData()
        ad.set("llcX", llcX)
        ad.set("llcY", llcY)
        ad.set("width", width)
        ad.set("height", height)
        return loc

    def _mapWcs(self, dataId, exposureType, needFilter=True):
        dataId = self._transformId(dataId)
        if needFilter:
            pathId = self._mapActualToPath(self._needFilter(dataId))
        else:
            pathId = self._mapActualToPath(dataId)
        path = os.path.join(self.root,
                getattr(self, exposureType + "Template") % pathId)
        return ButlerLocation(
                "lsst.afw.image.Wcs", "Wcs", "FitsStorage", path, dataId)

    def _standardizeExposure(self, item, dataId, isAmp=False):
        dataId = self._transformId(dataId)
        if isAmp:
            self._setAmpDetector(item, dataId)
        else:
            self._setCcdDetector(item, dataId)
        self._setFilter(item, dataId)
        self._setTimes(item, dataId)
        return item

    def _standardizeCalib(self, item, dataId, filterNeeded):
        dataId = self._transformId(dataId)
        self._setAmpDetector(item, dataId)
        if filterNeeded:
            self._setFilter(item, dataId)
        return item

    def _defectLookup(self, dataId, ccdSerial):
        if self.defectRegistry is None:
            return None

        rows = self.registry.executeQuery(("taiObs",), ("raw",),
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

    def map_raw_wcs(self, dataId):
        loc = self.map_raw(dataId)
        loc.pythonType = "lsst.afw.image.Wcs"
        loc.cppType = "Wcs"
        return loc

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
        exposure = afwImage.makeExposure(
                afwImage.makeMaskedImage(item.getImage()))
        md = item.getMetadata()
        stripFits(md)

        # Recompute EQUINOX and WCS based on actual observation date
        mjd = md.get("MJD-OBS")
        obsdate = dafBase.DateTime(mjd, dafBase.DateTime.MJD,
                dafBase.DateTime.TAI)
        gmt = time.gmtime(obsdate.nsecs(dafBase.DateTime.UTC) / 1.0e9)
        year = gmt[0]
        doy = gmt[7]
        equinox = year + (doy / 365.0)
        md.set("EQUINOX", equinox)

        exposure.setMetadata(md)
        exposure.setWcs(afwImage.makeWcs(md))
        wcsMetadata = exposure.getWcs().getFitsMetadata()
        for kw in wcsMetadata.paramNames():
            md.remove(kw)

        return self._standardizeExposure(exposure, dataId, True)

    def std_raw_sub(self, item, dataId):
        return self.std_raw(item, dataId)

###############################################################################

    def map_icSrc(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.icSrcTemplate % pathId)
        r1, r2 = pathId['raft']
        s1, s2 = pathId['sensor']
        ampExposureId = (dataId['visit'] << 9) + \
                (long(r1) * 5 + long(r2)) * 10 + (long(s1) * 3 + long(s2))
        filterId = self.filterIdMap[pathId['filter']]
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceVector",
                "PersistableSourceVector",
                "BoostStorage", path,
                {"ampExposureId": ampExposureId, "filterId": filterId})

###############################################################################

    def map_psf(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.psfTemplate % pathId)
        return ButlerLocation(
                "lsst.meas.algorithms.PSF", "PSF",
                "BoostStorage", path, dataId)

###############################################################################

    def map_src(self, dataId):
        dataId = self._transformId(dataId)
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.srcTemplate % pathId)
        r1, r2 = pathId['raft']
        s1, s2 = pathId['sensor']
        ampExposureId = (dataId['visit'] << 9) + \
                (long(r1) * 5 + long(r2)) * 10 + (long(s1) * 3 + long(s2))
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

for calibType in ("bias", "dark", "flat", "fringe"):
    needFilter = calibType in ("flat", "fringe")
    setattr(LsstSimMapper, "map_" + calibType,
            lambda self, dataId: self._mapExposure(dataId, calibType, True,
                needFilter))
    setattr(LsstSimMapper, "map_" + calibType + "_sub",
            lambda self, dataId: self._mapSubimage(dataId, calibType, True,
                needFilter))
    setattr(LsstSimMapper, "std_" + calibType,
            lambda self, item, dataId: self._standardizeCalib(item, dataId,
                needFilter))
    setattr(LsstSimMapper, "std_" + calibType + "_sub",
            lambda self, item, dataId: self._standardizeCalib(item, dataId,
                needFilter))

for exposureType in ("postISR", "postISRCCD", "visitim", "calexp"):
    setattr(LsstSimMapper, "map_" + exposureType,
            lambda self, dataId: self._mapExposure(dataId, exposureType))
    setattr(LsstSimMapper, "map_" + exposureType + "_wcs",
            lambda self, dataId: self._mapWcs(dataId, exposureType))
    setattr(LsstSimMapper, "map_" + exposureType + "_sub",
            lambda self, dataId: self._mapSubimage(dataId, exposureType))
    setattr(LsstSimMapper, "std_" + exposureType,
            lambda self, item, dataId: self._standardizeExposure(item, dataId,
                calibType == "postISR"))
    setattr(LsstSimMapper, "std_" + exposureType + "_sub",
            lambda self, item, dataId: self._standardizeExposure(item, dataId,
                calibType == "postISR"))

###############################################################################

def stripFits(propertySet):
    for kw in ("SIMPLE", "BITPIX", "EXTEND", "NAXIS", "NAXIS1", "NAXIS2",
            "BSCALE", "BZERO"):
        if propertySet.exists(kw):
            propertySet.remove(kw)
