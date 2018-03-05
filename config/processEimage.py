from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
import os.path
from lsst.utils import getPackageDir
config.charImage.refObjLoader.retarget(LoadIndexedReferenceObjectsTask)
config.calibrate.astromRefObjLoader.retarget(LoadIndexedReferenceObjectsTask)
config.calibrate.photoRefObjLoader.retarget(LoadIndexedReferenceObjectsTask)

config.charImage.repair.doCosmicRay=True

config.charImage.installSimplePsf.fwhm=2.

config.charImage.repair.cosmicray.nCrPixelMax=1000000

# Allows u-band to lock on to correct locus
# Does not seem to hurt r-band data
config.charImage.measurePsf.starSelector["objectSize"].widthStdAllowed = 1.

import lsst.meas.extensions.psfex.psfexPsfDeterminer

config.charImage.measurePsf.psfDeterminer.name = "psfex"
#config.charImage.measurePsf.psfDeterminer['pca'].kernelSize=25.
#config.charImage.measurePsf.psfDeterminer['pca'].kernelSizeMax=25
#config.charImage.measurePsf.psfDeterminer['pca'].kernelSizeMin=25

import lsst.meas.modelfit
import lsst.meas.extensions.photometryKron
config.charImage.measurement.plugins.names |= ["modelfit_DoubleShapeletPsfApprox"]
config.charImage.catalogCalculation.plugins['base_ClassificationExtendedness'].fluxRatio = 0.985
config.charImage.measurement.plugins.names |= ["ext_photometryKron_KronFlux"]

# Shape HSM
config.charImage.measurement.load(os.path.join(getPackageDir("meas_extensions_shapeHSM"), "config", "enable.py"))
# config.charImage.measurement.plugins["ext_shapeHSM_HsmShapeRegauss"].deblendNChild = "deblend_nChild"


# Set up aperture photometry
# 'config' should be a SourceMeasurementConfig

config.charImage.measurement.plugins.names |= ["base_CircularApertureFlux"]
# Roughly (1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0, 11.3, 16.0, 22.6 arcsec) in diameter: 2**(0.5*i)
# (assuming plate scale of 0.168 arcsec pixels)
config.charImage.measurement.plugins["base_CircularApertureFlux"].radii = [3.0, 4.5, 6.0, 9.0, 12.0, 17.0, 25.0, 35.0, 50.0, 70.0]

# Use a large aperture to be independent of seeing in calibration
config.charImage.measurement.plugins["base_CircularApertureFlux"].maxSincRadius = 12.0

config.calibrate.measurement.plugins.names |= ["ext_photometryKron_KronFlux"]

# Shape HSM
config.calibrate.measurement.load(os.path.join(getPackageDir("meas_extensions_shapeHSM"), "config", "enable.py"))
config.calibrate.measurement.plugins["ext_shapeHSM_HsmShapeRegauss"].deblendNChild = "deblend_nChild"


# Set up aperture photometry
# 'config' should be a SourceMeasurementConfig

config.calibrate.measurement.plugins.names |= ["base_CircularApertureFlux"]
# Roughly (1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0, 11.3, 16.0, 22.6 arcsec) in diameter: 2**(0.5*i)
# (assuming plate scale of 0.168 arcsec pixels)
config.calibrate.measurement.plugins["base_CircularApertureFlux"].radii = [3.0, 4.5, 6.0, 9.0, 12.0, 17.0, 25.0, 35.0, 50.0, 70.0]

# Use a large aperture to be independent of seeing in calibration
config.calibrate.measurement.plugins["base_CircularApertureFlux"].maxSincRadius = 12.0
