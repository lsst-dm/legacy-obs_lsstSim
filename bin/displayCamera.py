import argparse, re, sys
import lsst.obs.lsstSim as lsstSim
import lsst.afw.cameraGeom.utils as cameraGeomUtils

def checkStr(strVal, level):

    if level == 'amp':
        matchStr = '^R:[0-9],[0-9] S:[0-9],[0-9] A:[0-9],[0-9]$'
        if not re.match(matchStr, strVal):
            raise ValueError("Specify raft, ccd, and amp: %s"%(strVal))
    elif level == 'ccd':
        matchStr = '^R:[0-9],[0-9] S:[0-9],[0-9]$'
        if not re.match(matchStr, strVal):
            raise ValueError("Specify only raft and ccd: %s"%(strVal))
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
