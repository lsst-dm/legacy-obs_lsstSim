from glob import glob
from lsst.pipe.tasks.ingest import ParseTask
from lsst.pipe.tasks.ingest import IngestTask

__all__ = ['SimIngestTask', 'SimParseTask']


class SimIngestTask(IngestTask):

    def run(self, args):
        """Ingest all specified files and add them to the registry"""
        filenameList = sum([glob(filename) for filename in args.files], [])
        if args.output:
            outpath = args.output
        else:
            outpath = args.input
        context = self.register.openRegistry(outpath, create=args.create, dryrun=args.dryrun)
        ingest_list = []
        with context as registry:
            for infile in filenameList:
                if self.isBadFile(infile, args.badFile):
                    self.log.info("Skipping declared bad file %s", infile)
                    continue
                fileInfo, hduInfoList = self.parse.getInfo(infile)
                if self.isBadId(fileInfo, args.badId.idList):
                    self.log.info("Skipping declared bad file %s: %s", infile, fileInfo)
                    continue
                if self.register.check(registry, fileInfo):
                    self.log.warn("%s: already ingested: %s", infile, fileInfo)
                outfile = self.parse.getDestination(args.butler, fileInfo, infile)
                self.ingest(infile, outfile, mode=args.mode, dryrun=args.dryrun)
                for info in hduInfoList:
                    # The eimage has the same info as one of the amps, so if that amp has already
                    # been ingested, skip
                    if set(info.items()) in ingest_list:
                        continue
                    ingest_list.append(set(info.items()))
                    self.register.addRow(registry, info, dryrun=args.dryrun, create=args.create)
            self.register.addVisits(registry, dryrun=args.dryrun)


class SimParseTask(ParseTask):

    def translate_ccd(self, md):
        sensor_str = md.get('CHIPID')
        return ",".join(sensor_str[-2:])

    def translate_sensor(self, md):
        sensor_str = md.get('CHIPID')
        return ",".join(sensor_str[-2:])

    def translate_raft(self, md):
        sensor_str = md.get('CHIPID')
        return ",".join(sensor_str[1:3])

    def translate_taiobs(self, md):
        import lsst.daf.base as dafBase
        return dafBase.DateTime(md.get('MJD-OBS'), dafBase.DateTime.MJD,
                                dafBase.DateTime.TAI).toString(dafBase.DateTime.UTC)[:-1]

    def translate_channel(self, md):
        if 'AMPID' in md.names():
            amp_str = md.get('AMPID')
            return ",".join(amp_str[-2:])
        else:
            # Must be processing an eimage so return nominal amp
            return "0,0"

    def translate_snap(self, md):
        # HACK XXX this is just to work around the fact that we don't have
        # the correct header cards in the galsim images.
        filename_str = md.get('OUTFILE')
        if filename_str.endswith('fits'):
            return int(filename_str[-8:-5])
        else:
            return int(filename_str[-3:])

    def getDestination(self, butler, info, filename):
        """Get destination for the file

        @param butler      Data butler
        @param info        File properties, used as dataId for the butler
        @param filename    Input filename
        @return Destination filename
        """
        if 'lsst_a' in filename:
            raw = butler.get("raw_filename", info)[0]
            return raw
        elif 'lsst_e' in filename:
            return butler.get("eimage_filename", info)[0]
        else:
            raise RuntimeError('unrecognized filename: %s'%(filename))
