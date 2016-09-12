#!/usr/bin/env python2
#
# LSST Data Management System
# Copyright 2014 LSST Corporation.
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
# see <http://www.lsstcorp.org/LegalNotices/>.
#
"""
Extract gain and saturation values from phosim headers to make a gainFile for
makeLsstCameraRepository.py.

You first have to run phosim to generate images for each amp. These can be the
simplest no-background, no-source images, so long as they have a real gain and
saturation threshold.
"""
from __future__ import absolute_import, division, print_function

import os
import glob

from astropy.io import fits


def read_files(path, verbose=False):
    """Return a dictionary of amp name: (gain, saturation) for all amp files in path."""
    amps = {}
    files = glob.glob(os.path.join(path, 'lsst_*_R??_S??_C??*.fits.gz'))
    for file in files:
        if verbose:
            print(file)
        header = fits.getheader(file)
        ampid = '_'.join((header['CCDID'], header['AMPID']))
        amps[ampid] = header['GAIN'], int(header['SATURATE'])
    return amps


def write_gain_file(amps, filename):
    """Write a gainFile for use by makeLsstCameraRepository.py."""
    with open(filename, 'w') as outfile:
        for amp in sorted(amps):
            line = '{} {} {}\n'.format(amp, amps[amp][0], amps[amp][1])
            outfile.write(line)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phosim_output_path",
                        help="Path to phosim output directory containing amp files.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show file processing prgress.")
    args = parser.parse_args()

    amps = read_files(args.phosim_output_path, verbose=args.verbose)
    filename = os.path.join(os.environ['OBS_LSSTSIM_DIR'], 'description', 'gain_saturation.txt')
    write_gain_file(amps, filename)
    print("Wrote: ", filename)


if __name__ == "__main__":
    main()
