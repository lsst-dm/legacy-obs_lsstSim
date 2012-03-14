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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#
import numpy
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
import lsst.afw.image as afwImage
import lsst.meas.algorithms as measAlg
import lsst.afw.math as afwMath
import lsst.afw.cameraGeom as cameraGeom
import lsst.afw.geom as afwGeom

from lsst.ip.isr import IsrTask
from lsst.ip.isr import IsrTaskConfig

class ProcessCalibLsstSimConfig(pexConfig.Config):
    """Config for ProcessCcdLsstSim"""
    isr = pexConfig.ConfigField(dtype=IsrTask.ConfigClass, doc="Amp-level instrumental signature removal")
    sigmaClip = pexConfig.Field(dtype=float, default=3., doc="Sigma level for sigma clipping")
    clipIter = pexConfig.Field(dtype=int, default=5, doc="Number of iterations for sigma clipping")
    type = pexConfig.ChoiceField(dtype=str, default='bias', doc="Type of master calibration to produce", allowed={'bias':"make master bias(zero)", 'dark':"make master dark", 'flat':"make master flat"})

    def __init__(self, *args, **kwargs):
        pexConfig.Config.__init__(self, *args, **kwargs)

class ProcessCalibLsstSimTask(pipeBase.Task):
    """Process a CCD for LSSTSim
    
    @todo: this variant of ProcessCcdTask can be eliminated once IsrTask is unified.
    """
    ConfigClass = ProcessCalibLsstSimConfig

    def __init__(self, *args, **kwargs):
        pipeBase.Task.__init__(self, *args, **kwargs)
        self.methodListDict = { 'bias': ["doConversionForIsr", "doSaturationDetection", "doOverscanCorrection"],
                                'dark': ["doConversionForIsr", "doSaturationDetection", "doOverscanCorrection", "doBiasSubtraction"],
                                'flat': ["doConversionForIsr", "doSaturationDetection", "doOverscanCorrection", "doBiasSubtraction", "doDarkCorrection"]
                              }
        self.config.isr.methodList = self.methodListDict[self.config.type]
        self.config.isr.normalizeGain = True
        self.makeSubtask('isr', IsrTask)
        self.statsCtrl = afwMath.StatisticsControl()
        self.statsCtrl.setNumSigmaClip(self.config.sigmaClip)
        self.statsCtrl.setNumIter(self.config.clipIter)
        #Not sure how to do this.
        #self.statsCtrl.setAndMask('BAD')

    @pipeBase.timeMethod
    def run(self, sensorRefList, calibType):
        """Process a CCD: including ISR, source detection, photometry and WCS determination
        
        @param sensorRef: sensor-level butler data reference
        @return pipe_base Struct containing these fields:
        - calibFrame: exposure after ISR performed if calib.doIsr, else None
        """
        referenceAmps = sensorRefList[0].subItems(level="channel")
        print referenceAmps.dataId
        masterExpList = []
        dataIdList = []
        expmeta = None
        self.isr.config.methodList = self.methodListDict[calibType]
        methodList = []
        for methodname in self.methodListDict[calibType]:
            methodList.append(getattr(self.isr, methodname))
        self.isr.methodList = methodList
        for amp in referenceAmps:
            if amp.dataId['snap'] == 1:
                continue
            self.log.log(self.log.INFO, "Amp: Processing %s" % (amp.dataId))
            butler = amp.butlerSubset.butler
            ampMIList = afwImage.vectorMaskedImageF()
            for sRef in sensorRefList:
                self.log.log(self.log.INFO, "Sensor: Processing %s" % (sRef.dataId))
                ampSnapMIList = afwImage.vectorMaskedImageF()
                calibSet = self.isr.makeCalibDict(butler, amp.dataId)
                dataId = eval(amp.dataId.__repr__())
                dataId['visit'] = sRef.dataId['visit']
                #for snap in amp.subItems(level="snap"):
                for snap in (0,1):
                    dataId['snap'] = snap
                    raw = sRef.butlerSubset.butler.get('raw', dataId)
                    if expmeta is None:
                        expmeta = raw.getMetadata()
                        expfilter = raw.getFilter()
                        expcalib = raw.getCalib()
                    detector = cameraGeom.cast_Amp(raw.getDetector())
                    #Following is a hack to deal with trimming the amps.
                    #raw = self.isr.doConversionForIsr(raw, calibSet)
                    #raw = self.isr.doSaturationDetection(raw, calibSet)
                    #raw = self.isr.doOverscanCorrection(raw, calibSet)
                    resexp = self.isr.run(raw, calibSet).postIsrExposure
                    #trimmedexp = resexp.Factory(resexp, detector.getDiskDataSec())
                    ampSnapMIList.append(resexp.getMaskedImage())
                ampMIList.append(self.combineMIList(ampSnapMIList))
            masterFrame = self.combineMIList(ampMIList) 
            #Fix saturation too???
            self.fixDefects(masterFrame, detector)
            exp = afwImage.ExposureF(masterFrame)
            self.copyMetadata(exp, expmeta, calibType)
            exp.setDetector(detector)
            exp.setWcs(afwImage.Wcs())
            exp.setCalib(expcalib)
            if calibType is 'flat':
                exp.setFilter(expfilter)
            if self.isr.config.doWrite and calibType is not 'flat':
                print "writing file %s"%dataId
                butler.put(exp, calibType, dataId = amp.dataId)
            masterExpList.append(exp)
            dataIdList.append(amp.dataId)
        if self.isr.config.doWrite and calibType is 'flat':
            self.normChipAmps(masterExpList)
            for exp, dataId in zip(masterExpList, dataIdList):
                print "writing flat file %s"%dataId
                butler.put(exp, calibType, dataId)
        return pipeBase.Struct(
            masterFrameList = masterExpList,
        )

    def normChipAmps(self, exposureList):
        means = []
        for exp in exposureList:
            means.append(afwMath.makeStatistics(exp.getMaskedImage(), afwMath.MEANCLIP, self.statsCtrl).getValue())
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

    def fixDefects(self, masterFrame, detector):
        fwhm = self.isr.config.fwhm
        dataBbox = detector.getDataSec(True)
        #Reversing the x and y is essentially a hack since we have to apply the defects in Amp coordinates and they are recorded in chip coordinates
        #This should go away when the data from imSim is all in chip coordinates
        y = dataBbox.getMinX()
        x = dataBbox.getMinY()
        width = dataBbox.getDimensions()[1]
        height = dataBbox.getDimensions()[0]
        #Should when at detector level, there will not be the need to go through the step of getting the parent
        defectList = cameraGeom.cast_Ccd(detector.getParent()).getDefects() 
        dl = self.transposeDefectList(defectList, dataBbox)
        for d in dl:
            d.shift(-x, -y)
            if detector.getId().getSerial()>8:
                d.shift(0, height - 2*d.getBBox().getMinY()-1)
        self.isr.isr.maskPixelsFromDefectList(masterFrame, dl, maskName='BAD')
        self.isr.isr.interpolateDefectList(masterFrame, dl, fwhm)
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
       try:
           if method is 'MEANCLIP':
               combinedFrame = afwMath.statisticsStack(
                   miList, afwMath.MEANCLIP, self.statsCtrl)
           elif method is 'MEDIAN':
               combinedFrame = afwMath.statisticsStack(
                   miList, afwMath.MEDIAN, self.statsCtrl)
           else:
               raise ValueError("Method %s is not supported for combining frames"%(method))
       except Exception, e:
           self.log.log(self.log.INFO, "Could not combine the frames. %s"%(e,))

       return combinedFrame
