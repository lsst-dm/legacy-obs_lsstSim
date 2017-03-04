from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
import os.path
from lsst.utils import getPackageDir
config.charImage.refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
config.calibrate.astromRefObjLoader.retarget(LoadIndexedReferenceObjectsTask)
config.calibrate.photoRefObjLoader.retarget(LoadIndexedReferenceObjectsTask)

config.charImage.repair.doCosmicRay=True

config.calibrate.photoCal.doSelectUnresolved = False
config.charImage.installSimplePsf.fwhm=1.

config.charImage.repair.cosmicray.nCrPixelMax=1000000
config.calibrate.astrometry.matcher.numBrightStars=200
config.calibrate.photoCal.matcher.numBrightStars=200

# Allows u-band to lock on to correct locus
# Does not seem to hurt r-band data
config.charImage.measurePsf.starSelector["objectSize"].widthStdAllowed = 1.

config.charImage.measurePsf.psfDeterminer.name = "pca"
config.charImage.measurePsf.psfDeterminer['pca'].kernelSize=25.
config.charImage.measurePsf.psfDeterminer['pca'].kernelSizeMax=25
config.charImage.measurePsf.psfDeterminer['pca'].kernelSizeMin=25

# Shape HSM
# I don't think we need this at the charImage stage
# config.charImage.measurement.load(os.path.join(getPackageDir("meas_extensions_shapeHSM"), "config", "enable.py"))
config.calibrate.measurement.load(os.path.join(getPackageDir("meas_extensions_shapeHSM"), "config", "enable.py"))
config.calibrate.measurement.plugins["ext_shapeHSM_HsmShapeRegauss"].deblendNChild = "deblend_nChild"
