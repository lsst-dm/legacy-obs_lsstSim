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
from __future__ import absolute_import, division, print_function
import sys
import unittest

import lsst.afw.geom as afwGeom
from lsst.daf.persistence import DbAuth
from lsst.obs.lsstSim.selectLsstImages import SelectLsstImagesTask
import lsst.utils.tests

# this database should be around for awhile, but in the long run
# I hope we can define a standard database that is saved essentially forever
Database = "test_select_lsst_images"


def getCoordList(minRa, minDec, maxRa, maxDec):
    degList = (
        (minRa, minDec),
        (maxRa, minDec),
        (maxRa, maxDec),
        (minRa, maxDec),
    )
    return tuple(afwGeom.SpherePoint(d[0], d[1], afwGeom.degrees) for d in degList)


class LsstMapperTestCase(unittest.TestCase):
    """A test case for SelectLsstImagesTask."""

    def setUp(self):
        """Initialize the DB connection.  Raise SkipTest if unable to access DB."""
        config = SelectLsstImagesTask.ConfigClass()
        try:
            DbAuth.username(config.host, str(config.port)),
        except RuntimeError as e:
            reason = "Warning: did not find host=%s, port=%s in your db-auth file; or %s " \
                     "skipping unit tests" % \
                     (config.host, str(config.port), e)
            raise unittest.SkipTest(reason)

    def testMaxFwhm(self):
        """Test config.maxFwhm
        """
        config = SelectLsstImagesTask.ConfigClass()
        config.database = Database
        for maxFwhm in (0.75, 0.80):
            config.maxFwhm = maxFwhm
            task = SelectLsstImagesTask(config=config)
            coordList = getCoordList(80.0, -7.9, 81.0, -6.5)
            filter = "r"
            expInfoList = task.run(coordList, filter).exposureInfoList
            self.assertEqual(tuple(expInfo for expInfo in expInfoList if expInfo.fwhm > maxFwhm), ())

    def testMaxExposures(self):
        """Test config.maxExposures
        """
        config = SelectLsstImagesTask.ConfigClass()
        config.database = Database
        for maxExposures in (0, 6):
            config.maxExposures = maxExposures
            task = SelectLsstImagesTask(config=config)
            coordList = getCoordList(80.0, -7.9, 81.0, -6.5)
            filter = "r"
            expInfoList = task.run(coordList, filter).exposureInfoList
            self.assertEqual(len(expInfoList), maxExposures)

    def testWholeSky(self):
        """Test whole-sky search
        """
        config = SelectLsstImagesTask.ConfigClass()
        config.database = Database
        for maxFwhm in (0.75, 0.80):
            config.maxFwhm = maxFwhm
            task = SelectLsstImagesTask(config=config)
            coordList = None
            filter = "r"
            expInfoList = task.run(coordList, filter).exposureInfoList
            self.assertEqual(tuple(expInfo for expInfo in expInfoList if expInfo.fwhm > maxFwhm), ())


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    setup_module(sys.modules[__name__])
    unittest.main()
