from lsst.afw.cameraGeom.utils import ButlerImage, calcRawCcdBBox
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
from lsst.afw.math import rotateImageBy90
from lsst.daf.persistence.butlerExceptions import NoResults


class SimButlerImage(ButlerImage):

    def getCcdImage(self, ccd, imageFactory=afwImage.ImageF, binSize=1):
        """Return an image of the specified ccd, and also the (possibly updated) ccd"""

        if self.isTrimmed:
            bbox = ccd.getBBox()
        else:
            bbox = calcRawCcdBBox(ccd)

        def parse_name_to_dataId(name_str):
            raft, sensor = name_str.split()
            return {'raft':raft[-3:], 'sensor':sensor[-3:]}

        im = None
        if self.butler is not None:
            im = None
            cid = ccd.getName()
            did = parse_name_to_dataId(cid)
            # TODO override the constructor to handle this as state
            sensor_bin_size = self.kwargs.pop('sensorBinSize')
            self.kwargs.update(did)
            try:
                im = self.butler.get(self.type, **self.kwargs)
                ccd = im.getDetector()  # possibly modified by assembleCcdTask
                im.setMaskedImage(rotateImageBy90(im.getMaskedImage(), 2))
                binned_im = afwMath.binImage(im.getMaskedImage(), sensor_bin_size)
                self.butler.put(binned_im, 'binned_sensor_fits', **self.kwargs)
            except (NoResults, RuntimeError):
                pass
            self.kwargs['sensorBinSize'] = sensor_bin_size


        if im is None:
            return self._prepareImage(ccd, imageFactory(*bbox.getDimensions()), binSize), ccd

        if self.type == "raw":
            raise ValueError("This class only handles ccd size images")

        return self._prepareImage(ccd, im.getMaskedImage().getImage(), binSize), ccd
