from lsst.obs.lsstSim import MaxPsfWcsSelectImagesTask

config.select.retarget(MaxPsfWcsSelectImagesTask)
config.doPsfMatch=True
config.modelPsf.size=25
config.modelPsf.addWing=False

# Size (rows) in pixels of each SpatialCell for spatial modeling
config.warpAndPsfMatch.psfMatch.kernel['AL'].sizeCellX=500

# Size (columns) in pixels of each SpatialCell for spatial modeling
config.warpAndPsfMatch.psfMatch.kernel['AL'].sizeCellY=500

