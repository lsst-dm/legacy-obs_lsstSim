try:
    # Enable multiShapelet for model mags.
    import lsst.meas.extensions.multiShapelet
    root.measurement.algorithms.names |= lsst.meas.extensions.multiShapelet.algorithms
    root.measurement.slots.modelFlux = "multishapelet.combo.flux"
    # too many INTERP pixels on coadds, so we relax the masking in modeling
    for name in ("exp", "dev", "combo"):
        root.measurement.algorithms["multishapelet." + name].badMaskPlanes = ["EDGE", "SAT"]
except ImportError:
    # TODO: find a better way to log this
    print "WARNING: Could not import lsst.meas.extensions.multiShapelet; model fluxes not enabled!"

