from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
config.coaddName = 'deep'
config.match.refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
config.doPropagateFlags = False

import lsst.meas.modelfit
config.measurement.plugins.names |= ["modelfit_DoubleShapeletPsfApprox", "modelfit_CModel"]
config.measurement.slots.modelFlux = 'modelfit_CModel'
#config.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.985
