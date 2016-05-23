import os
from lsst.afw.cameraGeom import makeCameraFromPath, CameraConfig
from .lsstSimMapper import LsstSimMapper

__all__ = ['loadCamera']

def loadCamera(repoDir):
    """Load a camera given the path to its description

    I use this just in testing from the interpreter prompt.
    In general, it's probably best to do butler.get('camera')
    @param repoDir:  path to the root of the camera description tree
    """
    inputPath = os.path.join(repoDir, "description", "camera")
    camConfigPath = os.path.join(inputPath, "camera.py")
    camConfig = CameraConfig()
    camConfig.load(camConfigPath)
    lsstSimMapper = LsstSimMapper
    return makeCameraFromPath(camConfig, inputPath, lsstSimMapper.getShortCcdName)
