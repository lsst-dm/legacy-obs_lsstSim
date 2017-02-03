from lsst.meas.algorithms import LoadIndexedReferenceObjectsTask
config.refObjLoader.retarget(LoadIndexedReferenceObjectsTask)

config.astrometer.matcher.numBrightStars=200

config.getTemplate.coaddName='goodSeeing'
config.coaddName='goodSeeing'
config.kernelSourcesFromRef=True
config.doDecorrelation=True
