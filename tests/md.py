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
import os.path
import unittest

import lsst.utils.tests as utilsTests
import lsst.daf.persistence as dafPersist

class MetadataTestCase(unittest.TestCase):
    """Testing butler metadata retrieval"""

    def setUp(self):
        self.butler = dafPersist.Butler(root=os.path.join(os.path.dirname(__file__), "data"))

    def tearDown(self):
        del self.butler

    def testTiles(self):
        """Test sky tiles"""
        tiles = self.butler.queryMetadata("raw", "skyTile")
        tiles.sort()
        self.assertEqual(tiles, [
            92247, 92248, 92249, 92250, 92251, 92252, 92258, 92259, 92260,
            92261, 92967, 92968, 92969, 92970, 92971, 92972, 92977, 92978,
            92979, 92980, 92981, 92982, 93686, 93687, 93688, 93689, 93690,
            93691, 93692, 93696, 93697, 93698, 93699, 93700, 93701, 93702,
            94406, 94407, 94408, 94409, 94410, 94411, 94412, 94413, 94416,
            94417, 94418, 94419, 94420, 94421, 94422, 95127, 95128, 95129,
            95130, 95131, 95132, 95133, 95137, 95138, 95139, 95140, 95141,
            95142, 95847, 95848, 95849, 95850, 95851, 95852, 95857, 95858,
            95859, 95860, 95861, 95862, 96568, 96569, 96570, 96578, 96579,
            96580, 96581])

    def testCcdsInTiles(self):
        """Test CCDs in sky tiles"""
        ccds = self.butler.queryMetadata("raw", ("visit", "raft", "sensor"), skyTile=92247)
        ccds.sort()
        self.assertEqual(ccds, [(85471048, '1,4', '1,2')])

        ccds = self.butler.queryMetadata("raw", ("visit", "raft", "sensor"), dataId={'skyTile': 92250})
        ccds.sort()
        self.assertEqual(ccds, [
            (85470982, '3,4', '0,1'), (85470982, '3,4', '0,2'),
            (85470982, '3,4', '1,0'), (85470982, '3,4', '1,1'),
            (85470982, '3,4', '1,2'), (85470982, '3,4', '2,0'),
            (85470982, '3,4', '2,1'), (85470982, '3,4', '2,2'),
            (85471048, '3,4', '0,1'), (85471048, '3,4', '0,2'),
            (85471048, '3,4', '1,1'), (85471048, '3,4', '1,2'),
            (85471048, '3,4', '2,0'), (85471048, '3,4', '2,1'),
            (85471048, '3,4', '2,2') ])

    def testVisits(self):
        """Test visits"""
        visits = self.butler.queryMetadata("raw", ("visit",), {})
        visits.sort()
        self.assertEqual(visits, [85470982, 85471048, 85656362, 85801502])

    def testFilter(self):
        """Test filters"""
        filter = self.butler.queryMetadata("raw", ("filter",), visit=85470982)
        self.assertEqual(filter, ['y'])


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def suite():
    """Returns a suite containing all the test cases in this module."""

    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(MetadataTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    """Run the tests"""
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
