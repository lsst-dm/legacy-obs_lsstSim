#!/usr/bin/env python
from glob import glob
from lsst.pipe.tasks.ingest import IngestTask
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
                    self.log.info("Skipping declared bad file %s" % infile)
                    continue
                fileInfo, hduInfoList = self.parse.getInfo(infile)
                if self.isBadId(fileInfo, args.badId.idList):
                    self.log.info("Skipping declared bad file %s: %s" % (infile, fileInfo))
                    continue
                if self.register.check(registry, fileInfo):
                    self.log.warn("%s: already ingested: %s" % (infile, fileInfo))
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
SimIngestTask.parseAndRun()