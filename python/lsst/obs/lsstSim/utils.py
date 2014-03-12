import os
from lsst.afw.cameraGeom import CameraFactoryTask, CameraConfig
from .lsstSimMapper import LsstSimMapper

__ALL__ = ['loadCamera']

def loadCamera(repoDir):
    inputPath = os.path.join(repoDir, "description", "camera")
    camConfigPath = os.path.join(inputPath, "camera.py")
    camConfig = CameraConfig()
    camConfig.load(camConfigPath)
    cameraTask = CameraFactoryTask()
    lsstSimMapper = LsstSimMapper
    return cameraTask.run(camConfig, inputPath, lsstSimMapper.getShortCcdName)
