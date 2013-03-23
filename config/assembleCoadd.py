from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask
from lsst.obs.lsstSim.selectFluxMag0 import SelectLsstSimFluxMag0Task

root.select.retarget(SelectLsstImagesTask)
root.scaleZeroPoint.selectFluxMag0.retarget(SelectLsstSimFluxMag0Task)
root.scaleZeroPoint.doInterpScale=True
