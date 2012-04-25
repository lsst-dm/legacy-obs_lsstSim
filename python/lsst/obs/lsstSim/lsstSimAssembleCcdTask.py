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
import lsst.afw.cameraGeom.utils as cameraGeomUtils
import lsst.afw.image as afwImage
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
import lsst.ip.isr as ipIsr

__all__ = ["LsstSimAssembleCcdTask"]

class LsstSimAssembleCcdTask(ipIsr.AssembleCcdTask):
    """Assemble a CCD
    """
    def run(self, ampExposureList):
        """Assemble a CCD by trimming non-data areas

        @param[in,out]  ampExposureList list of amp exposures to assemble;
                                        the setTrimmed flag of the ccd device info may be modified
        @return a pipe_base Struct with one field:
        - exposure: assembled exposure
        """
        outExposure = self.assemblePixels(ampExposureList=ampExposureList)

        self.setExposureComponents(outExposure=outExposure, inExposure=ampExposureList[0])

        self.display("assembledExposure", exposure=outExposure)
    
        return pipeBase.Struct(exposure=outExposure)
    
    def assemblePixels(self, ampExposureList):
        """Assemble CCD pixels

        @param[in]      ampExposureList   list of amp exposures to assemble
        @param[in]      ccd         device info for assembled exposure
        @return         outExposure assembled exposure (just the pixels data is set)
        """
        ampExp0 = ampExposureList[0]
        amp0 = cameraGeom.cast_Amp(ampExp0.getDetector())
        if amp0 is None:
            raise RuntimeError("No amp detector found in first amp exposure")
        ccd = cameraGeom.cast_Ccd(amp0.getParent())
        if ccd is None:
            raise RuntimeError("No ccd detector found in amp detector")
        ccd.setTrimmed(self.config.doTrim)

        outExposure = afwImage.ExposureF(ccd.getAllPixels(self.config.doTrim))
        outMI = outExposure.getMaskedImage()
        outImageDict = dict(
            getImage = outMI.getImage(),
            getMask = outMI.getMask(),
            getVariance = outMI.getVariance(),
        )
        for ampExp in ampExposureList:
            amp = cameraGeom.cast_Amp(ampExp.getDetector())
            outBBox = amp.getAllPixels(self.config.doTrim)
            if self.config.doTrim:
                inBBox = amp.getDiskDataSec()
            else:
                inBBox = amp.getDiskAllPixels()

            for getterName in ("getImage", "getMask", "getVariance"):
                outImage = outImageDict[getterName]
                outView = outImage.Factory(outImage, outBBox, afwImage.LOCAL)

                inMI = ampExp.getMaskedImage()
                inImage = getattr(inMI, getterName)()
                inView = inImage.Factory(inImage, inBBox, afwImage.PARENT)
                outView <<= amp.prepareAmpData(inView)

        outExposure.setDetector(ccd)
        return outExposure
