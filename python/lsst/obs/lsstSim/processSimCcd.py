#!/usr/bin/env python
#
# LSST Data Management System
# Copyright 2008-2015 AURA/LSST.
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
# see <https://www.lsstcorp.org/LegalNotices/>.
#
from lsst.pipe.base.argumentParser import ArgumentParser
from lsst.pipe.tasks.processCcd import ProcessCcdTask
from lsst.pipe.base import DataIdContainer


class SimContainer(DataIdContainer):
    def makeDataRefList(self, namespace):
        """Compute refList based on idList.
        Parameters
        ----------
        namespace
            Results of parsing command-line (with ``butler`` and ``log`` elements).
        Notes
        -----
        Not called if ``add_id_argument`` called with ``doMakeDataRefList=False``.
        """
        if self.datasetType is None:
            raise RuntimeError("Must call setDatasetType first")
        butler = namespace.butler
        for dataId in self.idList:
            refList = list(butler.subset(datasetType=self.datasetType, level="channel", dataId=dataId))
            # exclude nonexistent data
            # this is a recursive test, e.g. for the sake of "raw" data
            refList = [dr for dr in refList if dataExists(butler=butler, datasetType=self.datasetType,
                                                          dataRef=dr)]
            if not refList:
                namespace.log.warn("No data found for dataId=%s", dataId)
                continue
            self.refList += list(butler.subset(datasetType=self.datasetType, level="sensor", dataId=dataId))


class ProcessSimCcdTask(ProcessCcdTask):

    """Process an Eimage CCD

    This variant of processCcdTask loads e-images as post-ISR images
    """
    _DefaultName = "processSimCcd"

    @classmethod
    def _makeArgumentParser(cls):
        """Create an argument parser
        """
        parser = ArgumentParser(name=cls._DefaultName)
        parser.add_id_argument("--id", "raw", "data ID, e.g. visit=1 raft=2,2 sensor=1,1 snap=0",
                               ContainerClass=SimContainer)
        return parser


def dataExists(butler, datasetType, dataRef):
    """Determine if data exists at the current level or any data exists at a deeper level.
    Parameters
    ----------
    butler : `lsst.daf.persistence.Butler`
        The Butler.
    datasetType : `str`
        Dataset type.
    dataRef : `lsst.daf.persistence.ButlerDataRef`
        Butler data reference.
    Returns
    -------
    exists : `bool`
        Return value is `True` if data exists, `False` otherwise.
    """
    subDRList = dataRef.subItems()
    if subDRList:
        for subDR in subDRList:
            if dataExists(butler, datasetType, subDR):
                return True
        return False
    else:
        return butler.datasetExists(datasetType=datasetType, dataId=dataRef.dataId)

