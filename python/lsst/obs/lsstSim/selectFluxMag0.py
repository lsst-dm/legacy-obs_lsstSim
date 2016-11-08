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

from lsst.afw.coord import IcrsCoord
import lsst.afw.geom as afwGeom
from lsst.daf.persistence import DbAuth
import lsst.pipe.base as pipeBase
from lsst.pipe.tasks.selectImages import BaseExposureInfo, DatabaseSelectImagesConfig

__all__ = ["SelectLsstSimFluxMag0Task"]


class SelectLsstSimFluxMag0Config(DatabaseSelectImagesConfig):

    """Config for SelectLsstImagesTask
    """

    def setDefaults(self):
        super(SelectLsstSimFluxMag0Config, self).setDefaults()
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
        result = [r for r in result]
        dataId = dict(
            visit=result.pop(0),
            raft=result.pop(0),
            ccd=result.pop(0),
            filter=result.pop(0),
        )

        coordList = [IcrsCoord(afwGeom.Angle(result.pop(0), afwGeom.degrees),
                               afwGeom.Angle(result.pop(0), afwGeom.degrees)) for i in range(4)]

        BaseExposureInfo.__init__(self, dataId=dataId, coordList=coordList)
        self.fluxMag0 = result.pop(0)
        self.fluxMag0Sigma = result.pop(0)

    @staticmethod
    def getColumnNames():
        """Get database columns to retrieve, in a format useful to the database interface

        @return database column names as list of strings
        """
        return (
            "visit raftName ccdName filterName".split() +
            "corner1Ra corner1Decl corner2Ra corner2Decl".split() +
            "corner3Ra corner3Decl corner4Ra corner4Decl".split() +
            "fluxMag0 fluxMag0Sigma".split()
        )


class SelectLsstSimFluxMag0Task(pipeBase.Task):

    """Select LsstSim data suitable for computing fluxMag0
    """
    ConfigClass = SelectLsstSimFluxMag0Config
    _DefaultName = "selectFluxMag0"

    @pipeBase.timeMethod
    def run(self, dataId):
        """Select flugMag0's of LsstSim images for a particular visit

        @param[in] visit: visit id

        @return a pipeBase Struct containing:
        - fluxMagInfoList: a list of FluxMagInfo objects
        """
        try:
            runArgDict = self.runArgDictFromDataId(dataId)
            visit = runArgDict["visit"]
        except Exception:
            self.log.fatal("dataId does not contain mandatory visit key: dataId: %s", dataId)

        if self._display:
            self.log.info(self.config.database)

        db = MySQLdb.connect(
            host=self.config.host,
            port=self.config.port,
            db=self.config.database,
            user=DbAuth.username(self.config.host, str(self.config.port)),
            passwd=DbAuth.password(self.config.host, str(self.config.port)),
        )
        cursor = db.cursor()

        columnNames = tuple(FluxMagInfo.getColumnNames())

        queryStr = "select %s from Science_Ccd_Exposure where "%(", ".join(columnNames))
        dataTuple = ()

        # compute where clauses as a list of (clause, data)
        whereDataList = [
            ("visit = %s", visit),
        ]

        queryStr += " and ".join(wd[0] for wd in whereDataList)
        dataTuple += tuple(wd[1] for wd in whereDataList)

        if self._display:
            self.log.info("queryStr=%r; dataTuple=%s", queryStr, dataTuple)

        cursor.execute(queryStr, dataTuple)
        result = cursor.fetchall()
        fluxMagInfoList = [FluxMagInfo(r) for r in result]
        if self._display:
            self.log.info("Found %d exposures", len(fluxMagInfoList))

        return pipeBase.Struct(
            fluxMagInfoList=fluxMagInfoList,
        )

    def runArgDictFromDataId(self, dataId):
        """Extract keyword arguments for visit (other than coordList) from a data ID

        @param[in] dataId: a data ID dict
        @return keyword arguments for visit (other than coordList), as a dict
        """
        return dict(
            visit=dataId["visit"]
        )
