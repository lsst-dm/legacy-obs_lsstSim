from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask
from lsst.obs.lsstSim.selectFluxMag0 import SelectLsstSimFluxMag0Task
from lsst.coadd.utils.scaleZeroPoint import SpatialScaleZeroPointTask

root.select.retarget(SelectLsstImagesTask)
#Retarget to database backed spatially varying ZP
root.scaleZeroPoint.retarget(SpatialScaleZeroPointTask)
root.scaleZeroPoint.selectFluxMag0.retarget(SelectLsstSimFluxMag0Task)

