#!/usr/bin/env python2
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
from __future__ import absolute_import, division
import sys
import traceback

from lsst.pipe.base import ArgumentParser
from lsst.obs.lsstSim.processCalibLsstSim import ProcessCalibLsstSimTask as TaskClass

if __name__ == "__main__":
    parser = ArgumentParser(name="argumentParser")
    namespace = parser.parse_args(config=TaskClass.ConfigClass())
    sensorDataRefLists = {}
    typeMap = {'0': 'bias', '1': 'dark', '2': 'flat_u', '3': 'flat_g', '4': 'flat_r',
               '5': 'flat_i', '6': 'flat_z', '7': 'flat_y'}
    types = []
    for dr in namespace.dataRefList:
        tdict = eval(dr.dataId.__repr__())
        types.append(typeMap[str(tdict['visit'])[4]])
        del tdict['visit']
        dstr = tdict.__repr__()
        if dstr in sensorDataRefLists:
            sensorDataRefLists[dstr].append(dr)
        else:
            sensorDataRefLists[dstr] = []
            sensorDataRefLists[dstr].append(dr)

    type = types[0]
    for t in types:
        if not t == type:
            raise ValueError("All calib visits must be of the same type: %s is not %s"%(t, type))

    task = TaskClass()
    if type in ('flat_u', 'flat_g', 'flat_r', 'flat_i', 'flat_z', 'flat_y'):
        type = 'flat'

    for k in sensorDataRefLists.keys():
        try:
            task.run(sensorDataRefLists[k], type)
        except Exception as e:
            task.log.fatal("Failed on dataId=%s: %s", k, e)
            traceback.print_exc(file=sys.stderr)
