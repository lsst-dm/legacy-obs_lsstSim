from __future__ import print_function
config.inputLevel = "sensor"
config.inputSourceDataset = "src"
config.inputCalexpMetadataDataset = "calexp_md"

try:
    import lsst.meas.extensions.multiShapelet
    config.measSlots.modelFlux = "multishapelet.combo.flux"
except ImportError:
    # TODO: find a better way to log this
    print("WARNING: Could not import lsst.meas.extensions.multiShapelet; model fluxes not enabled!")
