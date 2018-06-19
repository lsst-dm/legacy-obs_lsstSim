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
import os.path
import sys
import unittest

import lsst.utils.tests
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
                                sensor='0,1', channel='1,0', immediate=True)
        self.assertAlmostEqual(rawMd.getScalar("AIRMASS"), 1.3184949200550, places=11)
        self.assertEqual(rawMd.getScalar("BITPIX"), 16)
        self.assertEqual(rawMd.getScalar("CCDID"), "R03_S01_C10")


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    setup_module(sys.modules[__name__])
    unittest.main()
