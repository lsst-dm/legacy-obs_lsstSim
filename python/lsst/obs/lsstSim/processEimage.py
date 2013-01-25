#!/usr/bin/env python
#
# LSST Data Management System
# Copyright 2008, 2009, 2010, 2011, 2012, 2013 LSST Corporation.
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#
from lsst.pipe.base.argumentParser import ArgumentParser
from lsst.pipe.tasks.processImage import ProcessImageTask
import lsst.afw.image as afwImage
import lsst.afw.table as afwTable
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase

class ProcessEimageConfig(ProcessImageTask.ConfigClass):
    """Config for ProcessCcd"""
    doSetVariance = pexConfig.Field(dtype=bool, default=True, doc = "Set the variance plane in the eimage?")
    varianceType = pexConfig.ChoiceField(dtype=str, default="image", 
                                         allowed={"image":"set variance from image plane", 
                                                  "value":"set variance to a value"}, 
                                         doc="Choose method for setting the variance")
    varianceValue = pexConfig.Field(dtype=float, default=0.01, doc = "Value to use in the variance plane.")
    maskEdgeBorder = pexConfig.Field(dtype=int, default=0, doc = "Set mask to EDGE for a border of x pixels")

class ProcessEimageTask(ProcessImageTask):
    """Process an Eimage CCD
    
    Available steps include:
    - calibrate
    - detect sources
    - measure sources
    """
    ConfigClass = ProcessEimageConfig
    _DefaultName = "processEimage"
    dataPrefix = ""

    def __init__(self, **kwargs):
        ProcessImageTask.__init__(self, **kwargs)

    def makeIdFactory(self, sensorRef):
        expBits = sensorRef.get("ccdExposureId_bits")
        expId = long(sensorRef.get("ccdExposureId"))
        return afwTable.IdFactory.makeSource(expId, 64 - expBits)        

    @pipeBase.timeMethod
    def run(self, sensorRef):
        """Process one Eimage
        
        @param sensorRef: sensor-level butler data reference
        @return pipe_base Struct containing these fields:
        - exposure: calibrated exposure (calexp): as computed if config.doCalibrate,
            else as upersisted and updated if config.doDetection, else None
        - calib: object returned by calibration process if config.doCalibrate, else None
        - apCorr: aperture correction: as computed config.doCalibrate, else as unpersisted
            if config.doMeasure, else None
        - sources: detected source if config.doPhotometry, else None
        """
        self.log.info("Processing %s" % (sensorRef.dataId))

        inputExposure = sensorRef.get(self.dataPrefix + "eimage")

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
        
        # delegate most of the work to ProcessImageTask
        return self.process(sensorRef, inputExposure)

    def setVariance(self, inputExposure):
        if self.config.varianceType == 'value':
            var = inputExposure.getMaskedImage().getVariance()
            var.set(self.config.varianceValue)
        elif self.config.varianceType == 'image':
            var = inputExposure.getMaskedImage().getVariance()
            var <<= inputExposure.getMaskedImage().getImage()

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

    @classmethod
    def _makeArgumentParser(cls):
        """Create an argument parser

        Subclasses may wish to override, e.g. to change the dataset type or data ref level
        """
        return ArgumentParser(name=cls._DefaultName, datasetType="eimage")
