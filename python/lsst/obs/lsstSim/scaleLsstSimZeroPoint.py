#!/usr/bin/env python
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#
import MySQLdb
import numpy

import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.pex.config as pexConfig
import lsst.afw.geom as afwGeom
import lsst.pipe.base as pipeBase
from lsst.coadd.utils import  ScaleZeroPointTask
from .selectFluxMag0 import SelectLsstSimFluxMag0Task


__all__ = ["ScaleLsstSimZeroPointTask"]

class LsstSimImageScaler(object):
    """Multiplicative image scaler using interpolation over a grid of points.
    
    Contains the x, y positions in tract coordinates and the scale factors.
    Interpolates only when scaleMaskedImage() or getInterpImage() is called.
       
    Currently the only type of 'interpolation' implemented is CONSTANT which calculates the mean.
    """
    
    def __init__(self, interpStyle, xList, yList, scaleList):
        """Construct an LsstSimImageScaler
               
        @param[in] interpStyle: interpolation style (CONSTANT is only option)
        @param[in] xList: list of X pixel positions
        @param[in] yList: list of Y pixel positions
        @param[in] scaleList: list of multiplicative scale factors at (x,y)

        @raise RuntimeError if the lists have different lengths
        """
        if len(xList) != len(yList) or len(xList) != len(scaleList):
            raise RuntimeError(
                "len(xList)=%s len(yList)=%s, len(scaleList)=%s but all lists must have the same length" % \
                (len(xList), len(yList), len(scaleList)))

        #Eventually want this do be: self.interpStyle = getattr(afwMath.Interpolate2D, interpStyle)
        self.interpStyle = getattr(afwMath.Interpolate, interpStyle)
        self._xList = xList
        self._yList = yList
        self._scaleList = scaleList


    def scaleMaskedImage(self, maskedImage):
        """Apply scale correction to the specified masked image
        
        @param[in,out] image to scale; scale is applied in place
        """
        scale = self.getInterpImage(maskedImage.getBBox(afwImage.PARENT))
        maskedImage *= scale

    def getInterpImage(self, bbox):
        """Return an image containing the scale correction with same bounding box as supplied.
        
        @param[in] bbox: integer bounding box for image (afwGeom.Box2I)
        """
        npoints = len(self._xList)

        if npoints < 1:
            raise RuntimeError("Cannot create scaling image. Found no fluxMag0s to interpolate")

        image = afwImage.ImageF(bbox, numpy.mean(self._scaleList))

        return image


class ScaleLsstSimZeroPointConfig(ScaleZeroPointTask.ConfigClass):
    """Config for ScaleLsstSimZeroPointTask
    """
    selectFluxMag0 = pexConfig.ConfigurableField(
        doc = "Task to select data to compute spatially varying photometric zeropoint",
        target = SelectLsstSimFluxMag0Task,
    )
    
    interpStyle = pexConfig.ChoiceField(
        dtype = str,
        doc = "Algorithm to interpolate the flux scalings;" \
              "Currently only one choice implemented",
        default = "CONSTANT",
        allowed={
             "CONSTANT" : "Use a single constant value",
             }
    )
    

class ScaleLsstSimZeroPointTask(ScaleZeroPointTask):
    """Selects fluxmag0's and constructs an appropriate LsstSimImageScaler
    
    """
    ConfigClass = ScaleLsstSimZeroPointConfig
    _DefaultName = "scaleLsstSimZeroPoint"
    
    def __init__(self, *args, **kwargs):
        """Construct a ScalelsstSimZeroPointTask
        """
        pipeBase.Task.__init__(self, *args, **kwargs)
        self.makeSubtask("selectFluxMag0")

        #m1 = -2.5*log10(F1/F0)
        #flux at mag=0 is 10^(zeroPoint/2.5)
        fluxMag0 = 10**(0.4 * self.config.zeroPoint)
        self._calib = afwImage.Calib()
        self._calib.setFluxMag0(fluxMag0)

    def computeImageScaler(self, exposure, exposureId):
        """Query a database for all fluxMag0s in a single visit and return a LsstSimImageScaler
        
        @param[in] exposure: exposure for which we want an image scaler
        @param[in] exposureId: data ID of exposure (or a dict containing 'visit' e.g. {'visit': 882820621})

        """
        wcs = exposure.getWcs()
        bbox = exposure.getBBox(afwImage.PARENT)
        runArgDict = self.selectFluxMag0.runArgDictFromDataId(exposureId)
        
        fluxMagInfoList = self.selectFluxMag0.run(**runArgDict).fluxMagInfoList

        xList = []
        yList = []
        scaleList = []

        for fluxMagInfo in fluxMagInfoList:
            # find center of field in tract coordinates
            if not fluxMagInfo.coordList:
                raise RuntimeError("no x,y data for fluxMagInfo")
            ctr = afwGeom.Extent2D()
            for coord in fluxMagInfo.coordList:
                ctr += afwGeom.Extent2D(wcs.skyToPixel(coord))
                
            ctr = afwGeom.Point2D(ctr / len(fluxMagInfo.coordList))
            xList.append(ctr.getX())
            yList.append(ctr.getY())          
            scaleList.append(self.scaleFromFluxMag0(fluxMagInfo.fluxMag0).scale)
        
      
        self.log.info("Found %d flux scales for interpolation: %s"% (len(scaleList),
                                                                     ["%0.4f"%(s) for s in scaleList]))
        return LsstSimImageScaler(
            interpStyle = self.config.interpStyle,
            xList = xList,
            yList = yList,
            scaleList = scaleList,
        )



