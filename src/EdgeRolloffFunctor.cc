// -*- lsst-c++ -*-

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

#include <cmath>
#include "boost/make_shared.hpp"
#include "lsst/obs/lsstSim/EdgeRolloffFunctor.h"

namespace lsst {
namespace obs {
namespace lsstSim {

EdgeRolloffFunctor::EdgeRolloffFunctor(double amplitude, double scale,
                                       double width)
   : afw::geom::Functor("EdgeRolloffFunctor"), _amplitude(amplitude),
     _scale(scale), _width(width) {
}

PTR(afw::geom::Functor) EdgeRolloffFunctor::clone() const {
   return std::make_shared<EdgeRolloffFunctor>(_amplitude, _scale, _width);
}

double EdgeRolloffFunctor::operator()(double x) const {
   double y = x + _amplitude*(std::exp(-(_width - x)/_scale) 
                              - std::exp(-x/_scale));
   return y;
}

double EdgeRolloffFunctor::derivative(double x) const {
   double dydx = 1 + _amplitude/_scale*(std::exp(-(_width - x)/_scale)
                                        + std::exp(-x/_scale));
   return dydx;
}

} // namespace lsstSim
} // namespace obs
} // namespace lsst
