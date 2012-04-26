"""lsstSim-specific overrides for the processCcd task
"""
from lsst.obs.lsstSim import LsstSimIsrTask

root.isr.retarget(LsstSimIsrTask)
