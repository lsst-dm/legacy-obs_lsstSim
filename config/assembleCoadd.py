from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask
from lsst.obs.lsstSim.selectFluxMag0 import SelectLsstSimFluxMag0Task
from lsst.pipe.tasks.scaleZeroPoint import SpatialScaleZeroPointTask

#config.select.retarget(SelectLsstImagesTask)
#Retarget to database backed spatially varying ZP
#config.scaleZeroPoint.retarget(SpatialScaleZeroPointTask)
#config.scaleZeroPoint.selectFluxMag0.retarget(SelectLsstSimFluxMag0Task)

#to retarget back to the spatially invariant version,
#put the following two lines in your config file:
#from lsst.pipe.tasks.scaleZeroPoint import ScaleZeroPointTask
#config.scaleZeroPoint.retarget(ScaleZeroPointTask)
