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

class GetIdTestCase(unittest.TestCase):
	"""Testing butler exposure id retrieval"""

	def setUp(self):
		self.bf = dafPersist.ButlerFactory(mapper=LsstSimMapper(root="./tests/data"))
		self.butler = self.bf.create()

	def tearDown(self):
		del self.butler
		del self.bf

	def testId(self):
		"""Test retrieval of exposure ids"""
		bits = self.butler.get("ampExposureId_bits")
                self.assertEqual(bits, 45)
		id = self.butler.get("ampExposureId", visit=85471048, snap=0, raft='0,3',
				sensor='0,1', channel='1,0')
                self.assertEqual(id, (85471048 << 13) + 480 + 16 + 8)

                dr = self.butler.dataRef("raw", visit=85471048, raft='2,1', sensor='1,2')
                bits = dr.get("ampExposureId_bits")
                id = dr.get("ampExposureId", snap=0, channel='1,4')
                self.assertEqual(bits, 45)
                self.assertEqual(id, (85471048 << 13) + 11*160 + 5*16 + 12)
                bits = dr.get("ccdExposureId_bits")
                id = dr.get("ccdExposureId")
                self.assertEqual(bits, 41)
                self.assertEqual(id, (85471048 << 9) + 11*10 + 5)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def suite():
	"""Returns a suite containing all the test cases in this module."""

	utilsTests.init()

	suites = []
	suites += unittest.makeSuite(GetIdTestCase)
	suites += unittest.makeSuite(utilsTests.MemoryTestCase)
	return unittest.TestSuite(suites)

def run(shouldExit = False):
	"""Run the tests"""
	utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
	run(True)
