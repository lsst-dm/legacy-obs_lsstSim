# overrides for pipe_tasks ReportImagesToCoaddTask.ConfigClass
from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask

config.select.retarget(SelectLsstImagesTask)
