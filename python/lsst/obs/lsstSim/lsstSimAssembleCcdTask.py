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

class LsstSimAssembleCcdConfig(pexConfig.Config):
    def setDefaults(self):
        pass

    def doCcdAssembly(self, exposureList):
        renorm = self.config.reNormAssembledCcd
        setgain = self.config.setGainAssembledCcd
        k2rm = self.config.keysToRemoveFromAssembledCcd
        assembler = CcdAssembler(exposureList, reNorm=renorm, setGain=setgain, keysToRemove=k2rm)
        return assembler.assembleCcd()


class LsstSimAssembleCcdTask(ipIsr.AssembleCcdTask):
    """Assemble a CCD
    """
    ConfigClass = LsstSimAssembleCcdConfig
    
    def run(self, ampExposureList):
        """Assemble a CCD by trimming non-data areas

        @param[in]      ampExposureList   list of amp exposures to assemble
        """
        llAmpExp = ampExposureList[0]
        llAmp = cameraGeom.cast_Amp(llAmpExp.getDetector())
        ccd = cameraGeom.cast_Ccd(llAmp.getParent())

        if ccd is None or not isinstance(ccd, cameraGeom.Ccd) or \
               llAmp is None or not isinstance(llAmp, cameraGeom.Amp):
            raise RuntimeError("Detector in exposure does not match calling pattern")
        
        # convert CCD for assembled exposure
        ccd.setTrimmed(True)
        
        outExposure = self.assemblePixels(
            ampExposureList = ampExposureList,
            ccd = ccd,
        )

        self.setExposureComponents(
            outExposure = outExposure,
            ampExposureList = ampExposureList,
            ccd = ccd,
            llAmp = llAmp,
        )

        if self.config.setGain:
            if ccdVariance.getArray().max() == 0:
                raise("Can't calculate the effective gain since the variance plane is set to zero")
            self.setGain(
                outExposure = outExposure,
                ccd = ccd,
            )

        self.display("assembledExposure", exposure = outExposure)
    
        return pipeBase.Struct(
            exposure = outExposure
        )
    
    def assemblePixels(self, ampExposureList, ccd):
        """Assemble CCD pixels

        @param[in]      ampExposureList   list of amp exposures to assemble
        @param[in]      ccd         device info for assembled exposure
        @return         outExposure assembled exposure (just the pixels data is set)
        """
        maskedImageList = [exp.getMaskedImage() for exp in ampExposureList]
        ccdImage = cameraGeomUtils.makeImageFromCcd(
            ccd = ccd,
            imageSource = GetCcdImageData([mi.getImage() for mi in maskedImageList]),
            imageFactory = inMaskedImage.getImage().Factory,
            bin = False,
        )
        ccdVariance = cameraGeomUtils.makeImageFromCcd(
            ccd = ccd,
            imageSource = GetCcdImageData([mi.getVariance() for mi in maskedImageList]),
            imageFactory = afwImage.ImageF,
            bin = False,
        )
        ccdMask = cameraGeomUtils.makeImageFromCcd(
            ccd = ccd,
            imageSource = GetCcdImageData([mi.getMask() for mi in maskedImageList]),
            imageFactory = afwImage.MaskU,
            bin = False,
        )
        mi = afwImage.makeMaskedImage(ccdImage, ccdMask, ccdVariance)
        return afwImage.makeExposure(mi)


class GetCcdImageData(cameraGeomUtils.GetCcdImage):
    def __init__(self, imageList, isTrimmed=True):
        self.ampDict = {}
        for image in imageList:
            ampId = e.getDetector().getId()
            self.ampDict[ampId] = image
        self.isRaw = True
        self.isTrimmed = isTrimmed

    def getImage(self, ccd, amp, expType=None, imageFactory=afwImage.ImageF):
        ampId = amp.getId()
        image = self.ampDict.get(ampId)
        if image is None:
            return None
        
        if self.isTrimmed:
            bbox = amp.getDiskDataSec()
        else:
            bbox = amp.getDiskAllPixels()
        subImage = imageFactory(image, bbox, afwImage.PARENT)
        return amp.prepareAmpData(subImage)
