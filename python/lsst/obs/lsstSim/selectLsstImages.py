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

__all__ = ["SelectLSSTImagesTask"]

class SelectLSSTImagesConfig(pexConfig.Config):
    """Config for SelectLSSTImagesTask
    """
    host = pexConfig.Field(
        doc = "Database server host name",
        dtype = str,
        default = "lsst-db.ncsa.illinois.edu",
    )
    port = pexConfig.Field(
        doc = "Database server port",
        dtype = int,
        default = 3306,
    )
    database = pexConfig.Field(
        doc = "Name of database",
        dtype = str,
        default = "ktlim_PT1_2_u_ktlim_2012_0308_110900",
    )
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
    maxImages = pexConfig.Field(
        doc = "maximum images to select; intended for debugging; ignored in None",
        dtype = int,
        optional = True,
    )

class CcdExposureInfo(object):
    """Data about a found CCD exposure
    """
    def __init__(self, result):
        """Create image information from a query result from a db connection
        """
        self.dataId = dict(
            visit = result[0],
            raftName = result[1],
            ccdName = result[2],
        )
        self.ctrRaDec = result[3:5]
        self.fwhm = result[5]
        self.flags = result[6]

    @staticmethod
    def getColumnNames():
        """Set database query columns to be consistent with constructor
        """
        return "visit, raftName, ccdName, ra, decl, fwhm, flags"

class SelectLSSTImagesTask(pipeBase.Task):
    """Select LSST CCD exposures suitable for coaddition
    """
    ConfigClass = SelectLSSTImagesConfig
    _DefaultName = "selectImages"
    
    @pipeBase.timeMethod
    def run(self, filter, coordList):
        """Select LSST images suitable for coaddition in a particular region
        
        @param[in] filter: filter filter for images (e.g. "g", "r", "i"...)
        @param[in] coordList: list of coordinates defining region of interest; if None then select all images
        
        @return a pipeBase Struct containing:
        - ccdInfoList: a list of CcdExposureInfo objects, which have the following fields:
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
                """ % CcdExposureInfo.getColumnNames())
        else:
            # no region specified; look over the whole sky
            queryStr = ("""select %s
                from Science_Ccd_Exposure
                where filterName = %%s
                    and not (flags & ~%%s)
                    and fwhm < %%s
                """ % CcdExposureInfo.getColumnNames())
        cursor.execute(queryStr, (filter, self.config.flagMask, self.config.maxFwhm))
        ccdInfoList = [CcdExposureInfo(result) for result in cursor]
            
        if self.config.maxImages and self.config.maxImages < len(ccdInfoList):
            self.log.log(self.log.WARN, "Found %d images; truncating to config.maxImages=%d" % \
                (len(ccdInfoList), self.config.maxImages))
            ccdInfoList = ccdInfoList[0:self.config.maxImages]

        return pipeBase.Struct(
            ccdInfoList = ccdInfoList,
        )
    
    def runDataRef(self, dataRef, coordList):
        """Run based on a data reference
        
        @param[in] dataRef: data reference; must contain key "filter"
        @param[in] coordList: list of coordinates defining region of interest
        @return a pipeBase Struct containing:
        - dataRefList: a list of data references
        - ccdInfoList: a list of ccdInfo objects
        """
        butler = dataRef.butlerSubset.butler
        filter = dataRef.dataId["filter"]
        ccdInfoList = self.run(filter, coordList).ccdInfoList
        dataRefList = [butler.dataRef(
            datasetType = "calexp",
            dataId = ccdInfo.dataId,
        ) for ccdInfo in ccdInfoList]
        return pipeBase.Struct(
            dataRefList = dataRefList,
            ccdInfoList = ccdInfoList,
        )
    
    def searchWholeSky(self, dataRef):
        """Search the whole sky using a data reference
        @param[in] dataRef: data reference; must contain key "filter"
        @return a pipeBase Struct containing:
        - ccdInfoList: a list of ccdInfo objects
        """
        filter = dataRef.dataId["filter"]
        return self.run(filter, coordList=None)


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
    results = selectTask.run('r', coordList)
    for ccdInfo in results.ccdInfoList:
        print "dataId=%s, fwhm=%s, flags=%s" % (ccdInfo.dataId, ccdInfo.fwhm, ccdInfo.flags)
    
