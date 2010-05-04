#!/usr/bin/env python

import unittest
import lsst.utils.tests as utilsTests

import lsst.daf.persistence as dafPersist
from lsst.obs.lsstSim import LsstSimMapper

class GetRawTestCase(unittest.TestCase):
    """Testing butler raw image retrieval"""

    def setUp(self):
        self.bf = dafPersist.ButlerFactory(
                mapper=LsstSimMapper(root="./tests/data"))
        self.butler = self.bf.create()

    def tearDown(self):
        del self.butler
        del self.bf

    def testRaw(self):
        """Test retrieval of raw image"""
        raw = self.butler.get("raw", visit=85471048, snap=0, raft='0,3',
                sensor='0,1', channel='1,0')
        self.assertEqual(raw.getWidth(), 513)
        self.assertEqual(raw.getHeight(), 2001)
        self.assertEqual(raw.getFilter().getFilterProperty().getName(), "y")
        self.assertEqual(raw.getDetector().getId().getName(), "ID8")
        self.assertEqual(raw.getDetector().getParent().getId().getName(),
                "R:0,3 S:0,1")

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def suite():
    """Returns a suite containing all the test cases in this module."""

    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(GetRawTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    """Run the tests"""
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
