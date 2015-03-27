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

/**
 * \file 
 * @brief lsst::afw::geom::Functor subclass to describe the edge rolloff
 * effect in CCDs.
 */

#ifndef LSST_OBS_LSSTSIM_EDGEROLLOFFFUNCTOR_H
#define LSST_OBS_LSSTSIM_EDGEROLLOFFFUNCTOR_H

#include "lsst/afw/geom/Functor.h"

namespace lsst {
namespace obs {
namespace lsstSim {

/// @brief Stubbs parameterization of edge rolloff effect in LSST
/// CCDs, expressed as a function of nominal pixel distance, x, from
/// the edge at x = 0.  The actual pixel location, xp, is modeled by
///      xp = x + A*(exp(-(xmax - x)/xscale) - exp(-x/xscale))
/// where A is the amplitude of the rolloff, xmax is the pixel
/// coordinate of the far edge of the sensor, and xscale is length
/// scale of the rolloff effect.
class EdgeRolloffFunctor : public afw::geom::Functor {

public:

   /// @param amplitude Amplitude of the rolloff effect (pixels).
   /// @param scale Length scale of the effect (pixels).
   /// @param width Width of the sensor (pixels).
   EdgeRolloffFunctor(double amplitude, double scale, double width);

   ~EdgeRolloffFunctor() {}

   virtual PTR(afw::geom::Functor) clone() const;

   /// @param x Nominal pixel location. Must be in the range [0, xmax].
   virtual double operator()(double x) const;

   /// @return Derivative of the function with respect to x.
   /// @param x Nominal pixel location.
   virtual double derivative(double x) const;

private:

   double _amplitude;
   double _scale;
   double _width;

};

} // namespace lsstSim
} // namespace obs
} // namespace lsst

#endif // LSST_OBS_LSSTSIM_EDGEROLLOFFFUNCTOR_H
