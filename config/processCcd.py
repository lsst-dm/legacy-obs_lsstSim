"""lsstSim-specific overrides for the processCcd task
"""
from lsst.obs.lsstSim import LsstSimIsrTask

config.isr.retarget(LsstSimIsrTask)

try:
    import lsst.meas.extensions.multiShapelet
    config.calibrate.detectAndMeasure.measurement.algorithms.names = set(config.measurement.algorithms.names) | lsst.meas.extensions.multiShapelet.algorithms
    config.calibrate.detectAndMeasure.measurement.slots.modelFlux = "multishapelet.combo.flux"
except ImportError:
    # TODO: find a better way to log this
    print "WARNING: Could not import lsst.meas.extensions.multiShapelet; model fluxes not enabled!"
