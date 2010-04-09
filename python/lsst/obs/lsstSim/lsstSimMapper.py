import os
import re
from lsst.daf.persistence import Mapper, SqliteRegistry, ButlerLocation
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
            self.root = self.policy.getString('calibRoot')
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
                # raise pexExcept.LsstException, "Registry not found"
        if registryPath is not None:
            self.registry = SqliteRegistry(registryPath)

        # self.keys = self.registry.getFields()
        self.keys = ["visit", "raft", "sensor", "channel", "snap"]

        calibRegistryPath = None
        if self.policy.exists('calibRegistryPath'):
            calibRegistryPath = self.policy.getString('calibRegistryPath')
            if not os.path.exists(calibRegistryPath):
                calibRegistryPath = None
        if calibRegistryPath is None:
            calibRegistryPath = os.path.join(self.root, "calibRegistry.sqlite3")
            if not os.path.exists(calibRegistryPath):
                calibRegistryPath = None
        if calibRegistryPath is None:
            calibRegistryPath = "calibRegistry.sqlite3"
            if not os.path.exists(calibRegistryPath):
                pass
                # raise pexExcept.LsstException, "Calibration registry not found"
        if calibRegistryPath is not None:
            self.calibRegistry = SqliteRegistry(calibRegistryPath)

        # for k in self.calibRegistry.getFields():
        #     if k not in self.keys:
        #         self.keys.append(k)
        self.keys.append("filter")

        for datasetType in ["raw", "bias", "dark", "flat", "fringe"]:
            key = datasetType + "Template"
            setattr(self, key, self.policy.getString(key))

        cameraPolicy = pexPolicy.Policy.createPolicy(
                os.path.join(defaultFile.getRepositoryPath(),
                    self.policy.getString('cameraDescription')),
                defaultFile.getRepositoryPath())
        self.camera = cameraGeomUtils.makeCamera(cameraPolicy)

        filterPolicy = pexPolicy.Policy.createPolicy(
                os.path.join(defaultFile.getRepositoryPath(),
                    self.policy.getString('filterDescription')),
                defaultFile.getRepositoryPath())
        imageUtils.defineFiltersFromPolicy(filterPolicy, reset=True)


    def getKeys(self):
        return self.keys

    def map_raw(self, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        path = os.path.join(self.root, self.rawTemplate % pathId)
        return ButlerLocation(
                "lsst.afw.image.DecoratedImageU", "DecoratedImageU",
                "FitsStorage", path, dataId)

    def query_raw(self, key, format, dataId):
        return self.registry.getCollection(key, format, dataId)

    def std_raw(self, item, dataId):
        md = item.getMetadata()
        exposure = afwImage.makeExposure(
                afwImage.makeMaskedImage(item.getImage()))
        exposure.setMetadata(md)

        ampId = self.extract_ampId(dataId)
        detector = cameraGeomUtils.findAmp(
                self.camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        exposure.setDetector(detector)

        filterName = md.get("FILTER")
        filter = afwImage.Filter(filterName)
        exposure.setFilter(filter)

        exposure.setWcs(afwImage.makeWcs(md))

        return exposure

    def extract_ampId(self, dataId):
        m = re.match(r'(\d)(\d)', dataId['channel'])
        return (self.extract_detectorName(dataId),
                int(m.groups(1)), int(m.groups(2)))

    def extract_detectorName(self, dataId):
        return "%(raft)s %(sensor)s" % dataId

    def query_bias(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("bias", key, format, dataId)

    def std_bias(self, item, dataId):
        ampId = self.convert_raftSensorChannel_to_ampId(dataId)
        detector = cameraGeomUtils.findAmp(
                self.camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        exposure.setDetector(detector)
        return exposure

    def query_dark(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("dark", key, format, dataId)

    def std_dark(self, item, dataId):
        ampId = self.convert_raftSensorChannel_to_ampId(dataId)
        detector = cameraGeomUtils.findAmp(
                self.camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        exposure.setDetector(detector)
        return exposure

    def query_flat(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("flat", key, format, dataId)

    def std_flat(self, item, dataId):
        ampId = self.convert_raftSensorChannel_to_ampId(dataId)
        detector = cameraGeomUtils.findAmp(
                self.camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        exposure.setDetector(detector)

        md = item.getMetadata()
        filterName = md.get("FILTER")
        filter = afwImage.Filter(filterName)
        exposure.setFilter(filter)
        md.remove("FILTER")

        return exposure

    def query_fringe(self, key, format, dataId):
        return self.calibRegistry.queryMetadata("fringe", key, format, dataId)

    def std_fringe(self, item, dataId):
        ampId = self.convert_raftSensorChannel_to_ampId(dataId)
        detector = cameraGeomUtils.findAmp(
                self.camera, afwCameraGeom.Id(ampId[0]), ampId[1], ampId[2])
        exposure.setDetector(detector)

        md = item.getMetadata()
        filterName = md.get("FILTER")
        filter = afwImage.Filter(filterName)
        exposure.setFilter(filter)
        md.remove("FILTER")

        return exposure

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

    def _calibMapper(self, datasetType, dataId):
        pathId = self._mapActualToPath(self._mapIdToActual(dataId))
        # TODO get this from the metadata registry
        pathId['filter'] = 'r'
        path = os.path.join(self.calibRoot,
                getattr(self, datasetType + 'Template') % pathId)
        return ButlerLocation(
                "lsst.afw.image.ExposureU", "ExposureU",
                "FitsStorage", path, dataId)

for calibType in ["bias", "dark", "flat", "fringe"]:
    setattr(LsstSimMapper, "map_" + calibType, lambda self, dataId:
            self._calibMapper(calibType, dataId))
