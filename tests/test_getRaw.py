#
# LSST Data Management System
# Copyright 2008-2017 LSST Corporation.
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
import math
import os.path
import sys
import unittest

from lsst.daf.base import DateTime
import lsst.daf.persistence as dafPersist
from lsst.obs.base import MakeRawVisitInfo
import lsst.utils.tests
from lsst.afw.image import RotType
from lsst.geom import degrees, SpherePoint


class GetRawTestCase(lsst.utils.tests.TestCase):
    """Testing butler raw image retrieval"""

    def setUp(self):
        self.butler = dafPersist.Butler(root=os.path.join(os.path.dirname(__file__), "data"))
        self.exposureTime = 15.0
        self.darkTime = 15.0
        dateObs = DateTime(49552.28496, DateTime.MJD, DateTime.TAI)
        self.dateAvg = DateTime(dateObs.nsecs(DateTime.TAI) + int(0.5e9*self.exposureTime), DateTime.TAI)
        self.boresightRaDec = SpherePoint(359.936019771151, -2.3356222648145, degrees)
        self.boresightAzAlt = SpherePoint(127.158246182602, 90 - 40.6736117075876, degrees)
        self.boresightAirmass = 1.31849492005496
        self.boresightRotAngle = -3.43228*degrees
        self.rotType = RotType.SKY
        self.obs_longitude = -70.749417*degrees
        self.obs_latitude = -30.244633*degrees
        self.obs_elevation = 2663.0
        self.weath_airTemperature = 5.0
        self.weath_airPressure = MakeRawVisitInfo.pascalFromMmHg(520.0)
        self.weath_humidity = 40.

    def tearDown(self):
        del self.butler

    def testRaw(self):
        """Test retrieval of raw image"""
        raw = self.butler.get("raw", visit=85471048, snap=0, raft='0,3', sensor='0,1', channel='1,0',
                              immediate=True)
        self.assertEqual(raw.getWidth(), 513)
        self.assertEqual(raw.getHeight(), 2001)
        self.assertEqual(raw.getFilter().getFilterProperty().getName(), "y")
        self.assertEqual(raw.getDetector().getName(), "R:0,3 S:0,1")
        origin = raw.getWcs().getSkyOrigin()
        self.assertAlmostEqual(
            origin.getLongitude().asDegrees(), 0.0058520, 6)
        self.assertAlmostEqual(
            origin.getLatitude().asDegrees(), -2.3052624, 6)
        visitInfo = raw.getInfo().getVisitInfo()
        self.assertAlmostEqual(visitInfo.getDate().get(), self.dateAvg.get())
        # Explicit test for NaN here, because phosim output may not have consistent alt/az/ra/dec/time
        self.assertTrue(math.isnan(visitInfo.getEra()))
        self.assertAlmostEqual(visitInfo.getExposureTime(), self.exposureTime)
        self.assertAlmostEqual(visitInfo.getDarkTime(), self.darkTime)
        self.assertSpherePointsAlmostEqual(visitInfo.getBoresightRaDec(), self.boresightRaDec)
        self.assertSpherePointsAlmostEqual(visitInfo.getBoresightAzAlt(), self.boresightAzAlt)
        self.assertAlmostEqual(visitInfo.getBoresightAirmass(), self.boresightAirmass)
        self.assertAnglesAlmostEqual(visitInfo.getBoresightRotAngle(), self.boresightRotAngle)
        self.assertEqual(visitInfo.getRotType(), self.rotType)
        observatory = visitInfo.getObservatory()
        self.assertAnglesAlmostEqual(observatory.getLongitude(), self.obs_longitude)
        self.assertAnglesAlmostEqual(observatory.getLatitude(), self.obs_latitude)
        self.assertAlmostEqual(observatory.getElevation(), self.obs_elevation)
        weather = visitInfo.getWeather()
        self.assertAlmostEqual(weather.getAirTemperature(), self.weath_airTemperature)
        self.assertAlmostEqual(weather.getAirPressure(), self.weath_airPressure)
        self.assertAlmostEqual(weather.getHumidity(), self.weath_humidity)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    setup_module(sys.modules[__name__])
    unittest.main()
