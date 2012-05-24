# overrides for pipe_tasks OutlierRejectedCoaddTask.ConfigClass
from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask

root.select.retarget(SelectLsstImagesTask)
