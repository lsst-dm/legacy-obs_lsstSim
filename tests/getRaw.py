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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#

import unittest
import lsst.utils.tests as utilsTests

from lsst.pex.policy import Policy
import lsst.daf.persistence as dafPersist
from lsst.obs.lsstSim import LsstSimMapper
import lsst.afw.coord as afwCoord
import lsst.daf.base as dafBase

class GetRawTestCase(unittest.TestCase):
	"""Testing butler raw image retrieval"""

	def setUp(self):
		self.bf = dafPersist.ButlerFactory(mapper=LsstSimMapper(root="./tests/data"))
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
		origin = raw.getWcs().getSkyOrigin()
		self.assertAlmostEqual(
				origin.getLongitude(afwCoord.DEGREES), 0.005865, 6)
		self.assertAlmostEqual(
				origin.getLatitude(afwCoord.DEGREES), -2.305262, 6)

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
