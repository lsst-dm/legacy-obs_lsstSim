from __future__ import print_function
from builtins import zip
#
# LSST Data Management System
# Copyright 2008, 2009, 2010, 2011, 2012, 2013 LSST Corporation.
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
import lsst.afw.cameraGeom as cameraGeom
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.afw.geom as afwGeom
import lsst.meas.algorithms as measAlg
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsst.ip.isr import IsrTask
from lsst.ip.isr import isr

import numpy

__all__ = ["ProcessCalibLsstSimTask"]


class ProcessCalibLsstSimConfig(IsrTask.ConfigClass):

    """Config for ProcessCcdLsstSim"""
    sigmaClip = pexConfig.Field(dtype=float, default=3., doc="Sigma level for sigma clipping")
    clipIter = pexConfig.Field(dtype=int, default=5, doc="Number of iterations for sigma clipping")
    type = pexConfig.ChoiceField(dtype=str, default='bias', doc="Type of master calibration to produce",
                                 allowed={'bias': "make master bias(zero)",
                                          'dark': "make master dark",
                                          'flat': "make master flat"})

    def __init__(self, *args, **kwargs):
        pexConfig.Config.__init__(self, *args, **kwargs)


class ProcessCalibLsstSimTask(IsrTask):
    ConfigClass = ProcessCalibLsstSimConfig

    def __init__(self, **kwargs):
        IsrTask.__init__(self, **kwargs)
        self.transposeForInterpolation = True  # temporary hack until LSST data is in proper order
        self.statsCtrl = afwMath.StatisticsControl()
        self.statsCtrl.setNumSigmaClip(self.config.sigmaClip)
        self.statsCtrl.setNumIter(self.config.clipIter)
        # Not sure how to do this.
        # self.statsCtrl.setAndMask('BAD')
        self.isr = isr

    @pipeBase.timeMethod
    def run(self, sensorRefList, calibType):
        """Process a calibration frame.

        @param sensorRef: sensor-level butler data reference
        @return pipe_base Struct containing these fields:
        - masterExpList: amp exposures of master calibration products
        """
        referenceAmps = sensorRefList[0].subItems(level="channel")
        masterExpList = []
        dataIdList = []
        expmeta = None
        for amp in referenceAmps:
            if amp.dataId['snap'] == 1:
                continue
            self.log.info("Amp: Processing %s", amp.dataId)
            print("dataid %s" % (amp.dataId))
            butler = amp.butlerSubset.butler
            ampMIList = []
            for sRef in sensorRefList:
                self.log.info("Sensor: Processing %s", sRef.dataId)
                ampSnapMIList = []
                dataId = eval(amp.dataId.__repr__())
                dataId['visit'] = sRef.dataId['visit']
                for snap in (0, 1):
                    dataId['snap'] = snap
                    ampExposure = sRef.butlerSubset.butler.get('raw', dataId)
                    if expmeta is None:
                        expmeta = ampExposure.getMetadata()
                        expfilter = ampExposure.getFilter()
                        expcalib = ampExposure.getCalib()
                    ampDetector = cameraGeom.cast_Amp(ampExposure.getDetector())

                    ampExposure = self.convertIntToFloat(ampExposure)
                    ampExpDataView = ampExposure.Factory(ampExposure, ampDetector.getDiskDataSec())

                    self.saturationDetection(ampExposure, ampDetector)

                    self.overscanCorrection(ampExposure, ampDetector)
                    if calibType in ('flat', 'dark'):
                        self.biasCorrection(ampExpDataView, amp)

                    if False:
                        self.darkCorrection(ampExpDataView, amp)

                    self.updateVariance(ampExpDataView, ampDetector)
                    ampSnapMIList.append(ampExpDataView.getMaskedImage())
                ampMIList.append(self.combineMIList(ampSnapMIList))
            masterFrame = self.combineMIList(ampMIList)
            # Fix saturation too???
            self.fixDefectsAndSat(masterFrame, ampDetector)
            exp = afwImage.ExposureF(masterFrame)
            self.copyMetadata(exp, expmeta, calibType)
            exp.setDetector(ampDetector)
            exp.setWcs(afwImage.Wcs())
            exp.setCalib(expcalib)
            if calibType is 'flat':
                exp.setFilter(expfilter)
            if self.config.doWrite and calibType is not 'flat':
                print("writing file %s" % dataId)
                butler.put(exp, calibType, dataId=amp.dataId)
            masterExpList.append(exp)
            dataIdList.append(amp.dataId)
        if self.config.doWrite and calibType is 'flat':
            self.normChipAmps(masterExpList)
            for exp, dataId in zip(masterExpList, dataIdList):
                print("writing flat file %s" % dataId)
                butler.put(exp, calibType, dataId)
        return pipeBase.Struct(
            masterFrameList=masterExpList,
        )

    def normChipAmps(self, exposureList):
        means = []
        for exp in exposureList:
            means.append(afwMath.makeStatistics(exp.getMaskedImage(),
                                                afwMath.MEANCLIP, self.statsCtrl).getValue())
        means = numpy.asarray(means)
        mean = means.mean()
        for exp in exposureList:
            mi = exp.getMaskedImage()
            mi /= mean

    def copyMetadata(self, exposure, metadata, calibType):
        outmetadata = exposure.getMetadata()
        cardsToCopy = ['CREATOR', 'VERSION', 'BRANCH', 'DATE', 'CCDID']
        for card in cardsToCopy:
            outmetadata.add(card, metadata.get(card))
        outmetadata.add('ID', outmetadata.get('CCDID'))

    def fixDefectsAndSat(self, masterFrame, detector):
        fwhm = self.config.fwhm
        dataBbox = detector.getDataSec(True)
        # Reversing the x and y is essentially a hack since we have to apply the defects in Amp coordinates
        # and they are recorded in chip coordinates
        # This should go away when the data from imSim is all in chip coordinates
        y = dataBbox.getMinX()
        x = dataBbox.getMinY()
        height = dataBbox.getDimensions()[0]
        # When at detector level, there will not be the need to go through the step of getting the parent
        defectList = cameraGeom.cast_Ccd(detector.getParent()).getDefects()
        dl = self.transposeDefectList(defectList, dataBbox)
        for d in dl:
            d.shift(-x, -y)
            if detector.getId() > 8:
                d.shift(0, height - 2*d.getBBox().getMinY()-d.getBBox().getHeight())
        # Should saturation be interpolated as well?
        # sdl = self.isr.getDefectListFromMask(masterFrame, 'SAT', growFootprints=0)
        # for d in sdl:
        #     dl.push_back(d)
        self.isr.maskPixelsFromDefectList(masterFrame, dl, maskName='BAD')
        self.isr.interpolateDefectList(masterFrame, dl, fwhm)
        return masterFrame

    def transposeDefectList(self, defectList, checkBbox=None):
        retDefectList = measAlg.DefectListT()
        for defect in defectList:
            bbox = defect.getBBox()
            nbbox = afwGeom.Box2I(afwGeom.Point2I(bbox.getMinY(), bbox.getMinX()),
                                  afwGeom.Extent2I(bbox.getDimensions()[1], bbox.getDimensions()[0]))
            if checkBbox:

                if checkBbox.overlaps(bbox):
                    retDefectList.push_back(measAlg.Defect(nbbox))
                else:
                    pass
            else:
                retDefectList.push_back(measAlg.Defect(nbbox))
        return retDefectList

    def combineMIList(self, miList, method='MEANCLIP'):
        combinedFrame = miList[0].Factory()
        try:
            if method is 'MEANCLIP':
                combinedFrame = afwMath.statisticsStack(miList, afwMath.MEANCLIP, self.statsCtrl)
            elif method is 'MEDIAN':
                combinedFrame = afwMath.statisticsStack(miList, afwMath.MEDIAN, self.statsCtrl)
            else:
                raise ValueError("Method %s is not supported for combining frames" % (method))
        except Exception as e:
            self.log.warn("Could not combine the frames. %s", e)

        return combinedFrame
