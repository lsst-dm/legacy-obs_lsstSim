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
import os

import numpy
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.pex.config as pexConfig
from lsst.afw.coord import IcrsCoord
import lsst.afw.geom as afwGeom
from lsst.daf.persistence import DbAuth
import lsst.pipe.base as pipeBase
from lsst.pipe.tasks.selectImages import SelectImagesConfig, BaseExposureInfo
from lsst.coadd.utils import ImageScaler, ScaleZeroPointTask
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
        @param[in] scaleList: list of multiplicative scales at (x,y)

        @raise RuntimeError if the lists have different lengths
        """
        if len(xList) != len(yList) or len(xList) != len(scaleList):
            raise RuntimeError(
                "len(xList)=%s len(yList)=%s, len(scaleList)=%s but all lists must have the same length" % \
                (len(xList), len(yList), len(scaleList)))

        #Eventually want this do be:
        # self.interpStyle = getattr(afwMath.Interpolate2D, interpStyle)
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
        """Return an image interpolated in R.A direction covering supplied bounding box
        
        @param[in] bbox: integer bounding box for image (afwGeom.Box2I)
        """
        npoints = len(self._xList)

        if npoints < 1:
            raise RuntimeError("Cannot create scaling image. Found no fluxMag0s to interpolate")

        image = afwImage.ImageF(bbox, numpy.mean(self._scaleList))
        import pdb; pdb.set_trace()
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
        """Construct a ScaleZeroPointTask
        """
        pipeBase.Task.__init__(self, *args, **kwargs)
        self.makeSubtask("selectFluxMag0")
        
        fluxMag0 = 10**(0.4 * self.config.zeroPoint)
        self._calib = afwImage.Calib()
        self._calib.setFluxMag0(fluxMag0)

    def computeImageScaler(self, exposure, exposureId):
        """Query a database for all fluxMag0s in a single visit and return a LsstSimImageScaler
        
        @param[in] exposure: exposure for which we want an image scaler
        @param[in] exposureId: data ID of exposure

        """
        wcs = exposure.getWcs()
        bbox = exposure.getBBox(afwImage.PARENT)
        runArgDict = self.selectFluxMag0._runArgDictFromDataId(exposureId)
        
        fluxMagInfoList = self.selectFluxMag0.run(**runArgDict).fluxMagInfoList

        xList = []
        yList = []
        scaleList = []

        for fluxMagInfo in fluxMagInfoList:
            #find center of field in tract coordinates
            x0, y0 = wcs.skyToPixel(fluxMagInfo.coordList[0].getRa(), fluxMagInfo.coordList[0].getDec())
            x1, y1 = wcs.skyToPixel(fluxMagInfo.coordList[1].getRa(), fluxMagInfo.coordList[1].getDec())
            x2, y2 = wcs.skyToPixel(fluxMagInfo.coordList[2].getRa(), fluxMagInfo.coordList[2].getDec())
            x3, y3 = wcs.skyToPixel(fluxMagInfo.coordList[3].getRa(), fluxMagInfo.coordList[3].getDec())
            x = (x0 + x1 + x2 + x3)/4. 
            y = (y0 + y1 + y2 + y3)/4. 

            xList.append(x)
            yList.append(y)          
            scaleList.append(self.scaleFromFluxMag0(fluxMagInfo.fluxMag0).scale)

        self.log.info("Found %d flux scales for interpolation: %s"% (len(scaleList),
                                                                     ["%0.4f"%(s) for s in scaleList]))
        return LsstSimImageScaler(
            interpStyle = self.config.interpStyle,
            xList = xList,
            yList = yList,
            scaleList = scaleList,
        )



