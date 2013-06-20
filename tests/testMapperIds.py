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

import unittest
import lsst.utils.tests as utilsTests

import os
from lsst.daf.persistence import DbAuth
import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
from lsst.obs.lsstSim import LsstSimMapper

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
    return tuple(afwCoord.IcrsCoord(afwGeom.Point2D(d[0], d[1]), afwGeom.degrees) for d in degList)

class MapperIdsTestCase(unittest.TestCase):
    """A test case for ID handling by the mapper."""
    def testCcdExposureId(self):
        """Test mapping between data ID dict and CCD exposure ID
        """
        idSet = set() # to check for duplicates
        for visit in range(16):
            for r1 in range(4):
                for r2 in range(4):
                    if r1 == r2 == 4:
                        continue
                    if r1 == r2 == 0:
                        continue
        
                    for s1 in range(3):
                        for s2 in range(3):
                            dataId = dict(
                                visit = visit,
                                raft = "%d,%d" % (r1, r2),
                                sensor = "%d,%d" % (s1, s2),
                            )
                            ccdExposureId = LsstSimMapper._computeCcdExposureId(dataId)
                            self.assertFalse(ccdExposureId in idSet)
                            idSet.add(ccdExposureId)
                            reconDataId = LsstSimMapper.getDataIdFromCcdExposureId(ccdExposureId)
                            self.assertEqual(tuple(sorted(reconDataId.keys())), ("raft", "sensor", "visit"))
                            for key in ("raft", "sensor", "visit"):
                                self.assertEqual(reconDataId[key], dataId[key])


def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(MapperIdsTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(shouldExit=False):
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
