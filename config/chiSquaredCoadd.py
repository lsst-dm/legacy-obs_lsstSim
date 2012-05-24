# overrides for pipe_tasks ChiSquaredCoaddTask.ConfigClass
from lsst.obs.lsstSim.selectLsstImages import SelectLSSTImagesTask

root.select.retarget(SelectLSSTImagesTask)
