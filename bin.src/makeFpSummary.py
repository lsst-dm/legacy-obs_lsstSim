#!/usr/bin/env python
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsst.pipe.drivers.utils import ButlerTaskRunner
from lsst.obs.lsstSim import SimButlerImage
from lsst.afw.cameraGeom import utils as cgu
from lsst.afw.display.rgb import ZScaleMapping, writeRGB
import lsst.afw.image as afwImage
import lsst.afw.geom as afwGeom

class FocalplaneSummaryConfig(pexConfig.Config):
    binSize = pexConfig.Field(dtype=int, default=50, doc="pixels to bin for the focalplane summary")
    contrast = pexConfig.Field(dtype=float, default=1, doc="contrast factor")
    sensorBinSize = pexConfig.Field(dtype=int, default=4, doc="pixels to bin per sensor")


class FocalplaneSummaryTask(pipeBase.CmdLineTask):
    ConfigClass = FocalplaneSummaryConfig
    _DefaultName = "focalplaneSummary"
    RunnerClass = ButlerTaskRunner

    def __init__(self, *args, **kwargs):
        pipeBase.CmdLineTask.__init__(self, *args, **kwargs)

    def run(self, expRef, butler):
        """Make summary plots of full focalplane images.
        """
        sbi = SimButlerImage(butler, type='eimage', visit=expRef.dataId['visit'])
        # Get the per ccd images
        def parse_name_to_dataId(name_str):
            raft, sensor = name_str.split()
            return {'raft':raft[-3:], 'sensor':sensor[-3:]}
        for ccd in butler.get('camera'):
            data_id = parse_name_to_dataId(ccd.getName())
            data_id.update(expRef.dataId)
            binned_im = sbi.getCcdImage(ccd, binSize=self.config.sensorBinSize, as_masked_image=True)[0]
            try:
                butler.put(binned_im, 'binned_sensor_fits', **data_id)
            except RuntimeError:
                # butler couldn't put the image
                continue
            butler.put(binned_im, 'binned_sensor_fits', **data_id)
            (x, y) = binned_im.getDimensions()
            boxes = {'A':afwGeom.Box2I(afwGeom.PointI(0,y/2), afwGeom.ExtentI(x, y/2)),
                     'B':afwGeom.Box2I(afwGeom.PointI(0,0), afwGeom.ExtentI(x, y/2))}
            for half in ('A', 'B'):
                box = boxes[half]
                butler.put(afwImage.MaskedImageF(binned_im, box), 'binned_sensor_fits_halves', half=half,
                           **data_id)

        im = cgu.showCamera(butler.get('camera'), imageSource=sbi, binSize=self.config.binSize)
        butler.put(im, 'focalplane_summary_fits')
        zmap = ZScaleMapping(im, contrast=self.config.contrast)
        rgb = zmap.makeRgbImage(im, im, im)
        file_name = expRef.get('focalplane_summary_png_filename')
        writeRGB(file_name[0], rgb)

    @classmethod
    def _makeArgumentParser(cls, *args, **kwargs):
        # Pop doBatch keyword before passing it along to the argument parser
        kwargs.pop("doBatch", False)
        parser = pipeBase.ArgumentParser(name="focalplaneSummary",
                                         *args, **kwargs)
        parser.add_id_argument("--id", datasetType="eimage", level="visit",
                               help="data ID, e.g. --id visit=12345")
        return parser

    def _getConfigName(self):
        return None

    def _getMetadataName(self):
        return None

if __name__ == "__main__":
    FocalplaneSummaryTask.parseAndRun()