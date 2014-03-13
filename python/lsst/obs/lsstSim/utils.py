import os
from lsst.afw.cameraGeom import makeCameraFromPath, CameraConfig
from .lsstSimMapper import LsstSimMapper

__ALL__ = ['loadCamera']

def loadCamera(repoDir):
    inputPath = os.path.join(repoDir, "description", "camera")
    camConfigPath = os.path.join(inputPath, "camera.py")
    camConfig = CameraConfig()
    camConfig.load(camConfigPath)
    lsstSimMapper = LsstSimMapper
    return makeCameraFromPath(camConfig, inputPath, lsstSimMapper.getShortCcdName)
