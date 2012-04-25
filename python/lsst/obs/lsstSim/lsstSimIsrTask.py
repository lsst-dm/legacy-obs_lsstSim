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
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsst.ip.isr import IsrTask
from .snapCombine import SnapCombineTask
from .lsstSimAssembleCcdTask import LsstSimAssembleCcdTask

__all__ = ["LsstSimIsrTask"]

class LsstSimIsrConfig(IsrTask.ConfigClass):
    doWriteSnaps = pexConfig.Field(
        dtype = bool,
        doc = "Persist postIsrCCD for each snap?",
        default = True,
    )
    doSnapCombine = pexConfig.Field(
        dtype = bool,
        doc = "Combine Snaps? If False then use snap 0 as output exposure.",
        default = True,
    )
    snapCombine = pexConfig.ConfigurableField(
        target = SnapCombineTask,
        doc = "Combine snaps task",
    )
    
    def setDefaults(self):
        self.assembleCcdTask.retarget(LsstSimAssembleCcdTask)


class LsstSimIsrTask(IsrTask):
    ConfigClass = LsstSimIsrConfig

    def __init__(self, **kwargs):
        IsrTask.__init__(self, **kwargs)
        self.makeSubtask("snapCombine")

    @pipeBase.timeMethod
    def run(self, sensorRef):
        """Do instrument signature removal on an exposure
        
        Correct for saturation, bias, overscan, dark, flat..., perform CCD assembly,
        optionally combine snaps, and interpolate over defects and saturated pixels.
        
        If config.doSnapCombine true then combine the two ISR-corrected snaps to produce the final exposure.
        If config.doSnapCombine false then uses ISR-corrected snap 0 as the final exposure.
        In either case, the final exposure is persisted as "visitCCD" if config.doWriteSpans is True,
        and the two snaps are persisted as "postISRCCD" if config.doWriteSnaps is True.

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
            ampExpList = list()
            for ampRef in snapRef.subItems(level="channel"):
                ampExp = ampRef.get("raw")
                amp = cameraGeom.cast_Amp(ampExp.getDetector())
        
                self.saturationDetection(ampExp, amp)
    
                self.overscanCorrection(ampExp, amp)
    
                if self.config.doBias:
                    self.biasCorrection(ampExp, ampRef)
                
                if self.config.doDark:
                    self.darkCorrection(ampExp, ampRef)
                
                self.updateVariance(ampExp, amp)
                
                if self.config.doFlat:
                    self.flatCorrection(ampExp, ampRef)
                
                ampExpList.append(ampExp)
        
            ccdExp = self.assembleCcd.run(ampExpList).exposure
            del ampExpList
            ccd = cameraGeom.cast_Ccd(ccdExp.getDetector())

            self.maskAndInterpDefect(ccdExp, ccd)
            
            self.saturationInterpolation(ccdExp)

            self.maskAndInterpNan(ccdExp)

            snapDict[snapId] = ccdExp
    
            if self.config.doWriteSnaps:
                sensorRef.put(ccdExp, "postISRCCD", snap=snapId)

            self.display("postISRCCD%d" % (snapId,), exposure=ccdExp)
        
        if self.config.doSnapCombine:
            loadSnapDict(snapDict, snapIdList=(0, 1), sensorRef=sensorRef)
            outExposure = self.snapCombine.run(snapDict[0], snapDict[1]).outExposure
        else:
            self.log.log(self.log.WARN, "doSnapCombine false; using snap 0 as the result")
            loadSnapDict(snapDict, snapIdList=(0,), sensorRef=sensorRef)
            outExposure = snapDict[0]

        if self.config.doWrite:
            sensorRef.put(outExposure, "visitCCD")

        self.display("visitCCD", exposure=outExposure)
                
        return pipeBase.Struct(
            exposure = outExposure,
        )

def loadSnapDict(snapDict, snapIdList, sensorRef):
    """Load missing snaps from disk.
    
    @paramp[in,out] snapDict: a dictionary of snapId: snap exposure ("postISRCCD")
    @param[in] snapIdList: a list of snap IDs
    @param[in] sensorRef: sensor reference for snap, excluding the snap ID.
    """
    for snapID in snapIdList:
        if snapId not in snapDict:
            snapExposure = sensorRef.get("postISRCCD", snap=snapId)
            if snapExposure is None:
                raise RuntimeError("Could not find postISRCCD for snap=%s; id=%s" % (snapId, sensorRef.dataId))
            snapDict[snapId] = snapExposure
    
