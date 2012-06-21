# overrides for pipe_tasks ReportImagesToCoaddTask.ConfigClass
from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask

root.select.retarget(SelectLsstImagesTask)
