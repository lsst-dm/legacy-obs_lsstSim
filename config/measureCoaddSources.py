from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
import os
from lsst.utils import getPackageDir

config.coaddName = 'deep'
config.match.refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
config.doPropagateFlags = False

import lsst.meas.modelfit
config.measurement.plugins.names |= ["modelfit_DoubleShapeletPsfApprox", "modelfit_CModel"]
config.measurement.slots.modelFlux = 'modelfit_CModel'

config.measurement.load(os.path.join(getPackageDir("meas_extensions_shapeHSM"), "config", "enable.py"))
config.measurement.plugins["ext_shapeHSM_HsmShapeRegauss"].deblendNChild = "deblend_nChild"
config.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.985
