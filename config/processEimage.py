config.charImage.repair.doCosmicRay=True

config.calibrate.photoCal.doSelectUnresolved = False
config.charImage.installSimplePsf.fwhm=2.

# Allows u-band to lock on to correct locus
# Does not seem to hurt r-band data
config.charImage.measurePsf.starSelector["objectSize"].widthStdAllowed = 1.

config.charImage.measurePsf.psfDeterminer.name = "pca"
config.charImage.measurePsf.psfDeterminer['pca'].kernelSize=25.
config.charImage.measurePsf.psfDeterminer['pca'].kernelSizeMax=25
config.charImage.measurePsf.psfDeterminer['pca'].kernelSizeMin=25
