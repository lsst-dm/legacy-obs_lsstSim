#!/usr/bin/env python2
# 
# LSST Data Management System
# Copyright 2014 LSST Corporation.
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
from __future__ import absolute_import, division
import argparse
import re
import lsst.afw.geom as afwGeom
import lsst.afw.table as afwTable
from lsst.afw.cameraGeom import (DetectorConfig, CameraConfig, PUPIL, FOCAL_PLANE, PIXELS)
from lsst.obs.lsstSim import LsstSimMapper

def expandDetectorName(abbrevName):
    """Convert a detector name of the form Rxy_Sxy[_Ci] to canonical form: R:x,y S:x,y[,c]

    C0 -> A, C1 -> B
    """
    m = re.match(r"R(\d)(\d)_S(\d)(\d)(?:_C([0,1]))?", abbrevName)
    if m is None:
        raise RuntimeError("Cannot parse abbreviated name %r" % (abbrevName,))
    fullName = "R:%s,%s S:%s,%s" % tuple(m.groups()[0:4])
    subSensor = m.groups()[4]
    if subSensor is not None:
        fullName  = fullName + "," + {"0": "A", "1": "B"}[subSensor]
    return fullName

def makeAmpTables(segmentsFile):
    """
    Read the segments file from a PhoSim release and produce the appropriate AmpInfo
    @param segmentsFile -- String indicating where the file is located
    """
    returnDict = {}
    #TODO currently there is no linearity provided, but we should identify
    #how to get this information.
    linearityCoeffs = (0.,1.,0.,0.)
    linearityType = "Polynomial"
    ampCatalog = None
    with open(segmentsFile) as fh:
        for l in fh:
            if l.startswith("#"):
                continue

            els = l.rstrip().split()
            if len(els) == 4:
                if ampCatalog is not None:
                    returnDict[detectorName] = ampCatalog
                detectorName = expandDetectorName(els[0])
                numx = int(els[3])
                schema = afwTable.AmpInfoTable.makeMinimalSchema()
                ampCatalog = afwTable.AmpInfoCatalog(schema)
                continue
            record = ampCatalog.addNew()
            name = els[0].split("_")[-1]
            #Because of the camera coordinate system, we choose an
            #image coordinate system such that a transpose and reflection
            #about y is necessary to get the correct pixel positions from the
            #phosim segments file
            y0 = int(els[1])
            y1 = int(els[2])
            x0 = numx - 1 - int(els[4])
            x1 = numx - 1 - int(els[3])
            gain = float(els[7])
            readnoise = float(els[11])
            bbox = afwGeom.Box2I(afwGeom.Point2I(x0, y0), afwGeom.Point2I(x1, y1))

            if int(els[5]) == -1: 
                flipx = False 
            else: 
                flipx = True
            if int(els[6]) == -1: 
                flipy = False 
            else: 
                flipy = True
            ndatax = x1 - x0 + 1
            ndatay = y1 - y0 + 1
            prescan = int(els[15])
            hoverscan = int(els[16])
            extended = int(els[17])
            voverscan = int(els[18])
            rawBBox = afwGeom.Box2I(afwGeom.Point2I(0,0), afwGeom.Extent2I(extended+ndatax+hoverscan, prescan+ndatay+voverscan))
            rawDataBBox = afwGeom.Box2I(afwGeom.Point2I(extended, prescan), afwGeom.Extent2I(ndatax, ndatay))
            rawHorizontalOverscanBBox = afwGeom.Box2I(afwGeom.Point2I(extended+ndatax, prescan), afwGeom.Extent2I(hoverscan, ndatay))
            rawVerticalOverscanBBox = afwGeom.Box2I(afwGeom.Point2I(extended, prescan+ndatay), afwGeom.Extent2I(ndatax, voverscan))
            rawPrescanBBox = afwGeom.Box2I(afwGeom.Point2I(extended, 0), afwGeom.Extent2I(ndatax, prescan))

            #Set the elements of the record for this amp
            record.setBBox(bbox)
            record.setName(name)
            record.setGain(gain)
            record.setReadNoise(readnoise)
            record.setLinearityCoeffs(linearityCoeffs)
            record.setLinearityType(linearityType)
            record.setHasRawInfo(True)
            record.setRawFlipX(flipx)
            record.setRawFlipY(flipy)
            record.setRawBBox(rawBBox)
            record.setRawXYOffset(afwGeom.Extent2I(x0, y0))
            record.setRawDataBBox(rawDataBBox)
            record.setRawHorizontalOverscanBBox(rawHorizontalOverscanBBox)
            record.setRawVerticalOverscanBBox(rawVerticalOverscanBBox)
            record.setRawPrescanBBox(rawPrescanBBox)
    returnDict[detectorName] = ampCatalog
    return returnDict
   
def makeDetectorConfigs(detectorLayoutFile):
    """
    Create the detector configs to use in building the Camera
    @param detectorLayoutFile -- String describing where the focalplanelayout.txt file is located.
    """
    detectorConfigs = []
    detTypeMap = {"Group2":2, "Group1":3, "Group0":0}
    #We know we need to rotate 3 times and also apply the yaw perturbation
    nQuarter = 3
    with open(detectorLayoutFile) as fh:
        for l in fh:
            if l.startswith("#"):
                continue
            detConfig = DetectorConfig()
            els = l.rstrip().split()
            detConfig.name = els[0]
            detConfig.bbox_x0 = 0
            detConfig.bbox_y0 = 0
            detConfig.bbox_x1 = int(els[5]) - 1
            detConfig.bbox_y1 = int(els[4]) - 1
            detConfig.detectorType = detTypeMap[els[8]]
            #TODO same as name right now.
            detConfig.serial = els[0]
            detConfig.offset_x = float(els[1]) + float(els[12])
            detConfig.offset_y = float(els[2]) + float(els[13])
            detConfig.refpos_x = (int(els[5]) - 1.)/2.
            detConfig.refpos_y = (int(els[4]) - 1.)/2.
            #TODO we need to translate between John's angles an Orienation angles.
            #It's not a deal now because there is now rotation except about z in John's model.
            detConfig.yawDeg = 90.*nQuarter + float(els[9])
            detConfig.pitchDeg = float(els[10])
            detConfig.rollDeg = float(els[11])
            detConfig.pixelSize_x = float(els[3])
            detConfig.pixelSize_y = float(els[3])
            detConfig.transposeDetector = False
            detConfig.transformDict.nativeSys = PIXELS.getSysName()
            #Here is where other transforms would be inserted.  The pixel to focalplane transform
            #is generated by the Orientation class in the Camera maker.
            detectorConfigs.append(detConfig)
    return detectorConfigs

if __name__ == "__main__":
    """
    Create the configs for building a camera.  This runs on the files distributed with PhoSim.
    For example:
    DetectorLayoutFile -- https://dev.lsstcorp.org/cgit/LSST/sims/phosim.git/plain/data/lsst/focalplanelayout.txt?h=dev
    SegmentsFile -- https://dev.lsstcorp.org/cgit/LSST/sims/phosim.git/plain/data/lsst/segmentation.txt?h=dev
    """
    import os
    import shutil
    import eups
    baseDir = eups.productDir("obs_lsstSim")
    defaultOutDir = os.path.join(os.path.normpath(baseDir), "description", "camera")

    parser = argparse.ArgumentParser()
    parser.add_argument("DetectorLayoutFile", help="Path to detector layout file")
    parser.add_argument("SegmentsFile", help="Path to amp segments file")
    parser.add_argument("OutputDir",
        help = "Path to dump configs and AmpInfo Tables; defaults to %r" % (defaultOutDir,),
        default = defaultOutDir,
    )
    parser.add_argument("--clobber", action="store_true", dest="clobber", default=False,
        help=("remove and re-create the output directory if it already exists?"))
    args = parser.parse_args()
    ampTableDict = makeAmpTables(args.SegmentsFile)
    detectorConfigList = makeDetectorConfigs(args.DetectorLayoutFile)

    #Build the camera config.
    camConfig = CameraConfig() 
    camConfig.detectorList = dict([(i,detectorConfigList[i]) for i in xrange(len(detectorConfigList))])
    camConfig.name = 'LSST'
    camConfig.plateScale = 20.0
    pScaleRad = afwGeom.arcsecToRad(camConfig.plateScale)
    pincushion = 0.925
    # Don't have this yet ticket/3155
    #camConfig.boresiteOffset_x = 0.
    #camConfig.boresiteOffset_y = 0.
    tConfig = afwGeom.TransformConfig()
    tConfig.transform.name = 'radial'
    # According to Dave M. the simulated LSST transform is well approximated (1/3 pix) 
    # by a scale and a pincusion.
    tConfig.transform.active.coeffs = [0., 1./pScaleRad, 0., pincushion/pScaleRad]
    #tConfig.transform.active.boresiteOffset_x = camConfig.boresiteOffset_x
    #tConfig.transform.active.boresiteOffset_y = camConfig.boresiteOffset_y
    tmc = afwGeom.TransformMapConfig()
    tmc.nativeSys = FOCAL_PLANE.getSysName()
    tmc.transforms = {PUPIL.getSysName():tConfig}
    camConfig.transformDict = tmc

    # create camera -- not something we normally do here
    # cameraTask = CameraFactoryTask(camConfig, ampTableDict)
    # camera = cameraTask.run()

    def makeDir(dirPath, doClobber=False):
        """Make a directory; if it exists then clobber or fail, depending on doClobber

        @param[in] dirPath: path of directory to create
        @param[in] doClobber: what to do if dirPath already exists:
            if True and dirPath is a dir, then delete it and recreate it, else raise an exception
        @throw RuntimeError if dirPath exists and doClobber False
        """
        if os.path.exists(dirPath):
            if doClobber and os.path.isdir(dirPath):
                print "Clobbering directory %r" % (dirPath,)
                shutil.rmtree(dirPath)
            else:
                raise RuntimeError("Directory %r exists" % (dirPath,))
        print "Creating directory %r" % (dirPath,)
        os.makedirs(dirPath)

    # write data products
    outDir = args.OutputDir
    makeDir(dirPath=outDir, doClobber=args.clobber)

    camConfigPath = os.path.join(outDir, "camera.py")
    camConfig.save(camConfigPath)

    for detectorName, ampTable in ampTableDict.iteritems():
        shortDetectorName = LsstSimMapper.getShortCcdName(detectorName)
        ampInfoPath = os.path.join(outDir, shortDetectorName + ".fits")
        ampTable.writeFits(ampInfoPath)
