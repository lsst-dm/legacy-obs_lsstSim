// -*- c++ -*-

/* 
 * LSST Data Management System
 * Copyright 2015 LSST Corporation.
 * 
 * This product includes software developed by the
 * LSST Project (http://www.lsst.org/).
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the LSST License Statement and 
 * the GNU General Public License along with this program.  If not, 
 * see <http://www.lsstcorp.org/LegalNotices/>.
 */
 

%define sensorLib_DOCSTRING
"
Python interface to lsst::obs::lsstSim::sensorLib
"
%enddef

%feature("autodoc", "1");
%module(package="lsst.obs.lsstSim", docstring=sensorLib_DOCSTRING) sensorLib

%{
#include "lsst/afw/geom.h"
#include "lsst/obs/lsstSim/sensor.h"
%}

%include "lsst/pex/exceptions/handler.i"

%import "lsst/afw/geom/geomLib.i"

%shared_ptr(lsst::obs::lsstSim::EdgeRolloffFunctor);

%include "lsst/obs/lsstSim/EdgeRolloffFunctor.h"
