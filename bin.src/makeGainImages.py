#!/usr/bin/env python
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

from lsst.obs.lsstSim import LsstSimMapper
import lsst.afw.image as afwImage

def main():
    camera = LsstSimMapper().camera
    for filt_name in 'ugrizy':
        for ccd in camera:
            name = ccd.getName()
            # I'm not sure how to deal with the split chips yet.
            if 'A' in name or 'B' in name:
                continue
            print(name)
            CHIPID = "".join([c for c in name if c is not "," and c is not ":"])
            CHIPID = "_".join(CHIPID.split())
            image = afwImage.ImageF(ccd.getBBox())
            for amp in ccd:
                subim = afwImage.ImageF(image, amp.getBBox())
                subim[:] = amp.getGain()
                print(amp.getName(), amp.getGain())
            expInfo = afwImage.ExposureInfo()
            inFilter = afwImage.Filter(filt_name)
            expInfo.setFilter(inFilter)
            exp = afwImage.ExposureF(afwImage.MaskedImageF(image), expInfo)
            md = exp.getMetadata()
            md.set('CHIPID', CHIPID)
            # Set place holder date
            md.set('MJD-OBS', 53005.0)
            md.set('OBSTYPE', 'flat')
            # arbitrary for flats
            md.set('EXPTIME', 100)
            # need to be able to specify any filter
            md.set('CALDATE', 53005.0)
            exp.setMetadata(md)
            exp.writeFits("%(name)s_%(filter)s.fits"%({'name':CHIPID, 'filter':filt_name}))

if __name__ == "__main__":
    main()
