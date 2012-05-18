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
"""Note: this code uses MySQLdb primarily because daf_persistence cannot call scisql.scisql_s2CPolyRegion
"""
import MySQLdb
from lsst.daf.persistence import DbAuth
import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
from lsst.pipe.tasks.selectImages import BaseSelectImagesTask, BaseExposureInfo

__all__ = ["SelectLSSTImagesTask"]

class SelectLSSTImagesConfig(BaseSelectImagesTask.ConfigClass):
    """Config for SelectLSSTImagesTask
    """
    flagMask = pexConfig.Field(
        doc = """LSST quality mask; set allowed bits:
0x01 PROCESSING_FAILED: The pipeline failed to process this CCD
0x02 BAD_PSF_ZEROPOINT: The PSF flux zero-point appears to be bad
0x04 BAD_PSF_SCATTER: The PSF flux for stars shows excess scatter""",
        dtype = int,
        default = 0,
    )
    maxFwhm = pexConfig.Field(
        doc = "maximum FWHM (arcsec)",
        dtype = float,
        default = 2.0,
    )
    
    def setDefaults(self):
        self.host = "lsst-db.ncsa.illinois.edu"
        self.port = 3306
        self.database = "adm_smm_S12_lsstsim_u_smm_2012_0514_173319"


class ExposureInfo(BaseExposureInfo):
    """Data about a selected exposure
    
    Data includes:
    - dataId: data ID of exposure
    - coordList: list of afwCoord.IcrsCoord of corners of exposure
    - 
    """
    def _setData(self, result):
        """Set exposure information based on a query result from a db connection
        
        Sets at least the following fields:
        - dataId: data ID of exposure (a dict)
        - coordList: a list of corner coordinates of the exposure (list of afwCoord.Coord)
        - fwhm: mean FWHM of exposure
        - flags: flags field from Science_Ccd_Exposure table
        """
        self.dataId = dict(
            raft = result[self._nextInd],
            visit = result[self._nextInd],
            sensor = result[self._nextInd],
            filter = result[self._nextInd]
        )
        self.coordList = []
        for i in range(4):
            self.coordList.append(
                afwCoord.IcrsCoord(
                    afwGeom.Angle(result[self._nextInd], afwGeom.degrees),
                    afwGeom.Angle(result[self._nextInd], afwGeom.degrees),
                )
            )
        self.fwhm = result[self._nextInd]
        self.flags = result[self._nextInd]

    @staticmethod
    def getColumnNames():
        """Set database query columns to be consistent with constructor
        """
        return "raftName, visit, ccdName, filterName, " + \
            "corner1Ra, corner1Decl, corner2Ra, corner2Decl, " + \
            "corner3Ra, corner3Decl, corner4Ra, corner4Decl, " + \
            "fwhm, flags"


class SelectLSSTImagesTask(pipeBase.Task):
    """Select LSST CCD exposures suitable for coaddition
    """
    ConfigClass = SelectLSSTImagesConfig
    _DefaultName = "selectImages"
    
    @pipeBase.timeMethod
    def run(self, coordList, filter):
        """Select LSST images suitable for coaddition in a particular region
        
        @param[in] coordList: list of coordinates defining region of interest; if None then select all images
        @param[in] filter: filter (e.g. "g", "r", "i"...)
        
        @return a pipeBase Struct containing:
        - ccdInfoList: a list of ExposureInfo objects, which have the following fields:
            - dataId: data ID dictionary
            - fwhm: fwhm column
            - flags: flags column
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
                    and not (flags & ~%%s)
                    and fwhm < %%s
                """ % ExposureInfo.getColumnNames())
        else:
            # no region specified; look over the whole sky
            queryStr = ("""select %s
                from Science_Ccd_Exposure
                where filterName = %%s
                    and not (flags & ~%%s)
                    and fwhm < %%s
                """ % ExposureInfo.getColumnNames())
        
        if self.config.maxExposures:
            queryStr += " limit %s" % (self.config.maxExposures,)

        cursor.execute(queryStr, (filter, self.config.flagMask, self.config.maxFwhm))
        ccdInfoList = [ExposureInfo(result) for result in cursor]

        return pipeBase.Struct(
            ccdInfoList = ccdInfoList,
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
    import lsst.afw.coord as afwCoord
    import lsst.afw.geom as afwGeom
    
    selectTask = SelectLSSTImagesTask()
    minRa = afwGeom.Angle(1, afwGeom.degrees)
    maxRa = afwGeom.Angle(2, afwGeom.degrees)
    minDec = afwGeom.Angle(5, afwGeom.degrees)
    maxDec = afwGeom.Angle(6, afwGeom.degrees)
    coordList = [
        afwCoord.Coord(minRa, minDec),
        afwCoord.Coord(maxRa, minDec),
        afwCoord.Coord(maxRa, maxDec),
        afwCoord.Coord(minRa, maxDec),
    ]
    results = selectTask.run(coordList = coordList, filter = 'r')
    for ccdInfo in results.ccdInfoList:
        print "dataId=%s, fwhm=%s, flags=%s" % (ccdInfo.dataId, ccdInfo.fwhm, ccdInfo.flags)
    
