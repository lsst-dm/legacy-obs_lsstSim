Description
===========

This obs_lsstSim package provides an interface to the phosim output for the LSST Data Management software.

Updating camera description
---------------------------

The camera description FITS files are built from the phosim lsst data text files. To update the camera description to match a new version of phosim, you will need two files from `phosim_release/data/lsst`, and the gain and saturation data from the header of the phosim generated files for the entire focalplane.

1. Checkout the latest version of phosim:
    * `git clone https://bitbucket.org/phosim/phosim_release.git`
2. Copy these files from your phosim checkout into this repo's `description/` directory:
    * `description/lsst/focalplanelayout.txt`
    * `description/lsst/segmentation.txt`
3. Generate the gain/saturation file (with obs_lsstSim setup via eups):
    1. Build phosim (see [Using Phosim](https://bitbucket.org/phosim/phosim_release/wiki/Using%20PhoSim) for build instructions). You likely will need to create an SEDs directory (even if its empty):
    `mkdir data/SEDs`
    2. Run phosim to generate a simple no-background simulation (give this several hours to complete):
    `./phosim $OBS_LSSTSIM_DIR/description/nostars_allchips -c examples/nobackground`
    3. Extract the gain and saturation values from the headers produced by the above commands:
    `extractPhosimGainSaturation.py -v output/`
3. Update the phosim verison in this repo's `description/phosim_version.txt` to match the version associated with the above files.
4. Commit your above changes and push.

The files you have updated above will be converted into the camera description files when this product is built by scons. You can check that this completes successfully by setting up this product and running "scons" at the root level.

Note that this process does not build the wavefront sensor files.
