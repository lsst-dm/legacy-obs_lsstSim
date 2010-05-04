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

        self.log = pexLog.Log(pexLog.getDefaultLog(), "CfhtMapper")

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

        for datasetType in ["raw", "bias", "dark", "flat", "fringe",
            "postISR", "satPixelSet", "postISRCCD", "visitim",
            "psf", "calexp", "src", "obj"]:
            key = datasetType + "Template"
            if self.policy.exists(key):
                setattr(self, key, self.policy.getString(key))

        self._setupRegistry(registry)

        self.keys = ["visit", "snap", "raft", "sensor", "channel", "skyTile"]
        self.keys.append("filter")

        self.cameraPolicyLocation = os.path.join(self.repositoryPath,
                self.policy.getString('cameraDescription'))
        self.cameraPolicy = cameraGeomUtils.getGeomPolicy(
                self.cameraPolicyLocation)

        self.defectRegistry = None
        if self.policy.exists('defectPath'):
            self.defectPath = os.path.join(
                    self.repositoryPath, self.policy.getString('defectPath'))
            defectRegistryLocation = os.path.join(
                    self.defectPath, "defectRegistry.sqlite3")
            self.defectRegistry = \
                    butlerUtils.Registry.create(defectRegistryLocation)
        self.cameras = {}

        filterPolicy = pexPolicy.Policy.createPolicy(
                os.path.join(self.repositoryPath,
                    self.policy.getString('filterDescription')))
        imageUtils.defineFiltersFromPolicy(filterPolicy, reset=True)


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
            self.log.log(pexLog.INFO,
                    "Registry loaded from %s" % (registryPath,))
            self.registry = butlerUtils.Registry.create(registryPath)
        else:
            # TODO Try a FsRegistry(self.root) for raw (and all outputs?)
            self.registry = None

    def _setupCalibRegistry(self):
        calibRegistryPath = None
        if self.policy.exists('calibRegistryPath'):
            calibRegistryPath = self.policy.getString('calibRegistryPath')
            if not os.path.exists(calibRegistryPath):
                calibRegistryPath = None
        if calibRegistryPath is None:
            calibRegistryPath = os.path.join(self.calibRoot,
                    "calibRegistry.sqlite3")
            if not os.path.exists(calibRegistryPath):
                calibRegistryPath = None
        if calibRegistryPath is None:
            calibRegistryPath = "calibRegistry.sqlite3"
            if not os.path.exists(calibRegistryPath):
                calibRegistryPath = None
        if calibRegistryPath is not None:
            self.log.log(pexLog.INFO,
                    "Calibration registry loaded from %s" %
                    (calibRegistryPath,))
            self.calibRegistry = butlerUtils.SqliteRegistry(calibRegistryPath)

            # for k in self.calibRegistry.getFields():
            #     if k not in self.keys:
            #         self.keys.append(k)
        else:
            # TODO Try a FsRegistry(self.calibRoot) for all calibration types
            self.calibRegistry = None

    def _needFilter(self, dataId):
        if dataId.has_key('filter'):
            return dataId
        actualId = dict(dataId)
        rows = self.registry.executeQuery(("filter",), ("raw",),
                {'visit': "?"}, None, (dataId['visit'],))
        assert len(rows) == 1
        actualId['filter'] = str(rows[0][0])
        return actualId

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
        camera = self._cameraWithDefects(dataId)
        detector = cameraGeomUtils.findAmp(
                camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        item.setDetector(detector)

    def _setCcdDetector(self, item, dataId):
        ccdId = self._extractDetectorName(dataId)
        camera = self._cameraWithDefects(dataId)
        detector = cameraGeomUtils.findCcd(camera, afwCameraGeom.Id(ccdId))
        item.setDetector(detector)

    def _setFilter(self, item, dataId):
        md = item.getMetadata()
        filterName = None
        if md.exists("FILTER"):
            filterName = item.getMetadata().get("FILTER").strip()
        if filterName is None:
            rows = self.registry.executeQuery(("filter",), ("raw",),
                    {'visit': "?"}, None, (dataId['visit'],))
            assert len(rows) == 1
            filterName = str(rows[0][0])
        filter = afwImage.Filter(filterName)
        item.setFilter(filter)

    def _standardizeExposure(self, item, dataId, isAmp=False):
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
        wcsMetadata = item.getWcs().getFitsMetadata()
        wcsMetadata.set("EQUINOX", equinox)
        item.setWcs(afwImage.makeWcs(wcsMetadata))

        if isAmp:
            self._setAmpDetector(item, dataId)
        else:
            self._setCcdDetector(item, dataId)
        self._setFilter(item, dataId)
        return item

    def _standardizeCalib(self, item, dataId, filterNeeded):
        stripFits(item.getMetadata())
        self._setAmpDetector(item, dataId)
        if filterNeeded:
            self._setFilter(item, dataId)
        return item

    def _defectLookup(self, dataId):
        if self.defectRegistry is None:
            return None

        rows = self.registry.executeQuery(("taiObs",), ("raw",),
                {"visit": "?"}, None, (dataId['visit'],))
        if len(rows) == 0:
            return None
        assert len(rows) == 1
        taiObs = rows[0][0]

        rows = self.defectRegistry.executeQuery(("path",), ("defect",), None,
                ("DATETIME(?)", "DATETIME(validStart)", "DATETIME(validEnd)"),
                (taiObs,))
        if len(rows) == 0:
            return None
        assert len(rows) == 1
        return os.path.join(self.defectPath, str(rows[0][0]))

    def _cameraWithDefects(self, dataId):
        defectPolicy = self._defectLookup(dataId)
        if defectPolicy is None:
            if not self.cameras.has_key(""):
                self.cameras[""] = \
                        cameraGeomUtils.makeCamera(self.cameraPolicy)
            return self.cameras[""]
        if not self.cameras.has_key(defectPolicy):
            cameraPolicy = pexPolicy.Policy(self.cameraPolicy, True)
            cameraPolicy.set("Defects",
                    pexPolicy.Policy.createPolicy(defectPolicy).get("Defects"))
            self.cameras[defectPolicy] = \
                    cameraGeomUtils.makeCamera(cameraPolicy)
        return self.cameras[defectPolicy]


###############################################################################

    def map_camera(self, dataId):
        return ButlerLocation(
                "lsst.afw.cameraGeom.Camera", "Camera",
                "PafStorage", self.cameraPolicyLocation, dataId)

    def std_camera(self, item, dataId):
        pol = cameraGeomUtils.getGeomPolicy(item)
        defectPol = self._defectLookup(dataId)
        if defectPol is not None:
            pol.set("Defects", defectPol)
        return cameraGeomUtils.makeCamera(pol)

###############################################################################

    def map_raw(self, dataId):
        pathId = self._mapActualToPath(self._needField(dataId))
        path = os.path.join(self.root, self.rawTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.DecoratedImageU", "DecoratedImageU",
                "FitsStorage", path, dataId)

    def query_raw(self, key, format, dataId):
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
        exposure.setMetadata(md)
        exposure.setWcs(afwImage.makeWcs(md))
        wcsMetadata = exposure.getWcs().getFitsMetadata()
        for kw in wcsMetadata.paramNames():
            md.remove(kw)
        return self._standardizeExposure(exposure, dataId, True)

###############################################################################

    def map_bias(self, dataId):
        pathId = self._mapActualToPath(dataId)
        path = os.path.join(self.calibRoot, self.biasTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def query_bias(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("bias", key, format, dataId)

    def std_bias(self, item, dataId):
        return self._standardizeCalib(item, dataId, False)

###############################################################################

    def map_dark(self, dataId):
        pathId = self._mapActualToPath(dataId)
        path = os.path.join(self.calibRoot, self.darkTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_dark(self, item, dataId):
        return self._standardizeCalib(item, dataId, False)

###############################################################################

    def map_flat(self, dataId):
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.calibRoot, self.flatTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_flat(self, item, dataId):
        return self._standardizeCalib(item, dataId, True)

###############################################################################

    def map_fringe(self, dataId):
        pathId = self._mapActualToPath(self._needFilter((dataId))
        path = os.path.join(self.calibRoot, self.fringeTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_fringe(self, item, dataId):
        return self._standardizeCalib(item, dataId, True)

###############################################################################

    def map_postISR(self, dataId):
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.postISRTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postISR(self, item, dataId):
        return self._standardizeExposure(item, dataId, True)

###############################################################################

    def map_satPixelSet(self, dataId):
        pathId = self._mapActualToPath(_needFilter(dataId))
        path = os.path.join(self.root, self.satPixelSetTemplate % pathId)
        return ButlerLocation(None, None, "PickleStorage", path, None)

###############################################################################

    def map_postISRCCD(self, dataId):
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.postISRCCDTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postISRCCD(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_visitim(self, dataId):
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.visitimTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_visitim(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_psf(self, dataId):
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.psfTemplate % pathId)
        return ButlerLocation(
                "lsst.meas.algorithms.PSF", "PSF",
                "BoostStorage", path, dataId)

###############################################################################

    def map_calexp(self, dataId):
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.calexpTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_calexp(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_src(self, dataId):
        pathId = self._mapActualToPath(self._needFilter(dataId))
        path = os.path.join(self.root, self.srcTemplate % pathId)
        r1, r2 = dataId['raft'].split(',')
        s1, s2 = dataId['sensor'].split(',')
        ampExposureId = (dataId['visit'] << 9) + \
                (int(r1) * 5 + int(r2)) * 10 + (int(s1) * 3 + int(s2))
        return ButlerLocation(
                "lsst.afw.detection.PersistableSourceVector",
                "PersistableSourceVector",
                "BoostStorage", path, {"ampExposureId": ampExposureId})

###############################################################################

def stripFits(propertySet):
    for kw in ("SIMPLE", "BITPIX", "EXTEND", "NAXIS", "NAXIS1", "NAXIS2",
            "BSCALE", "BZERO"):
        if propertySet.exists(kw):
            propertySet.remove(kw)
