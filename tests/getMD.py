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

class GetRawMetadataTestCase(unittest.TestCase):
    """Testing butler raw image retrieval"""

    def setUp(self):
        self.butler = dafPersist.Butler(root=os.path.join(os.path.dirname(__file__), "data"))

    def tearDown(self):
        del self.butler

    def testRawMetadata(self):
        """Test retrieval of raw image metadata"""
        rawMd = self.butler.get("raw_md", visit=85471048, snap=0, raft='0,3',
                sensor='0,1', channel='1,0')
        self.assertAlmostEqual(rawMd.get("AIRMASS"), 1.3184949200550, places=11)
        self.assertEqual(rawMd.get("BITPIX"), 16)
        self.assertEqual(rawMd.get("CCDID"), "R03_S01_C10")

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def suite():
    """Returns a suite containing all the test cases in this module."""

    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(GetRawMetadataTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    """Run the tests"""
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
