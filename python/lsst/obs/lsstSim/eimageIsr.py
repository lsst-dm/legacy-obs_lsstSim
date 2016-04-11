#!/usr/bin/env python
#
# LSST Data Management System
# Copyright 2008-2015 AURA/LSST.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <https://www.lsstcorp.org/LegalNotices/>.
#
import lsst.afw.image as afwImage
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
import numpy

class EimageIsrConfig(pexConfig.Config):
    """Config for EimageIsrTask"""
    doAddNoise = pexConfig.Field(dtype=bool, default=False,
                                 doc="Add a flat Poisson noise background to the eimage?")
    rngSeed = pexConfig.Field(dtype=int, default=None, optional=True,
                              doc=("Random number seed used when adding noise (passed directly"
                                   " to numpy at task initialization)"))
    noiseValue = pexConfig.Field(dtype=int, default=1000, doc="Mean of the Poisson distribution in counts")
    doSetVariance = pexConfig.Field(dtype=bool, default=True, doc="Set the variance plane in the eimage?")
    varianceType = pexConfig.ChoiceField(dtype=str, default="image",
                                         allowed={"image":"set variance from image plane",
                                                  "value":"set variance to a value"},
                                         doc="Choose method for setting the variance")
    varianceValue = pexConfig.Field(dtype=float, default=0.01, doc="Value to use in the variance plane.")
    maskEdgeBorder = pexConfig.Field(dtype=int, default=0, doc="Set mask to EDGE for a border of x pixels")


class EimageIsrTask(pipeBase.Task):
    """Load an e-image as an assembled image
    """
    ConfigClass = EimageIsrConfig

    def __init__(self, **kwargs):
        pipeBase.Task.__init__(self, **kwargs)
        numpy.random.seed(self.config.rngSeed)

    @pipeBase.timeMethod
    def runDataRef(self, sensorRef):
        """Load the post instrument signature removal image

        \param[in]  sensorRef        sensor-level butler data reference

        \return     postIsrExposure  exposure to be passed to processCcdExposure
        """
        inputExposure = sensorRef.get("eimage", immediate=True)
        if self.config.doAddNoise:
            self.addNoise(inputExposure)

        if self.config.doSetVariance:
            self.setVariance(inputExposure)

        if self.config.maskEdgeBorder > 0:
            self.maskEdges(inputExposure)

        # We may need to ingest the results of the processing and
        # ingestProcessed.py expects some specific header cards.
        # Set the header cards to values appropriate for an image
        # that has not been read out.
        md = inputExposure.getMetadata()
        md.add('RDNOISE', 0.)
        md.add('SATURATE', 100000)
        md.add('GAINEFF', 1.)
        return pipeBase.Struct(exposure=inputExposure)

    def addNoise(self, inputExposure):
        mi = inputExposure.getMaskedImage()
        (x,y) = mi.getDimensions()
        noiseArr = numpy.random.poisson(self.config.noiseValue, size=x*y).reshape(y,x)
        noiseArr = noiseArr.astype(numpy.float32)
        noiseImage = afwImage.makeImageFromArray(noiseArr)
        mi += noiseImage

    def setVariance(self, inputExposure):
        if self.config.varianceType == 'value':
            var = inputExposure.getMaskedImage().getVariance()
            var.set(self.config.varianceValue)
        elif self.config.varianceType == 'image':
            var = inputExposure.getMaskedImage().getVariance()
            var[:] = inputExposure.getMaskedImage().getImage()

    def maskEdges(self, inputExposure):
        mask = inputExposure.getMaskedImage().getMask()
        edgeBitMask = mask.getPlaneBitMask("EDGE")
        npix = self.config.maskEdgeBorder
        maskArr = mask.getArray()
        # Note, in numpy arrays, y index comes first
        (ys, xs) = maskArr.shape
        maskArr[:npix,:] |= edgeBitMask # Bottom
        maskArr[ys-npix-1:,:] |= edgeBitMask # Top
        maskArr[npix:ys-npix-1,:npix] |= edgeBitMask # Left
        maskArr[npix:ys-npix-1,xs-npix-1:] |= edgeBitMask # Right
