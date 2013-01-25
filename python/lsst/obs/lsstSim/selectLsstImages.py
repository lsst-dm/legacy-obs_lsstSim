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
"""Note: this code uses MySQLdb primarily because daf_persistence cannot call scisql.scisql_s2CPolyRegion
"""
import MySQLdb
from lsst.afw.coord import IcrsCoord
import lsst.afw.geom as afwGeom
from lsst.daf.persistence import DbAuth
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsst.pipe.tasks.selectImages import BaseSelectImagesTask, BaseExposureInfo

__all__ = ["SelectLsstImagesTask"]

class SelectLsstImagesConfig(BaseSelectImagesTask.ConfigClass):
    """Config for SelectLsstImagesTask
    """
    maxFwhm = pexConfig.Field(
        doc = "maximum FWHM (arcsec)",
        dtype = float,
        default = 2.0,
    )
    
    def setDefaults(self):
        BaseSelectImagesTask.ConfigClass.setDefaults(self)
        self.host = "lsst-db.ncsa.illinois.edu"
        self.port = 3306


class ExposureInfo(BaseExposureInfo):
    """Data about a selected exposure
    
    Data includes:
    - dataId: data ID of exposure (a dict)
    - coordList: a list of corner coordinates of the exposure (list of IcrsCoord)
    - fwhm: mean FWHM of exposure
    """
    def __init__(self, result):
        """Set exposure information based on a query result from a db connection
        """
        BaseExposureInfo.__init__(self)
        self.dataId = dict(
            raft = result[self._nextInd],
            visit = result[self._nextInd],
            sensor = result[self._nextInd],
            filter = result[self._nextInd]
        )
        self.coordList = []
        for i in range(4):
            self.coordList.append(
                IcrsCoord(
                    afwGeom.Angle(result[self._nextInd], afwGeom.degrees),
                    afwGeom.Angle(result[self._nextInd], afwGeom.degrees),
                )
            )
        self.fwhm = result[self._nextInd]

    @staticmethod
    def getColumnNames():
        """Get database columns to retrieve, in a format useful to the database interface
        
        @return database column names as string of comma-separated values
        """
        return "raftName, visit, ccdName, filterName, " + \
            "corner1Ra, corner1Decl, corner2Ra, corner2Decl, " + \
            "corner3Ra, corner3Decl, corner4Ra, corner4Decl, " + \
            "fwhm"


class SelectLsstImagesTask(BaseSelectImagesTask):
    """Select LSST CCD exposures suitable for coaddition
    """
    ConfigClass = SelectLsstImagesConfig
    _DefaultName = "selectImages"
    
    @pipeBase.timeMethod
    def run(self, coordList, filter):
        """Select LSST images suitable for coaddition in a particular region
        
        @param[in] coordList: list of coordinates defining region of interest; if None then select all images
        @param[in] filter: filter (e.g. "g", "r", "i"...)
        
        @return a pipeBase Struct containing:
        - exposureInfoList: a list of ExposureInfo objects, which have the following fields:
            - dataId: data ID of exposure (a dict)
            - coordList: a list of corner coordinates of the exposure (list of afwCoord.IcrsCoord)
            - fwhm: fwhm column
        """
        db = MySQLdb.connect(
            host = self.config.host,
            port = self.config.port,
            user = DbAuth.username(self.config.host, str(self.config.port)),
            passwd = DbAuth.password(self.config.host, str(self.config.port)),
            db = self.config.database,
        )
        cursor = db.cursor()

        if coordList is not None:
            # look for exposures that overlap the specified region

            # create table scisql.Region containing patch region
            coordStrList = ["%s, %s" % (c.getLongitude().asDegrees(),
                                        c.getLatitude().asDegrees()) for c in coordList]
            coordStr = ", ".join(coordStrList)
            coordCmd = "call scisql.scisql_s2CPolyRegion(scisql_s2CPolyToBin(%s), 10)" % (coordStr,)
            cursor.execute(coordCmd)
            cursor.nextset() # ignore one-line result of coordCmd
        
            # find exposures
            queryStr = ("""select %s
                from Science_Ccd_Exposure as ccdExp,
                    (select distinct scienceCcdExposureId
                    from Science_Ccd_Exposure_To_Htm10 as ccdHtm inner join scisql.Region
                    on (ccdHtm.htmId10 between scisql.Region.htmMin and scisql.Region.htmMax)) as idList
                where ccdExp.scienceCcdExposureId = idList.scienceCcdExposureId
                    and filterName = %%s
                    and fwhm < %%s
                """ % ExposureInfo.getColumnNames())
        else:
            # no region specified; look over the whole sky
            queryStr = ("""select %s
                from Science_Ccd_Exposure
                where filterName = %%s
                    and fwhm < %%s
                """ % ExposureInfo.getColumnNames())
        
        if self.config.maxExposures is not None:
            queryStr += " limit %s" % (self.config.maxExposures,)

        dataTuple = (filter, self.config.maxFwhm)

        self.log.info("queryStr=%r; dataTuple=%s" % (queryStr, dataTuple))

        cursor.execute(queryStr, dataTuple)
        exposureInfoList = [ExposureInfo(result) for result in cursor]

        return pipeBase.Struct(
            exposureInfoList = exposureInfoList,
        )

    def _runArgDictFromDataId(self, dataId):
        """Extract keyword arguments for run (other than coordList) from a data ID
        
        @return keyword arguments for run (other than coordList), as a dict
        """
        return dict(
            filter = dataId["filter"]
        )


if __name__ == "__main__":
    # example of use
    selectTask = SelectLsstImagesTask()
    minRa = afwGeom.Angle(1, afwGeom.degrees)
    maxRa = afwGeom.Angle(2, afwGeom.degrees)
    minDec = afwGeom.Angle(5, afwGeom.degrees)
    maxDec = afwGeom.Angle(6, afwGeom.degrees)
    coordList = [
        IcrsCoord(minRa, minDec),
        IcrsCoord(maxRa, minDec),
        IcrsCoord(maxRa, maxDec),
        IcrsCoord(minRa, maxDec),
    ]
    results = selectTask.run(coordList = coordList, filter = 'r')
    for ccdInfo in results.exposureInfoList:
        print "dataId=%s, fwhm=%s" % (ccdInfo.dataId, ccdInfo.fwhm)
