# overrides for pipe_tasks CoaddTask.ConfigClass
from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask

root.select.retarget(SelectLsstImagesTask)
