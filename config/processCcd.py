"""lsstSim-specific overrides for the processCcd task
"""
from lsst.obs.lsstSim import LsstSimIsrTask

root.isr.retarget(LsstSimIsrTask)

try:
    import lsst.meas.extensions.multiShapelet
    root.measurement.algorithms.names = set(root.measurement.algorithms.names) | lsst.meas.extensions.multiShapelet.algorithms
    root.measurement.slots.modelFlux = "multishapelet.combo.flux"
except ImportError:
    # TODO: find a better way to log this
    print "WARNING: Could not import lsst.meas.extensions.multiShapelet; model fluxes not enabled!"
