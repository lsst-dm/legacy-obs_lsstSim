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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#

"""Test lsst.obs.lsstSim.ScaleLsstSimZeroPointTask
"""
import numpy
import unittest

import lsst.daf.base
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.utils.tests as utilsTests
import lsst.pex.exceptions as pexExcept
import lsst.pex.logging as pexLog
import lsst.coadd.utils as coaddUtils

from lsst.daf.persistence import DbAuth
from lsst.obs.lsstSim.scaleLsstSimZeroPoint import ScaleLsstSimZeroPointTask

    
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class ScaleLsstSimZeroPointTaskTestCase(unittest.TestCase):
    """A test case for ScaleLsstSimZeroPointTask
    """
    def setUp(self):
        #Create an LsstSim Wcs
        self.metadata = lsst.daf.base.PropertySet()
        self.metadata.set("NAXIS", 2)
        self.metadata.set("RADECSYS", "ICRS")
        self.metadata.set("EQUINOX", 2000.)
        self.metadata.setDouble("CRVAL1", 60.000000000000)
        self.metadata.setDouble("CRVAL2", 10.812316963572)
        self.metadata.setDouble("CRPIX1", 700000.00000000)
        self.metadata.setDouble("CRPIX2", 601345.00000000)
        self.metadata.set("CTYPE1", "RA---STG")
        self.metadata.set("CTYPE2", "DEC--STG")
        self.metadata.setDouble("CD1_1", -5.5555555555556e-05)
        self.metadata.setDouble("CD1_2", 0.0000000000000)
        self.metadata.setDouble("CD2_2", 5.5555555555556e-05)
        self.metadata.setDouble("CD2_1", 0.0000000000000)
        self.metadata.set("CUNIT1", "deg")
        self.metadata.set("CUNIT2", "deg")
        
        self.sctrl = afwMath.StatisticsControl()
        self.sctrl.setNanSafe(True)

                
    def tearDown(self):
        del self.metadata
    
    def testBasics(self):
        ZEROPOINT = 27
        config = ScaleLsstSimZeroPointTask.ConfigClass()
        config.zeroPoint = ZEROPOINT
        config.interpStyle = "CONSTANT"
        config.selectFluxMag0.database = "test_select_lsst_images"
        zpScaler = ScaleLsstSimZeroPointTask(config=config)
        outCalib = zpScaler.getCalib()
        self.assertAlmostEqual(outCalib.getMagnitude(1.0), ZEROPOINT)

        #exposure needs a wcs and a bbox
        wcs = afwImage.makeWcs(self.metadata)
        bbox = afwGeom.Box2I(afwGeom.Point2I(327750, 235750), afwGeom.Extent2I(10, 10))
        exposure = afwImage.ExposureF(bbox, wcs)
        mi = exposure.getMaskedImage()
        mi.set(1.0)
        mi.getVariance().set(1.0)

        exposureId = dataId= {'visit': 882820621, 'filter': 'r'}

        #test methods: computeImageScale(), scaleMaskedImage(), getInterpImage()
        imageScaler = zpScaler.computeImageScaler(exposure,exposureId)
        scaleFactorIm = imageScaler.getInterpImage(bbox)
        predScale = numpy.mean(imageScaler._scaleList) #0.011125492863357
        
        self.assertAlmostEqual(afwMath.makeStatistics(scaleFactorIm, afwMath.VARIANCE, self.sctrl).getValue(),
                               0.0)
        self.assertAlmostEqual(afwMath.makeStatistics(scaleFactorIm, afwMath.MEAN, self.sctrl).getValue(),
                               predScale)

        imageScaler.scaleMaskedImage(mi)
        self.assertAlmostEqual(mi.get(1,1)[0], predScale) #check image plane scaled
        self.assertAlmostEqual(mi.get(1,1)[2], predScale**2) #check variance plane scaled

        exposure.setCalib(zpScaler.getCalib())    
        self.assertAlmostEqual(exposure.getCalib().getFlux(ZEROPOINT), 1.0)

                                
    def makeCalib(self, zeroPoint):
        calib = afwImage.Calib()
        fluxMag0 = 10**(0.4 * zeroPoint)
        calib.setFluxMag0(fluxMag0, 1.0)
        return calib


def suite():
    """Return a suite containing all the test cases in this module.
    """
    utilsTests.init()

    suites = [
        unittest.makeSuite(ScaleLsstSimZeroPointTaskTestCase),
        unittest.makeSuite(utilsTests.MemoryTestCase),
    ]

    return unittest.TestSuite(suites)


def run(shouldExit=False):
    """Run the tests"""
    config =  ScaleLsstSimZeroPointTask.ConfigClass()
    try:
        user = DbAuth.username(config.selectFluxMag0.host, str(config.selectFluxMag0.port)),
    except Exception, e:
        print "Warning: did not find host=%s, port=%s in your db-auth file; or %s " \
              "skipping SelectLsstImagesTask unit tests" % \
            (config.selectFluxMag0.host, str(config.selectFluxMag0.port), e)
        return

    utilsTests.run(suite(), shouldExit)


if __name__ == "__main__":
    run(True)
