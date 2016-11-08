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
import sys
import unittest

import lsst.daf.persistence as dafPersist
import lsst.utils.tests


class GetIdTestCase(unittest.TestCase):
    """Testing butler exposure id retrieval"""

    def setUp(self):
        self.butler = dafPersist.Butler(root=os.path.join(os.path.dirname(__file__), "data"))

    def tearDown(self):
        del self.butler

    def testId(self):
        """Test retrieval of exposure ids"""
        bits = self.butler.get("ampExposureId_bits", immediate=True)
        self.assertEqual(bits, 45)
        id = self.butler.get("ampExposureId", visit=85471048, snap=0, raft='0,3', sensor='0,1',
                             channel='1,0', immediate=True)
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
        dataId = dict(tract=1, patch='2,3', filter='z')
        bits = self.butler.get("deepCoaddId_bits", dataId, immediate=True)
        id = self.butler.get("deepCoaddId", dataId, immediate=True)
        self.assertEqual(bits, 37)
        self.assertEqual(id, ((((1 * 8192) + 2) * 8192) + 3)*8 + 4)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    setup_module(sys.modules[__name__])
    unittest.main()
