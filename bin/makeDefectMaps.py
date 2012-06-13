import numpy
import time
import pyfits
import lsst.afw.image as ai
import lsst.afw.detection as afwDetection
import sys
rx = int(sys.argv[1])
ry = int(sys.argv[2])
sx = int(sys.argv[3])
sy = int(sys.argv[4])

mi = ai.MaskedImageF("QE_R%i%i_S%i%i.fits.gz"%(rx,ry,sx,sy))
im = mi.getImage()
arr = im.getArray()  
deadidx = numpy.where(arr == 0.)
hotidx = numpy.where(arr> 1.1)
arr[deadidx] = 2.
arr[hotidx] = 3.
im2 = ai.makeImageFromArray(arr)
thresh = afwDetection.Threshold(1.1)
fs = afwDetection.FootprintSet(im2, thresh)
x0 = []
y0 = [] 
width = []
height = []
for f in fs.getFootprints():
    for bbox in afwDetection.footprintToBBoxList(f):
        x0.append(bbox.getMinX())
        y0.append(bbox.getMinY())
        width.append(bbox.getWidth())
        height.append(bbox.getHeight())

head = pyfits.Header()
head.update('SERIAL',int('%i%i%i%i'%(rx,ry,sx,sy)),'Serial of the sensor')
head.update('NAME','R:%i,%i S:%i,%i'%(rx,ry,sx,sy),'Name of sensor for this defect map')
head.update('CDATE',time.asctime(time.gmtime()),'UTC of creation')

col1 = pyfits.Column(name='x0', format='I', array=numpy.array(x0))
col2 = pyfits.Column(name='y0', format='I', array=numpy.array(y0))
col3 = pyfits.Column(name='height', format='I', array=numpy.array(height))
col4 = pyfits.Column(name='width', format='I', array=numpy.array(width))
cols = pyfits.ColDefs([col1, col2, col3, col4])
tbhdu = pyfits.new_table(cols, header = head)
hdu = pyfits.PrimaryHDU()
thdulist = pyfits.HDUList([hdu, tbhdu])
thdulist.writeto("defects%i%i%i%i.fits"%(rx,ry,sx,sy))

