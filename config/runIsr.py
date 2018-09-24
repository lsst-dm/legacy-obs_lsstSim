"""
LSST Sim-specific overrides for RunIsrTask
"""
import os.path

from lsst.utils import getPackageDir
from lsst.obs.lsstSim.lsstSimIsrTask import LsstSimIsrTask

obsConfigDir = os.path.join(getPackageDir("obs_lsstSim"), "config")

config.isr.retarget(LsstSimIsrTask)
config.isr.load(os.path.join(obsConfigDir, "isr.py"))
