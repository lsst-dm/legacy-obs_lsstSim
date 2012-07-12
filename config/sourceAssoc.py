root.inputLevel = "sensor"
root.inputSourceDataset = "src"
root.inputCalexpMetadataDataset = "calexp_md"

try:
    import lsst.meas.extensions.multiShapelet
    root.measSlots.modelFlux = "multishapelet.combo.flux"
except ImportError:
    # TODO: find a better way to log this
    print "WARNING: Could not import lsst.meas.extensions.multiShapelet; model fluxes not enabled!"
