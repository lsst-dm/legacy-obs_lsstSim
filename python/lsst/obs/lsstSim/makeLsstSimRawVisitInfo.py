#
# LSST Data Management System
# Copyright 2016 LSST Corporation.
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
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import astropy.units

from lsst.afw.image import VisitInfo, RotType
from lsst.afw.geom import degrees, SpherePoint
from lsst.afw.coord import Observatory, Weather
from lsst.afw.coord.refraction import defaultWeather
from lsst.obs.base import MakeRawVisitInfo

__all__ = ["MakeLsstSimRawVisitInfo"]


class MakeLsstSimRawVisitInfo(MakeRawVisitInfo):
    """Make a VisitInfo from the FITS header of a raw LSST simulated image

    The convention for ROTANG is as follows:
    at  0 degrees E = +Y CCD = -X Focal Plane, N = +X CCD = +Y Focal Plane:   0 boresightRotAng
    at 90 degrees E = -X CCD = -Y Focal Plane, N = +Y CCD = -X Focal Plane: 270 boresightRotAng

    So boresightRotAng = -ROTANG
    """
    observatory = Observatory(-70.749417*degrees, -30.244633*degrees, 2663)  # long, lat, elev

    def setArgDict(self, md, argDict):
        """Set an argument dict for VisitInfo and pop associated metadata

        @param[in,out] md  metadata, as an lsst.daf.base.PropertyList or PropertySet
        @param[in,out] argdict  a dict of arguments
        """
        MakeRawVisitInfo.setArgDict(self, md, argDict)
        argDict["darkTime"] = self.popFloat(md, "DARKTIME")
        argDict["boresightAzAlt"] = SpherePoint(
            self.popAngle(md, "AZIMUTH"),
            self.altitudeFromZenithDistance(self.popAngle(md, "ZENITH")),
        )
        argDict["boresightRaDec"] = SpherePoint(
            self.popAngle(md, "RA_DEG"),
            self.popAngle(md, "DEC_DEG"),
        )
        argDict["boresightAirmass"] = self.popFloat(md, "AIRMASS")
        argDict["boresightRotAngle"] = -self.popAngle(md, "ROTANG")
        argDict["rotType"] = RotType.SKY
        argDict["observatory"] = self.observatory
        weather = defaultWeather(self.observatory.getElevation())
        temperature = self.defaultMetadata(self.popFloat(md, "TEMPERA"), weather.getAirTemperature(),
                                           minimum=-10, maximum=40.)
        pressure = self.defaultMetadata(self.pascalFromMmHg(self.popFloat(md, "PRESS")),
                                        weather.getAirPressure(), minimum=50000., maximum=90000.)
        humidity = 40.  # Not currently supplied by phosim, so set to a typical value.
        argDict["weather"] = Weather(temperature, pressure, humidity)
        longitude = argDict["observatory"].getLongitude()
        RA = argDict["boresightRaDec"][0]
        # phosim doesn't supply LST, HA, or UT1, and the alt/az/ra/dec/time can be inconsistent.
        # We will leave ERA as NaN until a better answer is available.
        try:
            # Other simulation tools don't have the same problem, and need hour angle if it is available.
            HA = self.popAngle(md, "HA", units=astropy.units.h)
            argDict['era'] = HA + RA - longitude
        except:
            self.log.warn("Hour angle missing from metadata, will be NAN")
        return VisitInfo(**argDict)

    def getDateAvg(self, md, exposureTime):
        """Return date at the middle of the exposure

        @param[in,out] md  FITS metadata; changed in place
        @param[in] exposureTime  exposure time in sec
        """
        startDate = self.popMjdDate(md, "TAI", timesys="TAI")
        return self.offsetDate(startDate, 0.5*exposureTime)
