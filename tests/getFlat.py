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

class GetFlatTestCase(unittest.TestCase):
    """Testing butler flat image retrieval"""

    def setUp(self):
        self.butler = dafPersist.Butler(root=os.path.join(os.path.dirname(__file__), "data"))

    def tearDown(self):
        del self.butler

    def testFlat(self):
        """Test retrieval of flat image"""
        # Note: no filter!
        raw = self.butler.get("flat", visit=85471048, snap=0, raft='0,3',
                sensor='0,1', channel='1,0', immediate=True)
        self.assertEqual(raw.getWidth(), 513)
        self.assertEqual(raw.getHeight(), 2001)
        self.assertEqual(raw.getFilter().getName(), "y")
        self.assertEqual(raw.getDetector().getName(), "R:0,3 S:0,1")
        self.assertEqual(raw.getDetector()['1,0'].getName(), '1,0')
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def suite():
    """Returns a suite containing all the test cases in this module."""

    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(GetFlatTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    """Run the tests"""
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
