# -*- python -*-
import lsst.sconsUtils
from lsst.sconsUtils import scripts
scripts.BasicSConstruct("obs_lsstSim",
                        defaultTargets=scripts.DEFAULT_TARGETS + ("description",),
                        sconscriptOrder=["python", "description", "tests"]
                        )
env = lsst.sconsUtils.env
# Don't need to rebuild the camera descriptions if this code changes, so just Requires(), not Depends().
env.Requires(lsst.sconsUtils.targets['description'], lsst.sconsUtils.targets['version'])
env.Requires(lsst.sconsUtils.targets['description'], lsst.sconsUtils.targets['python'])
# Do need to rerun tests anytime the camera descriptions change.
env.Depends(lsst.sconsUtils.targets['tests'], lsst.sconsUtils.targets['description'])
