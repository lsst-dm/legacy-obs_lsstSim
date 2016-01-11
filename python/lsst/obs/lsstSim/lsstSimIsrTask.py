#
# LSST Data Management System
# Copyright 2008-2016 AURA/LSST.
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
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsstDebug import getDebugFrame
from lsst.afw.display import getDisplay
from lsst.ip.isr import IsrTask
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
        target = SnapCombineTask,
        doc = "Combine snaps task",
    )

    def setDefaults(self):
        IsrTask.ConfigClass.setDefaults(self)
        self.doDark = False # LSSTSims do not include darks at this time
        self.snapCombine.averageKeys = ("TAI", "MJD-OBS", "AIRMASS", "AZIMUTH", "ZENITH",
            "ROTANG", "SPIDANG", "ROTRATE")
        self.snapCombine.sumKeys = ("EXPTIME", "CREXPTM", "DARKTIME")


class LsstSimIsrTask(IsrTask):
    """
    \section obs_lsstSim_isr_Debug Debug variables

    The \link lsst.pipe.base.cmdLineTask.CmdLineTask command line task\endlink interface supports a
    flag \c --debug, \c -d to import \b debug.py from your \c PYTHONPATH; see <a
    href="http://lsst-web.ncsa.illinois.edu/~buildbot/doxygen/x_masterDoxyDoc/base_debug.html">
    Using lsstDebug to control debugging output</a> for more about \b debug.py files.

    The available variables in LsstSimIsrTask are:
    <DL>
      <DT> \c display
      <DD> A dictionary containing debug point names as keys with frame number as value. Valid keys are:
        <DL>
          <DT> snapExp0
          <DD> Display ISR-corrected snap 0
          <DT> snapExp1
          <DD> Display ISR-corrected snap 1
          <DT> postISRCCD
          <DD> Display final exposure
        </DL>
    </DL>
    """
    ConfigClass = LsstSimIsrConfig

    def __init__(self, **kwargs):
        IsrTask.__init__(self, **kwargs)
        self.makeSubtask("snapCombine")

    def unmaskSatHotPixels(self, exposure):
        mi = exposure.getMaskedImage()
        mask = mi.getMask()
        maskarr = mask.getArray()
        badBitmask = numpy.array(mask.getPlaneBitMask("BAD"), dtype=maskarr.dtype)
        satBitmask = numpy.array(mask.getPlaneBitMask("SAT"), dtype=maskarr.dtype)
        orBitmask = badBitmask|satBitmask
        andMask = ~satBitmask
        idx = numpy.where((maskarr&orBitmask)==orBitmask)
        maskarr[idx] &= andMask

    def saturationInterpolation(self, ccdExposure):
        """!Unmask hot pixels and interpolate over saturated pixels, in place

        \param[in,out]  ccdExposure     exposure to process

        \warning:
        - Call saturationDetection first, so that saturated pixels have been identified in the "SAT" mask.
        - Call this after CCD assembly, since saturated regions may cross amplifier boundaries
        """
        self.unmaskSatHotPixels(ccdExposure)
        super(LsstSimIsrTask, self).saturationInterpolation(ccdExposure)

    @pipeBase.timeMethod
    def runDataRef(self, sensorRef):
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
            ccdExposure = snapRef.get('raw')
            isrData = self.readIsrData(snapRef, ccdExposure)
            ccdExposure = self.run(ccdExposure, **isrData.getDict()).exposure
            snapDict[snapId] = ccdExposure
    
            if self.config.doWriteSnaps:
                sensorRef.put(ccdExposure, "snapExp", snap=snapId)

            frame = getDebugFrame(self._display, "snapExp%d" % (snapId,))
            if frame:
                getDisplay(frame).mtv(ccdExposure)
        
        if self.config.doSnapCombine:
            loadSnapDict(snapDict, snapIdList=(0, 1), sensorRef=sensorRef)
            postIsrExposure = self.snapCombine.run(snapDict[0], snapDict[1]).exposure
        else:
            self.log.log(self.log.WARN, "doSnapCombine false; using snap 0 as the result")
            loadSnapDict(snapDict, snapIdList=(0,), sensorRef=sensorRef)
            postIsrExposure = snapDict[0]

        if self.config.doWrite:
            sensorRef.put(postIsrExposure, "postISRCCD")

        frame = getDebugFrame(self._display, "postISRCCD")
        if frame:
            getDisplay(frame).mtv(postIsrExposure)
                
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
    
