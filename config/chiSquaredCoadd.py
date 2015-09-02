# overrides for pipe_tasks ChiSquaredCoaddTask.ConfigClass
from lsst.obs.lsstSim.selectLsstImages import SelectLSSTImagesTask

config.select.retarget(SelectLSSTImagesTask)
