import os
import re
from lsst.daf.persistence import Mapper, ButlerLocation
import lsst.daf.butlerUtils as butlerUtils
import lsst.afw.image as afwImage
import lsst.afw.cameraGeom as afwCameraGeom
import lsst.afw.cameraGeom.utils as cameraGeomUtils
import lsst.afw.image.utils as imageUtils
import lsst.pex.policy as pexPolicy

class LsstSimMapper(Mapper):
    def __init__(self, policy=None, root=".", calibRoot=None):
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
            if not os.path.exists(registryPath):
                pass
        if registryPath is not None:
            self.registry = butlerUtils.SqliteRegistry(registryPath)

        # self.keys = self.registry.getFields()
        self.keys = ["visit", "raft", "sensor", "channel", "snap"]

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
                pass
        if calibRegistryPath is not None:
            self.calibRegistry = butlerUtils.SqliteRegistry(calibRegistryPath)

        # for k in self.calibRegistry.getFields():
        #     if k not in self.keys:
        #         self.keys.append(k)
        self.keys.append("filter")

        for datasetType in ["raw", "bias", "dark", "flat", "fringe",
            "postIsr", "postIsrCcd", "satDefect", "visitImage", "sci",
            "src", "obj"]:
            key = datasetType + "Template"
            if self.policy.exists(key):
                setattr(self, key, self.policy.getString(key))

        self.cameraPolicyLocation = os.path.join(
                defaultFile.getRepositoryPath(),
                self.policy.getString('cameraDescription'))
        cameraPolicy = pexPolicy.Policy.createPolicy(self.cameraPolicyLocation)
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

    def _mapIdToActual(self, dataId):
        # TODO map mapped fields in actualId to actual fields
        return dict(dataId)

    def _mapActualToPath(self, actualId):
        pathId = dict(actualId)
        if pathId.has_key("raft"):
            pathId['raft'] = re.sub(r'R:(\d),(\d)', r'\1\2', pathId['raft'])
        if pathId.has_key("sensor"):
            pathId['sensor'] = re.sub(r'S:(\d),(\d)', r'\1\2', pathId['sensor'])
        if pathId.has_key("detector"):
            for m in re.finditer(r'([RSC]):(\d),(\d)', pathId['detector']):
                id = m.groups(1) + m.groups(2)
                if m.groups(0) == 'R':
                    pathId['raft'] = id
                elif m.groups(0) == 'S':
                    pathId['sensor'] = id
                elif m.groups(0) == 'C':
                    pathId['channel'] = id
        if pathId.has_key("snap"):
            pathId['exposure'] = pathId['snap']
        return pathId

    def _extractDetectorName(self, dataId):
        return "%(raft)s %(sensor)s" % dataId

    def _extractAmpId(self, dataId):
        m = re.match(r'(\d)(\d)', dataId['channel'])
        # Note that indices are swapped in the camera geometry vs. official
        # channel specification.
        return (self._extractDetectorName(dataId),
                int(m.group(2)), int(m.group(1)))

    def _setDetector(self, item, dataId):
        ampId = self._extractAmpId(dataId)
        detector = cameraGeomUtils.findAmp(
                self.camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        item.setDetector(detector)

    def _setFilter(self, item):
        filterName = item.getMetadata().get("FILTER").strip()
        filter = afwImage.Filter(filterName)
        item.setFilter(filter)

    def _setWcs(self, item):
        md = item.getMetadata()
        item.setWcs(afwImage.makeWcs(md))
        wcsMetadata = item.getWcs().getFitsMetadata()
        for kw in wcsMetadata.paramNames():
            md.remove(kw)

    def _standardizeExposure(self, item, dataId):
        stripFits(item.getMetadata())
        self._setDetector(item, dataId)
        self._setFilter(item)
        self._setWcs(item)
        return item

    def _standardizeCalib(self, item, dataId, filterNeeded):
        stripFits(item.getMetadata())
        self._setDetector(item, dataId)
        if filterNeeded:
            self._setFilter(item)
        return item

###############################################################################

    def map_camera(self, dataId):
        return ButlerLocation(
                "lsst.afw.cameraGeom.Camera", "Camera",
                "PafStorage", self.cameraPolicyLocation, dataId)

    def std_camera(self, item, dataId):
        return cameraGeomUtils.makeCamera(item)

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
        exposure.setMetadata(item.getMetadata())
        return self._standardizeExposure(exposure, dataId)

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

    def map_postIsr(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.postIsrTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postIsr(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_postIsrCcd(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.postIsrCcdTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_postIsrCcd(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_visitImage(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.visitImageTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_visitImage(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

    def map_sci(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.sciTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureF", "ExposureF",
                "FitsStorage", path, dataId)

    def std_sci(self, item, dataId):
        return self._standardizeExposure(item, dataId)

###############################################################################

def stripFits(propertySet):
    for kw in ("SIMPLE", "BITPIX", "EXTEND", "NAXIS", "NAXIS1", "NAXIS2",
            "BSCALE", "BZERO"):
        if propertySet.exists(kw):
            propertySet.remove(kw)
