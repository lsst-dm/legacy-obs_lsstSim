#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
#
# LSST Data Management System
# Copyright 2008-2016 LSST Corporation.
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
"""Test ability to get an eimage from the butler.
**Note that this is an lsstSim specific test and
should not be considered generalizable.
"""
import os
import unittest

import numpy as np

import lsst.utils
import lsst.afw.geom as afwGeom
import lsst.utils.tests
import lsst.daf.persistence as dafPersistence
from lsst.afw.coord import Coord, IcrsCoord, Observatory, Weather
from lsst.daf.base import DateTime

obsLsstSimDir = lsst.utils.getPackageDir('obs_lsstSim')
InputDir = os.path.join(obsLsstSimDir, 'tests', 'data')


class GetEimageTestCase(lsst.utils.tests.TestCase):
    """Test the accessors for various bits of metadata attached to eimages.
    The exposure is read in setUpClass.  The different methods of VisitInfo
    are tested separately to simplify error reporting.
    """
    @classmethod
    def setUpClass(self):
        # For lsstSim specific reasons, we need to specify the raft and sensor
        dataId = dict(visit=840, raft='2,2', sensor='1,1')
        butler = dafPersistence.Butler(InputDir)
        self.exposure = butler.get('eimage', dataId=dataId)
        self.visit_info = self.exposure.getInfo().getVisitInfo()

    @classmethod
    def tearDownClass(self):
        del self.exposure
        del self.visit_info

    def test_getWcs(self):
        """Test whether the Exposure has a Wcs attached."""

        # Test for a Wcs object
        self.assertIsNotNone(self.exposure.getWcs())

    def test_getBoresightAirmass(self):
        self.assertEqual(1.00015190967402, self.visit_info.getBoresightAirmass())

    def test_getBoresightAzAlt(self):
        coord = Coord(afwGeom.Point2D(0.0, 89.0), afwGeom.degrees, 2000.0)
        self.assertEqual(coord, self.visit_info.getBoresightAzAlt())

    def test_getBoresightRaDec(self):
        coord = IcrsCoord(afwGeom.Point2D(53.0091385, -27.4389488), afwGeom.degrees)
        self.assertEqual(coord, self.visit_info.getBoresightRaDec())

    def test_getBoresightRotAngle(self):
        angle = afwGeom.Angle(-2.565348674005548, afwGeom.radians)
        self.assertAnglesNearlyEqual(angle, self.visit_info.getBoresightRotAngle())

    def test_getDarkTime(self):
        self.assertEqual(30.0, self.visit_info.getDarkTime())

    def test_getDate(self):
        date = DateTime("1994-01-02T01:46:59.520000913", DateTime.TAI)
        self.assertEqual(date, self.visit_info.getDate())

    def test_getEra(self):
        # numpy.isnan fails on afw:Angle, so just get a number out and test that.
        self.assertTrue(np.isnan(self.visit_info.getEra().asRadians()))

    def test_getExposureId(self):
        self.assertEqual(430204, self.visit_info.getExposureId())

    def test_getExposureTime(self):
        self.assertEqual(30.0, self.visit_info.getExposureTime())

    def test_getObservatory(self):
        observatory = Observatory(afwGeom.Angle(-70.749417, afwGeom.degrees),
                                  afwGeom.Angle(-30.244633, afwGeom.degrees), 2663)
        self.assertEqual(observatory, self.visit_info.getObservatory())

    def test_getRotType(self):
        self.assertEqual(1, self.visit_info.getRotType())

    def test_getWeather(self):
        def test_weather(w1, w2):
            """Test equality of two Weather objects
            @param[in] w1  First Weather object
            @param[in] w2  Second Weather object
            """
            humid_bool = np.isnan(w1.getHumidity()) and np.isnan(w2.getHumidity())
            if not humid_bool:
                humid_bool = (w1.getHumidity() == w2.getHumidity())
            self.assertTrue(w1.getAirPressure() == w2.getAirPressure() and w1.getAirTemperature() ==
                            w2.getAirTemperature() and humid_bool)

        weather = Weather(20, 69327.64145580001, np.nan)
        test_weather(weather, self.visit_info.getWeather())


def setup_module(module):
    lsst.utils.tests.init()


class MemoryTestCase(lsst.utils.tests.MemoryTestCase):
    pass

if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
