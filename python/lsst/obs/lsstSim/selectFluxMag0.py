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
import MySQLdb

import lsst.pex.config as pexConfig
from lsst.afw.coord import IcrsCoord
import lsst.afw.geom as afwGeom
from lsst.daf.persistence import DbAuth
import lsst.pipe.base as pipeBase
from lsst.pipe.tasks.selectImages import SelectImagesConfig, BaseExposureInfo


__all__ = ["SelectLsstSimFluxMag0Task"]

class SelectLsstSimFluxMag0Config(SelectImagesConfig):
    table = pexConfig.Field(
        doc = "Name of database table",
        dtype = str,
        default = "Science_Ccd_Exposure",
    )

    def setDefaults(self):
        SelectImagesConfig.setDefaults(self)
        self.database = "krughoff_deepTemplate"
        self.host = "lsst-db.ncsa.illinois.edu"
        self.port = 3306


class FluxMagInfo(BaseExposureInfo):
    """Data about a selected exposure
    
    Data includes:
    - dataId: data ID of exposure (a dict)
    - coordList: a list of corner coordinates of the exposure (list of IcrsCoord)
    - fluxMag0: float 
    - fluxMag0Sigma: float
    """
    def __init__(self, result):
        """Set exposure information based on a query result from a db connection
        """
        BaseExposureInfo.__init__(self)
        self.dataId = dict(
           visit =  result[self._nextInd],
           raft = result[self._nextInd],
           ccd = result[self._nextInd],
           filter = result[self._nextInd],
        )
        self.coordList = []
        for i in range(4):
            self.coordList.append(
                IcrsCoord(
                    afwGeom.Angle(result[self._nextInd], afwGeom.degrees),
                    afwGeom.Angle(result[self._nextInd], afwGeom.degrees),
                )
            )
        self.fluxMag0 = result[self._nextInd]
        self.fluxMag0Sigma = result[self._nextInd]
                
    @staticmethod
    def getColumnNames():
        """Get database columns to retrieve, in a format useful to the database interface
        
        @return database column names as list of strings
        """
        return (
            "visit raftName ccdName filterName".split() + \
            "corner1Ra corner1Decl corner2Ra corner2Decl".split() + \
            "corner3Ra corner3Decl corner4Ra corner4Decl".split() + \
            "fluxMag0 fluxMag0Sigma".split()
        )

class SelectLsstSimFluxMag0Task(pipeBase.Task):
    """Select LsstSim data suitable for computing fluxMag0
    """
    ConfigClass = SelectLsstSimFluxMag0Config

    @pipeBase.timeMethod
    def run(self, visit):
        """Select flugMag0's of LsstSim images for a particular visit

        @param[in] visit: visit id 
        
        @return a pipeBase Struct containing:
        - fluxMagInfoList: a list of FluxMagInfo objects
        """
        
        kwargs = dict(
            user = DbAuth.username(self.config.host, str(self.config.port)),
            passwd = DbAuth.password(self.config.host, str(self.config.port)),
        )
            
        if self._display:    
            self.log.info(self.config.table)    
            self.log.info(self.config.database)
        
        db = MySQLdb.connect(
            host = self.config.host,
            port = self.config.port,
            db = self.config.database,
            **kwargs
        )
        cursor = db.cursor()
        
        columnNames = tuple(FluxMagInfo.getColumnNames())
       
        queryStr = "select %s from %s where " % (", ".join(columnNames), self.config.table)
        dataTuple = () # tuple(columnNames)
      
        # compute where clauses as a list of (clause, data)
        whereDataList = [
            ("visit = %s", visit),
        ]
        
        queryStr += " and ".join(wd[0] for wd in whereDataList)
        dataTuple += tuple(wd[1] for wd in whereDataList)
        
        if self._display: 
            self.log.info("queryStr=%r; dataTuple=%s" % (queryStr, dataTuple))
        
        cursor.execute(queryStr, dataTuple)
        exposureInfoList = [FluxMagInfo(result) for result in cursor]        
        if self._display: 
            self.log.info("Found %d exposures" % \
                      (len(exposureInfoList)))
        
        return pipeBase.Struct(
            fluxMagInfoList = exposureInfoList,
        )

    def runArgDictFromDataId(self, dataId):
        """Extract keyword arguments for visit (other than coordList) from a data ID
        
        @param[in] dataId: a data ID dict
        @return keyword arguments for visit (other than coordList), as a dict
        """
        return dict(
            visit = dataId["visit"]
        )
