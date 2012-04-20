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
        doc = "Combine Snaps? If False then use snap 0 as the visitCCD.",
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
        """Do instrument signature removal on an exposure: saturation, bias, overscan, dark, flat, fringe correction

        @param sensorRef daf.persistence.butlerSubset.ButlerDataRef of the data to be processed
        @return a pipeBase.Struct with fields:
        - exposure: the exposure after application of ISR
        """
        snapDict = dict()
        for snapRef in sensorRef.subItems(level="snap"):
            snapId = snapRef.dataId['snap']
            if snapId not in (0, 1):
                raise RuntimeError("Unrecognized snapId=%s" % (snapId,))

            self.log.log(self.log.INFO, "Performing ISR on snap %s" % (snapRef.dataId))
            # perform amp-level ISR
            ampExpList = list()
            for ampRef in snapRef.subItems(level="channel"):
                self.log.log(self.log.INFO, "Performing ISR on channel %s" % (ampRef.dataId))
                ampExp = ampRef.get("raw")
                amp = cameraGeom.cast_Amp(ampExp.getDetector())
        
                self.saturationDetection(ampExp, amp)
    
#                self.linearization(ampExp, ampRef, amp)
    
                self.overscanCorrection(ampExp, amp)
    
                self.biasCorrection(ampExp, ampRef)
                
                isr.updateVariance(ampExp.getMaskedImage(), amp.getElectronicParams().getGain())
                
                self.darkCorrection(ampExp, ampRef)
                
                self.flatCorrection(ampExp, ampRef)
                
                ampExpList.append(ampExp)
        
            assembleRes = self.assembleCcd.run(ampExpList)
            del ampExpList
            ccdExp = assembleRes.exposure
            ccd = cameraGeom.cast_Ccd(ccdExp.getDetector())

            self.maskAndInterpDefect(ccdExp, ccd)
            
            self.saturationInterpolation(ccdExp)

            self.maskAndInterpNan(ccdExp)

            self.display("postISRCCD%d" % (snapId,), exposure=ccdExp)

            snapDict[snapId] = ccdExp
    
            if self.config.doWrite:
                sensorRef.put(ccdExp, "postISRCCD")
        
        if self.config.doSnapCombine:
            for snapId in (0, 1):
                if snapId not in snapDict:
                    snapDict[snapId] = sensorRef.get("postISRCCD", snap=snapId)

            combineRes = self.snapCombine.run(snapDict[0], snapDict[1])
            outExposure = combineRes.outExposure
        else:
            outExposure = snapDict[0]

        if self.config.doWrite:
            sensorRef.put(outExposure, "visitCCD")
        self.display("visitCcd", exposure=outExposure)
                
        return pipeBase.Struct(
            exposure = outExposure,
        )
    
