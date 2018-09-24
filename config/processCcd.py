"""
LSST Sim-specific overrides for the ProcessCcdTask
"""
import os.path

from lsst.utils import getPackageDir
from lsst.obs.lsstSim import LsstSimIsrTask

obsConfigDir = os.path.join(getPackageDir("obs_lsstSim"), "config"))

config.isr.retarget(LsstSimIsrTask)
config.isr.load(os.path.join(obsConfigDir, "isr.py")

# this was the default prior to DM-11521.  New default is 2000.
config.calibrate.deblend.maxFootprintSize=0

try:
    import lsst.meas.extensions.multiShapelet
    config.calibrate.measurement.algorithms.names = set(
        config.measurement.algorithms.names) | lsst.meas.extensions.multiShapelet.algorithms
    config.calibrate.measurement.slots.modelFlux = "multishapelet.combo.flux"
except ImportError:
    # TODO: find a better way to log this
    print("WARNING: Could not import lsst.meas.extensions.multiShapelet; model fluxes not enabled!")
