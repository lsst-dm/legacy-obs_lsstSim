import argparse, re, sys
import lsst.obs.lsstSim as lsstSim
import lsst.afw.cameraGeom.utils as cameraGeomUtils
from lsst.afw.cameraGeom import Camera

def checkStr(strVal, level):
    """Check if a string is a valid identifier
    @param[in] strVal: String containing the identifier
    @param[in] level: level of identifier: amp, ccd, raft
    return True if valid
    """
    if level == 'amp':
        matchStr = '^R:[0-9],[0-9] S:[0-9],[0-9] A:[0-9],[0-9]$'
        if not re.match(matchStr, strVal):
            raise ValueError("Specify raft, ccd, and amp: %s"%(strVal))
    elif level == 'ccd':
        matchStr = '^R:[0-9],[0-9] S:[0-9],[0-9]$'
        if not re.match(matchStr, strVal):
            raise ValueError("Specify only raft and ccd: %s"%(strVal))
    elif level == 'raft':
        matchStr = '^R:[0-9],[0-9]$'
        if not re.match(matchStr, strVal):
            raise ValueError("Specify only raft: %s"%(strVal))
    else:
        raise ValueError("level must be one of: ('amp', 'ccd', 'raft')")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display the lsstSim camera')
    parser.add_argument('--showAmp', help='Show an amplifier segment in ds9  May occur multiple times. '\
                                          'Format like R:Rx,Ry S:Sx,Sy A:Ax,Ay e.g. '\
                                          '\"R:2,2 S:1,1 A:0,0\"', type=str, nargs='+')
    parser.add_argument('--showCcd', help='Show a CCD from the mosaic in ds9.  May occur multiple times. '\
                                          'Format like R:Rx,Ry S:Sx,Sy e.g. \"R:2,2 S:1,1\"', type=str,
                                          nargs='+')
    parser.add_argument('--showRaft', help='Show a Raft from the mosaic in ds9.  May occur multiple times. '\
                                           'Format like R:Rx,Ry e.g. \"R:2,2\"', type=str, nargs='+')
    parser.add_argument('--showCamera', help='Show the camera mosaic in ds9.', action='store_true')
    parser.add_argument('--cameraBinSize', type= int, default=20,
                        help='Size of binning when displaying the full camera mosaic')
    parser.add_argument('--plotFocalPlane', action='store_true',
                        help='Plot the focalplane in an interactive matplotlib window')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    mapper = lsstSim.LsstSimMapper()
    camera = mapper.camera

    frame = 0
    if args.showAmp:
        for ampStr in args.showAmp:
            if checkStr(ampStr, 'amp'):
                raft, ccd, amp = ampStr.split()
                detector = camera[raft+" "+ccd]
                amplifier = detector[amp[2:]]
                cameraGeomUtils.showAmp(amplifier, frame=frame)
                frame += 1

    if args.showCcd:
        for ccdStr in args.showCcd:
            if checkStr(ccdStr, 'ccd'):
                raft, ccd = ccdStr.split()
                detector = camera[raft+" "+ccd]
                cameraGeomUtils.showCcd(detector, frame=frame)
                frame += 1

    if args.showRaft:
        for raftStr in args.showRaft:
            if checkStr(raftStr, 'raft'):
                detectorList = []
                for detector in camera:
                    detName = detector.getName()
                    if detName.startswith(raftStr):
                        detectorList.append(detector)
                tmpCamera = Camera(raftStr, detectorList, camera._transformMap)
                cameraGeomUtils.showCamera(tmpCamera, frame=frame, binSize=1)
                frame += 1

    if args.showCamera:
        cameraGeomUtils.showCamera(camera, frame=frame, binSize=args.cameraBinSize)

    if args.plotFocalPlane:
        cameraGeomUtils.plotFocalPlane(camera, 4., 4.)
