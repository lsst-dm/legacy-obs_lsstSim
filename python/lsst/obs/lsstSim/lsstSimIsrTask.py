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
import lsst.afw.image as afwImage
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsst.ip.isr import AssembleCcdTask, IsrTask
from lsst.pipe.tasks.snapCombine import SnapCombineTask 
import numpy

__all__ = ["LsstSimIsrTask"]

class LsstSimIsrConfig(IsrTask.ConfigClass):
    doWriteSnaps = pexConfig.Field(
        dtype = bool,
        doc = "Persist snapExp for each snap?",
        default = True,
    )
    doSnapCombine = pexConfig.Field(
        dtype = bool,
        doc = "Combine Snaps? If False then use snap 0 as output exposure.",
        default = True,
    )
    snapCombine = pexConfig.ConfigurableField(
        target = w,
        doc = "Combine snaps task",
    )

    def setDefaults(self):
        IsrTask.ConfigClass.setDefaults(self)
        self.doDark = False # LSSTSims do not include darks at this time
        self.snapCombine.keysToAverage = ("TAI", "MJD-OBS", "AIRMASS", "AZIMUTH", "ZENITH",
            "ROTANG", "SPIDANG", "ROTRATE")
        self.snapCombine.keysToSum = ("EXPTIME", "CREXPTM", "DARKTIME")


class LsstSimIsrTask(IsrTask):
    ConfigClass = LsstSimIsrConfig

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
    def run(self, sensorRef):
        """Do instrument signature removal on an exposure
        
        Correct for saturation, bias, overscan, dark, flat..., perform CCD assembly,
        optionally combine snaps, and interpolate over defects and saturated pixels.
        
        If config.doSnapCombine true then combine the two ISR-corrected snaps to produce the final exposure.
        If config.doSnapCombine false then uses ISR-corrected snap 0 as the final exposure.
        In either case, the final exposure is persisted as "postISRCCD" if config.doWriteSpans is True,
        and the two snaps are persisted as "snapExp" if config.doWriteSnaps is True.

        @param sensorRef daf.persistence.butlerSubset.ButlerDataRef of the data to be processed
        @return a pipeBase.Struct with fields:
        - exposure: the exposure after application of ISR
        """
        self.log.log(self.log.INFO, "Performing ISR on sensor %s" % (sensorRef.dataId))
        snapDict = dict()
        for snapRef in sensorRef.subItems(level="snap"):
            snapId = snapRef.dataId['snap']
            if snapId not in (0, 1):
                raise RuntimeError("Unrecognized snapId=%s" % (snapId,))

            self.log.log(self.log.INFO, "Performing ISR on snap %s" % (snapRef.dataId))
            # perform amp-level ISR
            ampExposureList = list()
            for ampRef in snapRef.subItems(level="channel"):
                ampExposure = ampRef.get("raw")
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
                
                ampExposureList.append(ampExposure)
        
            ccdExposure = self.assembleCcd.assembleAmpList(ampExposureList)
            del ampExposureList

            self.maskAndInterpDefect(ccdExposure)

            self.unmaskSatHotPixels(ccdExposure)
            
            self.saturationInterpolation(ccdExposure)

            self.maskAndInterpNan(ccdExposure)

            snapDict[snapId] = ccdExposure
    
            if self.config.doWriteSnaps:
                sensorRef.put(ccdExposure, "snapExp", snap=snapId)

            self.display("snapExp%d" % (snapId,), exposure=ccdExposure)
        
        if self.config.doSnapCombine:
            loadSnapDict(snapDict, snapIdList=(0, 1), sensorRef=sensorRef)
            postIsrExposure = self.snapCombine.run(snapDict[0], snapDict[1]).exposure
        else:
            self.log.log(self.log.WARN, "doSnapCombine false; using snap 0 as the result")
            loadSnapDict(snapDict, snapIdList=(0,), sensorRef=sensorRef)
            postIsrExposure = snapDict[0]

        if self.config.doWrite:
            sensorRef.put(postIsrExposure, "postISRCCD")

        self.display("postISRCCD", exposure=postIsrExposure)
                
        return pipeBase.Struct(
            exposure = postIsrExposure,
        )

def loadSnapDict(snapDict, snapIdList, sensorRef):
    """Load missing snaps from disk.
    
    @paramp[in,out] snapDict: a dictionary of snapId: snap exposure ("snapExp")
    @param[in] snapIdList: a list of snap IDs
    @param[in] sensorRef: sensor reference for snap, excluding the snap ID.
    """
    for snapId in snapIdList:
        if snapId not in snapDict:
            snapExposure = sensorRef.get("snapExp", snap=snapId)
            if snapExposure is None:
                raise RuntimeError("Could not find snapExp for snap=%s; id=%s" % (snapId, sensorRef.dataId))
            snapDict[snapId] = snapExposure
    
