#
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
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
# see <http://www.lsstcorp.org/LegalNotices/>.
#
import lsst.afw.cameraGeom as cameraGeom
import lsst.meas.algorithms as measAlg
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsst.ip.isr import IsrTask
import lsst.ip.isr as ipIsr
from lsst.pipe.tasks.snapCombine import SnapCombineTask 
import numpy

__all__ = ["LsstSimCalibIsrTask"]

class LsstSimCalibIsrConfig(IsrTask.ConfigClass):
    doSnapCombine = pexConfig.Field(
        dtype = bool,
        doc = "Combine snaps into a single image?",
        default = True,
    )
    snapCombine = pexConfig.ConfigurableField(
        target = SnapCombineTask,
        doc = "Combine snaps task",
    )
    doInterpSaturated = pexConfig.Field(
        dtype = bool,
        doc = "Do saturation interpolation?",
        default = False,
    )


class LsstSimCalibIsrTask(IsrTask):
    ConfigClass = LsstSimCalibIsrConfig

    def __init__(self, **kwargs):
        IsrTask.__init__(self, **kwargs)
        self.transposeForInterpolation = True # temporary hack until LSST data is in proper order
        self.makeSubtask("snapCombine")

    def unmaskSatHotPixels(self, exposure):
        mi = exposure.getMaskedImage()
        mask = mi.getMask()
        badBitmask = mask.getPlaneBitMask("BAD")
        satBitmask = mask.getPlaneBitMask("SAT")
        orBitmask = badBitmask|satBitmask
        andMask = ~satBitmask
        maskarr = mask.getArray()
        idx = numpy.where((maskarr&orBitmask)==orBitmask)
        maskarr[idx] &= andMask

    @pipeBase.timeMethod
    def run(self, ampRef):
        """Do instrument signature removal on a calibration exposure
        
        If config.doSnapCombine true then combine the two ISR-corrected amp snaps to produce the final exposure.
        If config.doSnapCombine false then uses ISR-corrected snap 0 as the final exposure.

        @param ampRef daf.persistence.butlerSubset.ButlerDataRef of the data to be processed
        @return a pipeBase.Struct with fields:
        - exposure: the exposure after application of ISR
        """
        self.log.log(self.log.INFO, "Performing ISR on amp %s" % (ampRef.dataId))
        snapArr = []
        dataId = ampRef.dataId
        dataButler = ampRef.butlerSubset.butler
        for snap in (0,1):
            dataId['snap'] = snap
            snapRef = dataButler.dataRef("raw", dataId=dataId)
            self.log.log(self.log.INFO, "Performing ISR on snap %s" % (snapRef.dataId))
            ampExposure = snapRef.get("raw")
            amp = cameraGeom.cast_Amp(ampExposure.getDetector())

            ampExposure = self.convertIntToFloat(ampExposure)
            ampExpDataView = ampExposure.Factory(ampExposure, amp.getDiskDataSec(), afwImage.PARENT)
           
            self.saturationDetection(ampExposure, amp)
    
            self.overscanCorrection(ampExposure, amp)
    
            if self.config.doBias:
                self.biasCorrection(ampExpDataView, ampRef)
                
            if self.config.doDark:
                self.darkCorrection(ampExpDataView, ampRef)
                
            self.updateVariance(ampExpDataView, amp)
                
            if self.config.doFlat:
                self.flatCorrection(ampExpDataView, ampRef)
            snapArr.append(ampExpDataView)

        if self.config.doSnapCombine:
            combinedFrame = self.snapCombine.run(snapArr[0], snapArr[1]).exposure
        else:
            self.log.log(self.log.WARN, "doSnapCombine false; using snap 0 as the result")
            combinedFrame = snapArr[0]
                
        self.fixDefectsAndSat(combinedFrame.getMaskedImage(), amp)
        self.unmaskSatHotPixels(combinedFrame)
        self.maskAndInterpNan(combinedFrame)

        return pipeBase.Struct(
            exposure = combinedFrame,
        )

    def fixDefectsAndSat(self, masterFrame, detector):
        fwhm = self.config.fwhm
        dataBbox = detector.getDataSec(True)
        #Reversing the x and y is essentially a hack since we have to apply the defects in Amp coordinates and they are recorded in chip coordinates
        #This should go away when the data from imSim is all in chip coordinates
        y = dataBbox.getMinX()
        x = dataBbox.getMinY()
        width = dataBbox.getDimensions()[1]
        height = dataBbox.getDimensions()[0]
        #When at detector level, there will not be the need to go through the step of getting the parent
        defectList = cameraGeom.cast_Ccd(detector.getParent()).getDefects() 
        dl = self.transposeDefectList(defectList, dataBbox)
        for d in dl:
            d.shift(-x, -y)
            if detector.getId().getSerial()>8:
                d.shift(0, height - 2*d.getBBox().getMinY()-d.getBBox().getHeight())
        if self.config.doInterpSaturated: #Can't really imagine why you'd need this.
            sdl = self.isr.getDefectListFromMask(masterFrame, 'SAT', growFootprints=0)
            for d in sdl:
                dl.push_back(d)
        ipIsr.maskPixelsFromDefectList(masterFrame, dl, maskName='BAD')
        ipIsr.interpolateDefectList(masterFrame, dl, fwhm)
        return masterFrame

    def transposeDefectList(self, defectList, checkBbox=None):
        retDefectList = measAlg.DefectListT()
        for defect in defectList:
            bbox = defect.getBBox()
            nbbox = afwGeom.Box2I(afwGeom.Point2I(bbox.getMinY(), bbox.getMinX()),
                 afwGeom.Extent2I(bbox.getDimensions()[1], bbox.getDimensions()[0]))
            if checkBbox:
                
                if checkBbox.overlaps(bbox):
                    retDefectList.push_back(measAlg.Defect(nbbox))
                else:
                    pass
            else:
                retDefectList.push_back(measAlg.Defect(nbbox))
        return retDefectList
