from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask
from lsst.obs.lsstSim.scaleLsstSimZeroPoint import ScaleLsstSimZeroPointTask

root.select.retarget(SelectLsstImagesTask)
root.scaleZeroPoint.retarget(ScaleLsstSimZeroPointTask)
