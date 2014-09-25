import argparse, sys
import lsst.obs.lsstSim as lsstSim
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display the lsstSim camera')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    mapper = lsstSim.LsstSimMapper()
    camera = mapper.camera
