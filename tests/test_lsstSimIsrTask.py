#
# LSST Data Management System
# Copyright 2015-2017 LSST Corporation.
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
import os
import sys
import unittest

import lsst.afw.math as afwMath
import lsst.daf.persistence as dafPersist
from lsst.obs.lsstSim import LsstSimIsrTask
import lsst.utils.tests


class LsstSimIsrTaskTestCase(unittest.TestCase):
    """A test case for LsstSimIsrTask
    """

    def setUp(self):
        self.butler = dafPersist.Butler(root=os.path.join(os.path.dirname(__file__), "data"))
        self.ampRef = self.butler.dataRef("raw", level=None,
                                          dataId=dict(visit=85471048, snap=0, raft='0,3',
                                                      sensor='0,1', channel='1,0'))

    def tearDown(self):
        del self.butler
        del self.ampRef

    def testRunDataRef(self):
        """Test LsstSimIsrTask on amp-sized images in tests/data/

        applyToSensorRef is not intended to take single amp-sized exposures, but will
        run if the doAssembleCcd config parameter is False.
        However, the exposure is not trimmed, and gain not reset.
        """
        config = LsstSimIsrTask.ConfigClass()
        config.doDark = False
        config.doFringe = False
        config.doAssembleCcd = False
        config.doSnapCombine = False
        lsstIsrTask = LsstSimIsrTask(config=config)
        exposure = lsstIsrTask.runDataRef(self.ampRef).exposure
        self.assertAlmostEqual(afwMath.makeStatistics(exposure.getMaskedImage(), afwMath.MEAN).getValue(),
                               2.855780, places=3)

    def testRun(self):
        """Test LsstSimIsrTask on amp-sized images in tests/data/

        Do not assembleCcd.
        """
        config = LsstSimIsrTask.ConfigClass()
        config.doDark = False
        config.doFringe = False
        config.doAssembleCcd = False
        config.doSnapCombine = False
        lsstIsrTask = LsstSimIsrTask(config=config)
        ampExp = self.ampRef.get('raw')
        camera = self.ampRef.get("camera")
        isrData = lsstIsrTask.readIsrData(self.ampRef, ampExp)
        postIsrExp = lsstIsrTask.run(ampExp, camera=camera, **isrData.getDict()).exposure
        self.assertAlmostEqual(ampExp.getMetadata().getScalar('GAIN'),
                               postIsrExp.getMetadata().getScalar('GAIN'))
        self.assertAlmostEqual(ampExp.getDimensions()[0], postIsrExp.getDimensions()[0])
        self.assertAlmostEqual(ampExp.getDimensions()[1], postIsrExp.getDimensions()[1])
        self.assertAlmostEqual(afwMath.makeStatistics(postIsrExp.getMaskedImage(), afwMath.MEAN).getValue(),
                               2.855780, places=3)


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    setup_module(sys.modules[__name__])
    unittest.main()
