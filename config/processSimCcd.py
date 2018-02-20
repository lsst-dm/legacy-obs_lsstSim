"""lsstSim-specific overrides for the processCcd task
"""
from __future__ import print_function
from lsst.obs.lsstSim import LsstSimIsrTask
config.isr.retarget(LsstSimIsrTask)
config.isr.doBias=False
config.isr.doDark=False
config.isr.doFlat=True
config.isr.doFringe=False
config.isr.doDefect=False
config.isr.doSnapCombine=False
config.isr.doAssembleCcd=False # we are doing this by hand
config.charImage.doMeasurePsf=False
config.calibrate.doAstrometry=False
config.calibrate.doPhotoCal=False
config.charImage.doApCorr=False
config.calibrate.doApCorr=False

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
