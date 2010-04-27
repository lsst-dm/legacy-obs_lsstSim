import os
import re
import time
import lsst.daf.base as dafBase
from lsst.daf.persistence import Mapper, ButlerLocation
import lsst.daf.butlerUtils as butlerUtils
import lsst.afw.image as afwImage
import lsst.afw.cameraGeom as afwCameraGeom
import lsst.afw.cameraGeom.utils as cameraGeomUtils
import lsst.afw.image.utils as imageUtils
import lsst.pex.policy as pexPolicy

class LsstSimMapper(Mapper):
    def __init__(self, policy=None, root=".", calibRoot=None, **kw):
        Mapper.__init__(self)

        self.policy = policy
        if self.policy is None:
            self.policy = pexPolicy.Policy()
        defaultFile = pexPolicy.DefaultPolicyFile("obs_lsstSim",
                "LsstSimMapperDictionary.paf", "policy")
        defaultPolicy = pexPolicy.Policy.createPolicy(defaultFile,
                defaultFile.getRepositoryPath())
        self.policy.mergeDefaults(defaultPolicy)

        self.root = root
        if self.policy.exists('root'):
            self.root = self.policy.getString('root')
        self.calibRoot = calibRoot
        if self.policy.exists('calibRoot'):
            self.calibRoot = self.policy.getString('calibRoot')
        if self.calibRoot is None:
            self.calibRoot = self.root

        for datasetType in ["raw", "bias", "dark", "flat", "fringe",
            "postISR", "postISRCCD", "satDefect", "visitim", "calexp",
            "psf", "src", "obj"]:
            key = datasetType + "Template"
            if self.policy.exists(key):
                setattr(self, key, self.policy.getString(key))

        self._setupRegistry(kw)
        self._setupCalibRegistry(kw)

        if self.registry:
            self.keys = self.registry.getFields()
        else:
            self.keys = ["visit", "raft", "sensor", "channel", "snap"]
        if self.calibRegistry:
            for k in self.calibRegistry.getFields():
                if k not in self.keys:
                    self.keys.append(k)
        else:
            self.keys.append("filter")

        self.cameraPolicyLocation = os.path.join(
                defaultFile.getRepositoryPath(),
                self.policy.getString('cameraDescription'))
        cameraPolicy = cameraGeomUtils.getGeomPolicy(self.cameraPolicyLocation)
        self.camera = cameraGeomUtils.makeCamera(cameraPolicy)

        filterPolicy = pexPolicy.Policy.createPolicy(
                os.path.join(defaultFile.getRepositoryPath(),
                    self.policy.getString('filterDescription')))
        imageUtils.defineFiltersFromPolicy(filterPolicy, reset=True)


    def getKeys(self):
        return self.keys

###############################################################################
#
# Utility functions
#
###############################################################################

    def _setupRegistry(self, kw):
        registryPath = None
        if self.policy.exists('registryPath'):
            registryPath = self.policy.getString('registryPath')
            if not os.path.exists(registryPath):
                registryPath = None
        if registryPath is None:
            registryPath = os.path.join(self.root, "registry.sqlite3")
            if not os.path.exists(registryPath):
                registryPath = None
        if registryPath is None:
            registryPath = "registry.sqlite3"
        if os.path.exists(registryPath):
            self.registry = butlerUtils.SqliteRegistry(registryPath)
        else:
            # TODO Try a FsRegistry(self.root) for raw and all intermediates
            self.registry = None

    def _setupCalibRegistry(self, kw):
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
        if os.path.exists(calibRegistryPath):
            self.calibRegistry = butlerUtils.SqliteRegistry(calibRegistryPath)
        else:
            # TODO Try a FsRegistry(self.calibRoot) for all calibration types
            self.calibRegistry = None

    def _mapIdToActual(self, dataId):
        actualId = dict(dataId)
        if actualId.has_key("detector"):
            for m in re.finditer(r'([RSC]):(\d),(\d)', actualId['detector']):
                if m.group(1) == 'R':
                    actualId['raft'] = m.group(0)
                elif m.group(1) == 'S':
                    actualId['sensor'] = m.group(0)
                elif m.group(1) == 'C':
                    actualId['channel'] = m.group(0)
        return actualId

    def _mapActualToPath(self, actualId):
        pathId = dict(actualId)
        if pathId.has_key("raft"):
            pathId['raft'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['raft'])
        if pathId.has_key("sensor"):
            pathId['sensor'] = re.sub(r'(\d),(\d)', r'\1\2', pathId['sensor'])
        if pathId.has_key("channel"):
            pathId['channel'] = re.sub(r'(\d),(\d)', r'\1\2',
                    pathId['channel'])
        if pathId.has_key("snap"):
            pathId['exposure'] = pathId['snap']
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
        item.setDetector(detector)

    def _setCcdDetector(self, item, dataId):
        ccdId = self._extractDetectorName(dataId)
        detector = cameraGeomUtils.findCcd(
                self.camera, afwCameraGeom.Id(ccdId))
        item.setDetector(detector)

    def _setFilter(self, item):
        filterName = item.getMetadata().get("FILTER").strip()
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
        self._setFilter(item)
        return item

    def _standardizeCalib(self, item, dataId, filterNeeded):
        stripFits(item.getMetadata())
        self._setAmpDetector(item, dataId)
        if filterNeeded:
            self._setFilter(item)
        return item

###############################################################################

    def map_camera(self, dataId):
        return ButlerLocation(
                "lsst.afw.cameraGeom.Camera", "Camera",
                "PafStorage", self.cameraPolicyLocation, dataId)

    def std_camera(self, item, dataId):
        pol = cameraGeomUtils.getGeomPolicy(item)
        return cameraGeomUtils.makeCamera(pol)

###############################################################################

    def map_raw(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.rawTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.DecoratedImageU", "DecoratedImageU",
                "FitsStorage", path, dataId)

    def query_raw(self, key, format, dataId):
        return self.registry.getCollection(key, format, dataId)

    def std_raw(self, item, dataId):
        exposure = afwImage.ExposureU(
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
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
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
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.calibRoot, self.darkTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def query_dark(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("dark", key, format, dataId)

    def std_dark(self, item, dataId):
        return self._standardizeCalib(item, dataId, False)

###############################################################################

    def map_flat(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        # TODO get this from the metadata registry
        pathId['filter'] = 'r'
        path = os.path.join(self.calibRoot, self.flatTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def query_flat(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("flat", key, format, dataId)

    def std_flat(self, item, dataId):
        return self._standardizeCalib(item, dataId, True)

###############################################################################

    def map_fringe(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        # TODO get this from the metadata registry
        pathId['filter'] = 'r'
        path = os.path.join(self.calibRoot, self.fringeTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def query_fringe(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("fringe", key, format, dataId)

    def std_fringe(self, item, dataId):
        return self._standardizeCalib(item, dataId, True)

###############################################################################

    def map_postISR(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.postISRTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postISR(self, item, dataId):
        return self._standardizeExposure(item, dataId, True)

###############################################################################

    def map_postISRCCD(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.postISRCCDTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postISRCCD(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_visitim(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.visitimTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_visitim(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_psf(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.psfTemplate % pathId)
        return ButlerLocation(
                "lsst.meas.algorithms.PSF", "PSF",
                "BoostStorage", path, dataId)

###############################################################################

    def map_calexp(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.calexpTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_calexp(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_src(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.srcTemplate % pathId)
        ampExposureId = dataId['visit'] << 12
        # TODO add in ccd and amp bits
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
