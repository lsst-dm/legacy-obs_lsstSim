from lsst.pipe.tasks.ingest import ParseTask
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
                dafBase.DateTime.TAI).toString()[:-1]

    def translate_channel(self, md):
        if 'AMPID' in md.names():
            amp_str = md.get('AMPID')
            return ",".join(amp_str[-2:])
        else:
            # Must be processing an eimage so return nominal amp
            return "0,0"

    def translate_snap(self, md):
        #HACK XXX this is just to work around the fact that we don't have
        #the correct header cards in the galsim images.
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


config.parse.retarget(SimParseTask)
config.parse.translation = {'visit': 'OBSID',
                          'expTime': 'EXPTIME',
                          }
config.parse.translators = {'taiObs': 'translate_taiobs',
                          'filter': 'translate_filter',
                          'ccd': 'translate_ccd',
                          'sensor': 'translate_sensor',
                          'raft': 'translate_raft',
                          'channel': 'translate_channel',
                          'snap': 'translate_snap'
                          }
config.register.columns = {'visit':    'int',
                         'channel':  'text',
                         'snap':     'int',
                         'sensor':   'text',
                         'ccd':      'text',
                         'raft':     'text',
                         'filter':   'text',
                         'taiObs':   'text',
                         'expTime':  'double',
                         }
config.register.visit = ['visit', 'filter']
config.register.unique = ['visit', 'sensor', 'raft', 'channel', 'snap']